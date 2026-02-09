"""
Recording Handler - Manages message recording
Extracted from main_window.py to reduce complexity
"""
from typing import List, Optional, Callable, Any
from ..models.can_message import CANMessage


class RecordingHandler:
    """Manages recording of CAN messages"""
    
    def __init__(self, logger: Any):
        """
        Initialize recording handler
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.is_recording = False
        self.recorded_messages: List[CANMessage] = []
        
        # Callbacks
        self.on_recording_start: Optional[Callable] = None
        self.on_recording_stop: Optional[Callable[[int], None]] = None
        self.on_message_recorded: Optional[Callable[[CANMessage], None]] = None
    
    def start_recording(self):
        """Start recording messages"""
        if self.is_recording:
            self.logger.warning("Recording already in progress")
            return
        
        self.is_recording = True
        self.recorded_messages.clear()
        self.logger.info("Recording started")
        
        if self.on_recording_start:
            self.on_recording_start()
    
    def stop_recording(self):
        """Stop recording messages"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        count = len(self.recorded_messages)
        self.logger.info(f"Recording stopped: {count} messages recorded")
        
        if self.on_recording_stop:
            self.on_recording_stop(count)
    
    def toggle_recording(self) -> bool:
        """
        Toggle recording state
        
        Returns:
            New recording state
        """
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
        
        return self.is_recording
    
    def add_message(self, msg: CANMessage):
        """
        Add a message to recording
        
        Args:
            msg: CAN message to record
        """
        if not self.is_recording:
            return
        
        self.recorded_messages.append(msg)
        
        if self.on_message_recorded:
            self.on_message_recorded(msg)
    
    def get_recorded_messages(self) -> List[CANMessage]:
        """Get list of recorded messages"""
        return self.recorded_messages.copy()
    
    def get_message_count(self) -> int:
        """Get number of recorded messages"""
        return len(self.recorded_messages)
    
    def clear_recording(self):
        """Clear all recorded messages"""
        count = len(self.recorded_messages)
        self.recorded_messages.clear()
        self.logger.info(f"Recording cleared: {count} messages removed")
    
    def is_recording_active(self) -> bool:
        """Check if recording is active"""
        return self.is_recording
    
    def load_messages(self, messages: List[CANMessage]):
        """
        Load messages from file
        
        Args:
            messages: List of messages to load
        """
        self.recorded_messages = messages.copy()
        self.logger.info(f"Loaded {len(messages)} messages")
    
    def get_statistics(self) -> dict:
        """
        Get recording statistics
        
        Returns:
            Dictionary with statistics
        """
        if not self.recorded_messages:
            return {
                'count': 0,
                'unique_ids': 0,
                'duration': 0,
                'first_timestamp': None,
                'last_timestamp': None
            }
        
        unique_ids = len(set(msg.can_id for msg in self.recorded_messages))
        first_ts = self.recorded_messages[0].timestamp
        last_ts = self.recorded_messages[-1].timestamp
        duration = last_ts - first_ts
        
        return {
            'count': len(self.recorded_messages),
            'unique_ids': unique_ids,
            'duration': duration,
            'first_timestamp': first_ts,
            'last_timestamp': last_ts
        }
