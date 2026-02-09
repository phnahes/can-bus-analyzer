"""
UI State Manager - Manages UI state and mode transitions
Extracted from main_window.py to reduce complexity
"""
from typing import Optional, Callable, Any
from collections import defaultdict


class UIStateManager:
    """Manages UI state, modes, and transitions"""
    
    def __init__(self, logger: Any):
        """
        Initialize UI state manager
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        
        # Mode states
        self.tracer_mode = False
        self.split_screen_mode = False
        self.transmit_panel_visible = True
        
        # Connection state
        self.connected = False
        self.paused = False
        
        # Split screen channels
        self.split_screen_left_channel = None
        self.split_screen_right_channel = None
        
        # Message counters
        self.message_counters = defaultdict(int)
        self.message_last_timestamp = {}
        
        # Callbacks for UI updates
        self.on_mode_changed: Optional[Callable[[str], None]] = None
        self.on_connection_changed: Optional[Callable[[bool], None]] = None
    
    def set_tracer_mode(self, enabled: bool):
        """
        Set tracer mode
        
        Args:
            enabled: True to enable tracer mode
        """
        if self.tracer_mode != enabled:
            self.tracer_mode = enabled
            self.logger.info(f"Tracer mode: {enabled}")
            
            if self.on_mode_changed:
                self.on_mode_changed("tracer" if enabled else "monitor")
    
    def toggle_tracer_mode(self) -> bool:
        """
        Toggle tracer mode
        
        Returns:
            New tracer mode state
        """
        self.set_tracer_mode(not self.tracer_mode)
        return self.tracer_mode
    
    def is_tracer_mode(self) -> bool:
        """Check if in tracer mode"""
        return self.tracer_mode
    
    def set_split_screen(self, enabled: bool, left_channel: str = None, right_channel: str = None):
        """
        Set split screen mode
        
        Args:
            enabled: True to enable split screen
            left_channel: Left channel name
            right_channel: Right channel name
        """
        self.split_screen_mode = enabled
        if enabled:
            self.split_screen_left_channel = left_channel
            self.split_screen_right_channel = right_channel
            self.logger.info(f"Split screen: {left_channel} | {right_channel}")
        else:
            self.split_screen_left_channel = None
            self.split_screen_right_channel = None
            self.logger.info("Split screen disabled")
    
    def is_split_screen(self) -> bool:
        """Check if in split screen mode"""
        return self.split_screen_mode
    
    def set_transmit_panel_visible(self, visible: bool):
        """Set transmit panel visibility"""
        self.transmit_panel_visible = visible
        self.logger.info(f"Transmit panel: {'visible' if visible else 'hidden'}")
    
    def is_transmit_panel_visible(self) -> bool:
        """Check if transmit panel is visible"""
        return self.transmit_panel_visible
    
    def set_connected(self, connected: bool):
        """
        Set connection state
        
        Args:
            connected: True if connected
        """
        if self.connected != connected:
            self.connected = connected
            self.logger.info(f"Connection state: {connected}")
            
            if self.on_connection_changed:
                self.on_connection_changed(connected)
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected
    
    def set_paused(self, paused: bool):
        """Set paused state"""
        self.paused = paused
        self.logger.info(f"Paused: {paused}")
    
    def is_paused(self) -> bool:
        """Check if paused"""
        return self.paused
    
    def increment_message_counter(self, can_id: int, source: str) -> int:
        """
        Increment message counter
        
        Args:
            can_id: CAN ID
            source: Source channel
            
        Returns:
            New counter value
        """
        key = (can_id, source)
        self.message_counters[key] += 1
        return self.message_counters[key]
    
    def get_message_count(self, can_id: int, source: str) -> int:
        """Get message count for specific ID and source"""
        key = (can_id, source)
        return self.message_counters.get(key, 0)
    
    def update_last_timestamp(self, can_id: int, source: str, timestamp: float):
        """Update last timestamp for message"""
        key = (can_id, source)
        self.message_last_timestamp[key] = timestamp
    
    def get_last_timestamp(self, can_id: int, source: str) -> Optional[float]:
        """Get last timestamp for message"""
        key = (can_id, source)
        return self.message_last_timestamp.get(key)
    
    def calculate_period(self, can_id: int, source: str, current_timestamp: float) -> Optional[int]:
        """
        Calculate period in milliseconds
        
        Args:
            can_id: CAN ID
            source: Source channel
            current_timestamp: Current timestamp
            
        Returns:
            Period in milliseconds or None
        """
        last_ts = self.get_last_timestamp(can_id, source)
        if last_ts is not None:
            period_ms = int((current_timestamp - last_ts) * 1000)
            return period_ms
        return None
    
    def clear_counters(self):
        """Clear all message counters"""
        self.message_counters.clear()
        self.message_last_timestamp.clear()
        self.logger.info("Message counters cleared")
    
    def get_unique_id_count(self) -> int:
        """Get number of unique message IDs"""
        return len(self.message_counters)
    
    def get_total_message_count(self) -> int:
        """Get total message count"""
        return sum(self.message_counters.values())
    
    def get_statistics(self) -> dict:
        """
        Get UI statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'tracer_mode': self.tracer_mode,
            'split_screen': self.split_screen_mode,
            'connected': self.connected,
            'paused': self.paused,
            'unique_ids': self.get_unique_id_count(),
            'total_messages': self.get_total_message_count()
        }
