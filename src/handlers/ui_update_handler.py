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
            if not self.parent.message_queue.empty() and getattr(self.parent, 'logger', None):
                if not getattr(self, '_logged_paused', False):
                    self._logged_paused = True
                    self.parent.logger.info(
                        f"UI: paused - not displaying messages (qsize≈{self.parent.message_queue.qsize()}). "
                        "Unpause to see them."
                    )
            return
        self._logged_paused = False  # clear when not paused
        
        try:
            batch = 0
            while not self.parent.message_queue.empty():
                msg = self.parent.message_queue.get_nowait()
                self.parent.received_messages.append(msg)
                batch += 1
                try:
                    # Forward to FTCAN dialog if open
                    if getattr(self.parent, '_ftcan_dialog', None) is not None:
                        self.parent._ftcan_dialog.add_message(msg)
                    
                    # Check and fire triggers
                    if self.parent.triggers_enabled and self.parent.connected:
                        self.parent.check_and_fire_triggers(msg)
                    
                    split_active = self._is_split_screen_active()
                    if getattr(self.parent, 'logger', None) and (batch <= 2 or batch % 25 == 0):
                        self.parent.logger.debug(
                            f"UI: processing msg 0x{msg.can_id:03X} from '{msg.source}' "
                            f"(batch={batch}, split_screen={split_active}, "
                            f"mode={'tracer' if self.parent.tracer_mode else 'monitor'})"
                        )
                    
                    # Handle split-screen mode
                    if split_active:
                        self._handle_split_screen_message(msg)
                    else:
                        self._handle_single_screen_message(msg)
                    
                    self.parent.update_message_count()
                except Exception as e:
                    if getattr(self.parent, 'logger', None):
                        self.parent.logger.error(
                            f"Error displaying CAN message 0x{getattr(msg, 'can_id', 0):X}: {e}",
                            exc_info=True
                        )
            if batch > 0 and getattr(self.parent, 'logger', None) and batch > 2:
                self.parent.logger.debug(f"UI: processed batch of {batch} messages")
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
        # Note: Split-screen should only be active in Monitor mode, not Tracer
        # But we keep this logic for safety
        left_ch = self.parent.split_screen_left_channel
        right_ch = self.parent.split_screen_right_channel
        if msg.source != left_ch and msg.source != right_ch:
            if getattr(self.parent, 'logger', None):
                self.parent.logger.debug(
                    f"UI split_screen: msg 0x{msg.can_id:03X} from '{msg.source}' "
                    f"does not match left='{left_ch}' or right='{right_ch}' -> not displayed"
                )
            return
        if self.parent.tracer_mode:
            # Tracer mode should not use split-screen, but handle it anyway
            # Check channel filter
            if hasattr(self.parent, 'tracer_channel_combo'):
                selected_channel = self.parent.tracer_channel_combo.currentText()
                if selected_channel != "ALL" and msg.source != selected_channel:
                    return
            
            if self.parent.recording:
                self.parent.recording_mgr.add_message(msg)
            if msg.source == left_ch:
                self.parent._add_message_to_table(msg, self.parent.receive_table_left)
            elif msg.source == right_ch:
                self.parent._add_message_to_table(msg, self.parent.receive_table_right)
        else:
            if msg.source == left_ch:
                self.parent.add_message_monitor_mode(msg, target_table=self.parent.receive_table_left)
            elif msg.source == right_ch:
                self.parent.add_message_monitor_mode(msg, target_table=self.parent.receive_table_right)
    
    def _handle_single_screen_message(self, msg):
        """Handle message in single-screen mode
        
        Args:
            msg: The CANMessage to process
        """
        if self.parent.tracer_mode:
            # Check channel filter in Tracer mode
            if hasattr(self.parent, 'tracer_channel_combo'):
                selected_channel = self.parent.tracer_channel_combo.currentText()
                if selected_channel != "ALL" and msg.source != selected_channel:
                    # Message from different channel, skip it
                    return
            
            if self.parent.recording:
                self.parent.recording_mgr.add_message(msg)
                self.parent.add_message_tracer_mode(msg)
        else:
            self.parent.add_message_monitor_mode(msg)
