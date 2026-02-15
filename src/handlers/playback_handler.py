"""
Playback Handler - Manages message playback/replay
Extracted from main_window.py to reduce complexity
"""
from typing import List, Optional, Callable, Any
from threading import Thread, Event
import time
from ..models.can_message import CANMessage


class PlaybackHandler:
    """Manages playback of recorded CAN messages"""
    
    def __init__(self, 
                 send_callback: Callable[[CANMessage], bool],
                 logger: Any):
        """
        Initialize playback handler
        
        Args:
            send_callback: Callback to send a CAN message
            logger: Logger instance
        """
        self.send_callback = send_callback
        self.logger = logger
        
        self.playback_thread: Optional[Thread] = None
        self.stop_event = Event()
        self.pause_event = Event()
        self.is_playing = False
        self.is_paused = False
        
        # Callbacks for UI updates
        self.on_playback_start: Optional[Callable] = None
        self.on_playback_progress: Optional[Callable[[int, int], None]] = None
        self.on_playback_complete: Optional[Callable] = None
        self.on_playback_error: Optional[Callable[[str], None]] = None
        self.on_message_highlight: Optional[Callable[[int], None]] = None  # Highlight current message row
        self.on_playback_pause: Optional[Callable] = None  # Called when paused
        self.on_playback_resume: Optional[Callable] = None  # Called when resumed
    
    def play_all(self, messages: List[CANMessage], respect_timing: bool = True):
        """
        Play all recorded messages
        
        Args:
            messages: List of messages to play
            respect_timing: If True, respect original timing between messages
        """
        if self.is_playing:
            self.logger.warning("Playback already in progress")
            return
        
        if not messages:
            self.logger.warning("No messages to play")
            if self.on_playback_error:
                self.on_playback_error("No messages to play")
            return
        
        self.logger.info(f"Starting playback of {len(messages)} messages")
        self.stop_event.clear()
        self.is_playing = True
        
        if self.on_playback_start:
            self.on_playback_start()
        
        # Start playback in background thread
        self.playback_thread = Thread(
            target=self._playback_worker,
            args=(messages, respect_timing),
            daemon=True
        )
        self.playback_thread.start()
    
    def play_selected(self, messages: List[CANMessage], respect_timing: bool = True):
        """
        Play selected messages
        
        Args:
            messages: List of selected messages to play
            respect_timing: If True, respect original timing between messages
        """
        self.play_all(messages, respect_timing)
    
    def pause(self):
        """Pause current playback"""
        if not self.is_playing or self.is_paused:
            return
        
        self.logger.info("Pausing playback")
        self.is_paused = True
        self.pause_event.clear()  # Block the playback thread
        
        if self.on_playback_pause:
            self.on_playback_pause()
    
    def resume(self):
        """Resume paused playback"""
        if not self.is_playing or not self.is_paused:
            return
        
        self.logger.info("Resuming playback")
        self.is_paused = False
        self.pause_event.set()  # Unblock the playback thread
        
        if self.on_playback_resume:
            self.on_playback_resume()
    
    def toggle_pause(self):
        """Toggle pause/resume"""
        if self.is_paused:
            self.resume()
        else:
            self.pause()
    
    def stop(self):
        """Stop current playback"""
        if not self.is_playing:
            return
        
        self.logger.info("Stopping playback")
        self.stop_event.set()
        
        # If paused, resume to allow thread to exit
        if self.is_paused:
            self.pause_event.set()
        
        # Wait for thread to finish (with timeout)
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
        
        self.is_playing = False
        self.is_paused = False
        
        if self.on_playback_complete:
            self.on_playback_complete()
    
    def is_playback_active(self) -> bool:
        """Check if playback is currently active"""
        return self.is_playing
    
    def _playback_worker(self, messages: List[CANMessage], respect_timing: bool):
        """
        Background worker for message playback
        
        Args:
            messages: Messages to play
            respect_timing: Whether to respect original timing
        """
        try:
            total = len(messages)
            sent_count = 0
            failed_count = 0
            
            # Set pause event initially (not paused)
            self.pause_event.set()
            
            for i, msg in enumerate(messages):
                # Check stop signal
                if self.stop_event.is_set():
                    self.logger.info(f"Playback stopped by user at {i}/{total}")
                    break
                
                # Wait if paused
                self.pause_event.wait()
                
                # Check stop again after resuming from pause
                if self.stop_event.is_set():
                    self.logger.info(f"Playback stopped by user at {i}/{total}")
                    break
                
                # Highlight current message row
                if self.on_message_highlight:
                    self.on_message_highlight(i)
                
                # Send message
                try:
                    success = self.send_callback(msg)
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                        self.logger.warning(f"Failed to send message {i+1}/{total}")
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Error sending message {i+1}/{total}: {e}")
                
                # Update progress
                if self.on_playback_progress:
                    self.on_playback_progress(i + 1, total)
                
                # Respect timing if enabled
                if respect_timing and i < total - 1:
                    # Calculate delay to next message
                    delay = messages[i + 1].timestamp - msg.timestamp
                    if delay > 0 and delay < 10:  # Max 10 seconds between messages
                        time.sleep(delay)
                    elif delay <= 0:
                        time.sleep(0.001)  # Minimum delay
                else:
                    # Small delay between messages
                    time.sleep(0.01)
            
            # Playback complete
            self.logger.info(f"Playback complete: {sent_count} sent, {failed_count} failed")
            self.is_playing = False
            
            if self.on_playback_complete:
                self.on_playback_complete()
                
        except Exception as e:
            self.logger.error(f"Playback error: {e}")
            self.is_playing = False
            
            if self.on_playback_error:
                self.on_playback_error(str(e))
