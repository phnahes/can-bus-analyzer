"""
UI Update Handler
Handles periodic UI updates with incoming CAN messages
"""

import queue


class UIUpdateHandler:
    """Handles UI updates with incoming messages"""
    
    def __init__(self, parent):
        """Initialize the handler
        
        Args:
            parent: The parent window (main_window)
        """
        self.parent = parent
    
    def update_ui(self):
        """Update the interface with new messages
        
        Processes messages from the queue and updates the appropriate tables
        based on the current mode (Tracer/Monitor) and split-screen configuration.
        """
        if self.parent.paused:
            return
        
        try:
            while not self.parent.message_queue.empty():
                msg = self.parent.message_queue.get_nowait()
                self.parent.received_messages.append(msg)
                
                # Forward to FTCAN dialog if open
                if self.parent._ftcan_dialog is not None:
                    self.parent._ftcan_dialog.add_message(msg)
                
                # Check and fire triggers
                if self.parent.triggers_enabled and self.parent.connected:
                    self.parent.check_and_fire_triggers(msg)
                
                # Handle split-screen mode
                if self._is_split_screen_active():
                    self._handle_split_screen_message(msg)
                else:
                    self._handle_single_screen_message(msg)
                
                self.parent.update_message_count()
                
        except queue.Empty:
            pass
    
    def _is_split_screen_active(self) -> bool:
        """Check if split-screen mode is active and configured"""
        return (self.parent.split_screen_mode and 
                self.parent.receive_table_left and 
                self.parent.receive_table_right)
    
    def _handle_split_screen_message(self, msg):
        """Handle message in split-screen mode
        
        Args:
            msg: The CANMessage to process
        """
        if self.parent.tracer_mode:
            if self.parent.recording:
                self.parent.recording_mgr.add_message(msg)
                if msg.source == self.parent.split_screen_left_channel:
                    self.parent._add_message_to_table(msg, self.parent.receive_table_left)
                elif msg.source == self.parent.split_screen_right_channel:
                    self.parent._add_message_to_table(msg, self.parent.receive_table_right)
        else:
            if msg.source == self.parent.split_screen_left_channel:
                self.parent.add_message_monitor_mode(msg, target_table=self.parent.receive_table_left)
            elif msg.source == self.parent.split_screen_right_channel:
                self.parent.add_message_monitor_mode(msg, target_table=self.parent.receive_table_right)
    
    def _handle_single_screen_message(self, msg):
        """Handle message in single-screen mode
        
        Args:
            msg: The CANMessage to process
        """
        if self.parent.tracer_mode:
            if self.parent.recording:
                self.parent.recording_mgr.add_message(msg)
                self.parent.add_message_tracer_mode(msg)
        else:
            self.parent.add_message_monitor_mode(msg)
