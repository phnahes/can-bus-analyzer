"""
UI Update Handler
Handles periodic UI updates with incoming CAN messages
"""

import queue
import time


class UIUpdateHandler:
    """Handles UI updates with incoming messages

    Messages are drained in bounded batches (wall-clock budget + hard cap) so a
    burst can never monopolize the Qt event loop. Tracer rows are buffered by
    the table manager and inserted once per tick; the status bar is refreshed
    once per tick instead of once per frame.
    """

    #: Wall-clock budget for one UI tick; the remainder stays queued.
    TICK_BUDGET_S = 0.020
    #: Hard cap per tick, so a huge backlog cannot stall the event loop.
    MAX_MESSAGES_PER_TICK = 1000

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
        parent = self.parent

        if parent.paused:
            if not parent.message_queue.empty() and getattr(parent, 'logger', None):
                if not getattr(self, '_logged_paused', False):
                    self._logged_paused = True
                    parent.logger.info(
                        f"UI: paused - not displaying messages (qsize≈{parent.message_queue.qsize()}). "
                        "Unpause to see them."
                    )
            return
        self._logged_paused = False  # clear when not paused

        manager = getattr(parent, 'receive_table_mgr', None)
        tables = self._active_tables()

        for table in tables:
            table.setUpdatesEnabled(False)
        if manager is not None:
            manager.begin_batch()

        batch = 0
        try:
            deadline = time.monotonic() + self.TICK_BUDGET_S
            while batch < self.MAX_MESSAGES_PER_TICK:
                if time.monotonic() >= deadline:
                    break
                try:
                    msg = parent.message_queue.get_nowait()
                except queue.Empty:
                    break

                batch += 1
                parent.received_messages.append(msg)

                try:
                    self._dispatch(msg, batch)
                except Exception as e:
                    if getattr(parent, 'logger', None):
                        parent.logger.error(
                            f"Error displaying CAN message 0x{getattr(msg, 'can_id', 0):X}: {e}",
                            exc_info=True
                        )
        finally:
            # Flush buffered tracer rows and re-enable painting even on error.
            if manager is not None:
                manager.end_batch()
            for table in tables:
                table.setUpdatesEnabled(True)

        if batch:
            # Once per tick (was once per message).
            parent.update_message_count()

            if parent.tracer_mode:
                for table in tables:
                    if table.rowCount():
                        table.scrollToBottom()

            if getattr(parent, 'logger', None) and batch > 2:
                parent.logger.debug(f"UI: processed batch of {batch} messages")

    def _dispatch(self, msg, batch: int):
        """Route one message to the dialogs, triggers and tables."""
        parent = self.parent

        # Forward to FTCAN dialog if open
        if getattr(parent, '_ftcan_dialog', None) is not None:
            parent._ftcan_dialog.add_message(msg)

        # Forward to BAP dialog if open
        if getattr(parent, '_bap_dialog', None) is not None:
            parent._bap_dialog.add_message(msg)

        # Check and fire triggers
        if parent.triggers_enabled and parent.connected:
            parent.check_and_fire_triggers(msg)

        if getattr(parent, 'logger', None) and (batch <= 2 or batch % 25 == 0):
            parent.logger.debug(
                f"UI: processing msg 0x{msg.can_id:03X} from '{msg.source}' "
                f"(batch={batch}, split_screen={self._is_split_screen_active()}, "
                f"mode={'tracer' if parent.tracer_mode else 'monitor'})"
            )

        if self._is_split_screen_active():
            self._handle_split_screen_message(msg)
        else:
            self._handle_single_screen_message(msg)

    def _active_tables(self):
        """Tables that receive frames for the current view."""
        parent = self.parent
        if self._is_split_screen_active():
            return [parent.receive_table_left, parent.receive_table_right]
        table = getattr(parent, 'receive_table', None)
        return [table] if table is not None else []

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
