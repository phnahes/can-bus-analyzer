"""
Transmit Handler

Manages CAN message transmission logic including periodic sending.
Separated from UI code for better testability and maintainability.
"""

import threading
from typing import List, Dict, Optional
from ..logger import get_logger

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False


class TransmitHandler:
    """Handles CAN message transmission"""
    
    def __init__(self, parent_window, can_bus_manager=None):
        """
        Initialize transmit handler.
        
        Args:
            parent_window: Main window instance
            can_bus_manager: CAN bus manager instance
        """
        self.parent = parent_window
        self.can_bus_manager = can_bus_manager
        self.logger = get_logger()
        
        # Transmit messages list
        self.transmit_messages: List[Dict] = []
        
        # Periodic sending state
        self.periodic_send_active = False
        self.periodic_threads: Dict[int, threading.Thread] = {}
        self.periodic_stop_events: Dict[int, threading.Event] = {}
        
        # Callbacks
        self.on_count_updated = None
    
    def add_message(self, message_data: Dict) -> None:
        """
        Add a message to the transmit list.
        
        Args:
            message_data: Dictionary with message data (id, dlc, data, etc.)
        """
        self.transmit_messages.append(message_data)
    
    def remove_message(self, index: int) -> bool:
        """
        Remove a message from the transmit list.
        
        Args:
            index: Index of message to remove
            
        Returns:
            bool: True if removed successfully
        """
        if 0 <= index < len(self.transmit_messages):
            self.transmit_messages.pop(index)
            return True
        return False
    
    def send_single(self, message_data: Dict, target_bus: str = None) -> bool:
        """
        Send a single CAN message.
        
        Args:
            message_data: Message data dictionary
            target_bus: Target bus name (None = all buses)
            
        Returns:
            bool: True if sent successfully
        """
        if not self.can_bus_manager:
            self.logger.warning("Cannot send: not connected")
            return False
        
        try:
            self.logger.debug(f"send_single: message_data={message_data}")
            self.logger.debug(f"send_single: target_bus={target_bus}")
            
            # Create CAN message
            can_msg = can.Message(
                arbitration_id=message_data['can_id'],
                data=message_data['data'],
                is_extended_id=message_data.get('is_extended', False),
                is_remote_frame=message_data.get('is_rtr', False)
            )
            
            self.logger.debug(f"send_single: can_msg.arbitration_id=0x{can_msg.arbitration_id:03X}")
            self.logger.debug(f"send_single: can_msg.data={can_msg.data.hex()}")
            self.logger.debug(f"send_single: can_msg.is_extended_id={can_msg.is_extended_id}")
            self.logger.debug(f"send_single: can_msg.is_remote_frame={can_msg.is_remote_frame}")
            
            # Send via bus manager
            if target_bus:
                success = self.can_bus_manager.send_to(target_bus, can_msg)
                self.logger.debug(f"send_single: send_to result={success}")
            else:
                results = self.can_bus_manager.send_to_all(can_msg)
                success = any(results.values())
                self.logger.debug(f"send_single: send_to_all results={results}")
            
            if success:
                msg_type = "RTR" if message_data.get('is_rtr', False) else "Data"
                self.logger.info(f"Sent {msg_type} 0x{message_data['can_id']:03X} to {target_bus or 'all'}")
            else:
                self.logger.warning(f"Failed to send 0x{message_data['can_id']:03X}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}", exc_info=True)
            return False
    
    def start_periodic(self, index: int, period_ms: int, message_data: Dict = None) -> bool:
        """
        Start periodic transmission of a message.
        
        Args:
            index: Index of message in transmit list
            period_ms: Period in milliseconds
            message_data: Optional message data (if not in transmit_messages list)
            
        Returns:
            bool: True if started successfully
        """
        self.logger.debug(f"start_periodic: index={index}, period_ms={period_ms}")
        self.logger.debug(f"start_periodic: message_data={message_data}")
        
        if index in self.periodic_threads:
            self.logger.warning(f"Periodic send already active for row {index}")
            return False
        
        # Use provided message_data or get from list
        if message_data is None:
            self.logger.debug(f"start_periodic: message_data is None, getting from transmit_messages")
            if index < 0 or index >= len(self.transmit_messages):
                self.logger.warning(f"start_periodic: invalid index {index}, transmit_messages length={len(self.transmit_messages)}")
                return False
            message_data = self.transmit_messages[index]
            self.logger.debug(f"start_periodic: got message_data from list: {message_data}")
        
        # Create stop event
        stop_event = threading.Event()
        self.periodic_stop_events[index] = stop_event
        
        # Create and start thread
        thread = threading.Thread(
            target=self._periodic_send_worker,
            args=(index, message_data, period_ms, stop_event),
            daemon=True
        )
        self.periodic_threads[index] = thread
        thread.start()
        
        self.periodic_send_active = True
        self.logger.info(f"start_periodic: started periodic send for index {index} with period {period_ms}ms")
        return True
    
    def stop_periodic(self, index: int) -> bool:
        """
        Stop periodic transmission of a message.
        
        Args:
            index: Index of message in transmit list
            
        Returns:
            bool: True if stopped successfully
        """
        if index not in self.periodic_threads:
            return False
        
        # Signal stop
        self.periodic_stop_events[index].set()
        
        # Wait for thread to finish
        self.periodic_threads[index].join(timeout=1.0)
        
        # Clean up
        del self.periodic_threads[index]
        del self.periodic_stop_events[index]
        
        # Update state
        if not self.periodic_threads:
            self.periodic_send_active = False
        
        return True
    
    def stop_all_periodic(self) -> None:
        """Stop all periodic transmissions"""
        indices = list(self.periodic_threads.keys())
        for index in indices:
            self.stop_periodic(index)
    
    def is_periodic_active(self, index: int) -> bool:
        """Check if periodic sending is active for a message"""
        return index in self.periodic_threads
    
    def start_all_periodic(self, messages: List[Dict]) -> int:
        """
        Start periodic transmission for all messages with TX Mode = 'on'
        
        Args:
            messages: List of message dictionaries from transmit table
            
        Returns:
            int: Number of messages started
        """
        self.logger.debug(f"start_all_periodic: received {len(messages)} messages")
        count = 0
        for i, msg_data in enumerate(messages):
            self.logger.debug(f"start_all_periodic: msg[{i}] = {msg_data}")
            
            tx_mode = msg_data.get('tx_mode', 'off').lower()
            self.logger.debug(f"start_all_periodic: msg[{i}] tx_mode={tx_mode}")
            if tx_mode != 'on':
                continue
            
            period = msg_data.get('period', 0)
            self.logger.debug(f"start_all_periodic: msg[{i}] period={period} (type={type(period).__name__})")
            if isinstance(period, str):
                if period == 'off' or period == '0':
                    self.logger.debug(f"start_all_periodic: msg[{i}] period is 'off' or '0', skipping")
                    continue
                try:
                    period = int(period)
                    self.logger.debug(f"start_all_periodic: msg[{i}] period converted to {period}")
                except ValueError:
                    self.logger.debug(f"start_all_periodic: msg[{i}] period conversion failed, skipping")
                    continue
            
            if period <= 0:
                self.logger.debug(f"start_all_periodic: msg[{i}] period <= 0, skipping")
                continue
            
            self.logger.debug(f"start_all_periodic: msg[{i}] starting periodic with period={period}")
            if self.start_periodic(i, period, msg_data):
                count += 1
                self.logger.debug(f"start_all_periodic: msg[{i}] started successfully")
            else:
                self.logger.debug(f"start_all_periodic: msg[{i}] failed to start")
        
        self.logger.info(f"start_all_periodic: started {count} messages")
        return count
    
    def set_can_bus_manager(self, can_bus_manager):
        """Update CAN bus manager reference"""
        self.can_bus_manager = can_bus_manager
    
    def _periodic_send_worker(self, index: int, message_data: Dict, 
                             period_ms: int, stop_event: threading.Event) -> None:
        """
        Worker thread for periodic message sending.
        
        Args:
            index: Message index
            message_data: Message data dictionary
            period_ms: Period in milliseconds
            stop_event: Event to signal stop
        """
        import time
        
        period_s = period_ms / 1000.0
        count = 0
        
        while not stop_event.is_set():
            # Send message
            target_bus = message_data.get('target_bus')
            if self.send_single(message_data, target_bus):
                count += 1
                if self.on_count_updated:
                    self.on_count_updated(index, count)
            
            # Wait for next period
            stop_event.wait(period_s)
        
        self.logger.info(f"Periodic send stopped for row {index}, sent {count} messages")
