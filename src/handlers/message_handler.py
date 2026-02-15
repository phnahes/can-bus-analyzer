"""
Message Handler

Manages CAN message reception, processing, and display logic.
Separated from UI code for better testability and maintainability.
"""

import threading
import queue
from typing import List, Dict, Callable, Optional
from collections import defaultdict
from ..models import CANMessage
from ..logger import get_logger


class MessageHandler:
    """Handles CAN message reception and processing"""
    
    def __init__(self, parent_window):
        """
        Initialize message handler.
        
        Args:
            parent_window: Main window instance (for UI updates)
        """
        self.parent = parent_window
        self.logger = get_logger()
        
        # Message storage
        self.received_messages: List[CANMessage] = []
        self.recorded_messages: List[CANMessage] = []  # For playback
        self.message_queue = queue.Queue()
        
        # Message statistics - use parent's counters
        self.message_counters = None  # Will be set to parent's counters
        self.message_last_timestamp = None  # Will be set to parent's timestamps
        
        # State
        self.paused = False
        self.recording = False
        
        # Threading
        self.receive_thread: Optional[threading.Thread] = None
    
    def add_message(self, msg: CANMessage, source: str = None) -> None:
        """
        Add a received message to the queue.
        
        Args:
            msg: CAN message to add
            source: Source bus name
        """
        if source:
            msg.source = source
        
        self.message_queue.put(msg)
        
        # Update statistics
        self.message_counters[msg.can_id] += 1
        self.message_last_timestamp[msg.can_id] = msg.timestamp
    
    def process_queue(self) -> List[CANMessage]:
        """
        Process messages from queue.
        
        Returns:
            List of messages processed
        """
        messages = []
        
        try:
            while not self.message_queue.empty():
                msg = self.message_queue.get_nowait()
                
                if not self.paused:
                    self.received_messages.append(msg)
                    
                    if self.recording:
                        self.recorded_messages.append(msg)
                    
                    messages.append(msg)
                    
        except queue.Empty:
            pass
        
        return messages
    
    def clear_messages(self) -> None:
        """Clear all received messages"""
        self.received_messages.clear()
        self.message_counters.clear()
        self.message_last_timestamp.clear()
        
        # Clear queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
    
    def toggle_pause(self) -> bool:
        """
        Toggle pause state.
        
        Returns:
            bool: New pause state
        """
        self.paused = not self.paused
        return self.paused
    
    def get_message_count(self) -> int:
        """Get total number of received messages"""
        return len(self.received_messages)
    
    def get_unique_ids(self) -> int:
        """Get number of unique CAN IDs seen"""
        return len(self.message_counters)
    
    def get_message_rate(self, can_id: int) -> float:
        """
        Calculate message rate for a specific CAN ID.
        
        Args:
            can_id: CAN ID to calculate rate for
            
        Returns:
            float: Messages per second (0 if not enough data)
        """
        if can_id not in self.message_counters or self.message_counters[can_id] < 2:
            return 0.0
        
        # Find first and last message with this ID
        first_msg = None
        last_msg = None
        
        for msg in self.received_messages:
            if msg.can_id == can_id:
                if first_msg is None:
                    first_msg = msg
                last_msg = msg
        
        if first_msg and last_msg and last_msg.timestamp > first_msg.timestamp:
            time_span = last_msg.timestamp - first_msg.timestamp
            return (self.message_counters[can_id] - 1) / time_span
        
        return 0.0
    
    def get_statistics(self) -> Dict:
        """
        Get message statistics.
        
        Returns:
            Dict with statistics
        """
        return {
            'total_messages': self.get_message_count(),
            'unique_ids': self.get_unique_ids(),
            'paused': self.paused,
            'recording': self.recording,
            'recorded_count': len(self.recorded_messages)
        }
    
    def prepare_tracer_row_data(self, msg: CANMessage, row_index: int) -> Dict:
        """
        Prepare data for a tracer mode table row.
        
        Args:
            msg: CAN message
            row_index: Row index in table
            
        Returns:
            Dict with formatted data for each column
        """
        from datetime import datetime
        
        dt = datetime.fromtimestamp(msg.timestamp)
        time_str = dt.strftime("%S.%f")[:-3]  # Segundos.milissegundos
        pid_str = f"0x{msg.can_id:03X}"
        data_str = " ".join([f"{b:02X}" for b in msg.data])
        ascii_str = msg.to_ascii()
        
        # Add gateway action indicator
        gateway_indicator = ""
        if msg.gateway_action:
            if msg.gateway_action == "blocked":
                gateway_indicator = "🚫"  # Blocked
            elif msg.gateway_action == "forwarded":
                gateway_indicator = "➡️"  # Forwarded
            elif msg.gateway_action == "modified":
                gateway_indicator = "✏️"  # Modified
            elif msg.gateway_action == "loop_prevented":
                gateway_indicator = "🔄"  # Loop prevented
        
        # Add indicator to channel display
        channel_display = msg.source
        if gateway_indicator:
            channel_display = f"{msg.source} {gateway_indicator}"
        
        return {
            'id': str(row_index + 1),
            'time': time_str,
            'channel': channel_display,
            'pid': pid_str,
            'dlc': str(msg.dlc),
            'data': data_str,
            'ascii': ascii_str,
            'comment': msg.comment,
            'msg_index': len(self.recorded_messages) - 1,  # For UserRole
            'gateway_action': msg.gateway_action
        }
    
    def calculate_period(self, msg: CANMessage, counter_key: tuple) -> str:
        """
        Calculate period for a message BEFORE updating timestamp.
        
        Args:
            msg: CAN message
            counter_key: Tuple of (can_id, source) for counter lookup
            
        Returns:
            Period string in milliseconds
        """
        # Initialize references if needed
        if self.message_counters is None:
            self.message_counters = self.parent.message_counters
        if self.message_last_timestamp is None:
            self.message_last_timestamp = self.parent.message_last_timestamp
        
        period_str = ""
        if counter_key in self.message_last_timestamp:
            period_ms = int((msg.timestamp - self.message_last_timestamp[counter_key]) * 1000)
            period_str = f"{period_ms}"
        return period_str
    
    def prepare_monitor_row_data(self, msg: CANMessage, counter_key: tuple, period_str: str = "") -> Dict:
        """
        Prepare data for a monitor mode table row.
        
        Args:
            msg: CAN message
            counter_key: Tuple of (can_id, source) for counter lookup
            period_str: Pre-calculated period string
            
        Returns:
            Dict with formatted data and metadata
        """
        pid_str = f"0x{msg.can_id:03X}"
        data_str = " ".join([f"{b:02X}" for b in msg.data])
        ascii_str = msg.to_ascii()
        
        # Get count
        count = self.message_counters[counter_key]
        
        # Add gateway action indicator
        gateway_indicator = ""
        if msg.gateway_action:
            if msg.gateway_action == "blocked":
                gateway_indicator = "🚫"  # Blocked
            elif msg.gateway_action == "forwarded":
                gateway_indicator = "➡️"  # Forwarded
            elif msg.gateway_action == "modified":
                gateway_indicator = "✏️"  # Modified
            elif msg.gateway_action == "loop_prevented":
                gateway_indicator = "🔄"  # Loop prevented
        
        # Add indicator to channel display
        channel_display = msg.source
        if gateway_indicator:
            channel_display = f"{msg.source} {gateway_indicator}"
        
        return {
            'pid': pid_str,
            'count': str(count),
            'channel': channel_display,
            'dlc': str(msg.dlc),
            'data': data_str,
            'period': period_str,
            'ascii': ascii_str,
            'comment': msg.comment,
            'can_id': msg.can_id,
            'should_highlight': count > 1,
            'gateway_action': msg.gateway_action
        }
    
    def update_counter(self, msg: CANMessage) -> tuple:
        """
        Update message counter for a CAN ID + source.
        
        Args:
            msg: CAN message
            
        Returns:
            Tuple of (can_id, source) as counter key
        """
        counter_key = (msg.can_id, msg.source)
        
        # Use parent's counters if available, otherwise use local
        if self.message_counters is None:
            self.message_counters = self.parent.message_counters
        if self.message_last_timestamp is None:
            self.message_last_timestamp = self.parent.message_last_timestamp
        
        self.message_counters[counter_key] += 1
        self.message_last_timestamp[counter_key] = msg.timestamp
        return counter_key
