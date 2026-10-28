"""
Tracer Mode Manager

Manages switching between Tracer and Monitor modes.
Extracted from main_window.py to reduce complexity.
"""

from datetime import datetime
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt
from collections import defaultdict
from ..ui import table_helpers


class TracerModeManager:
    """Manages tracer/monitor mode switching"""
    
    def __init__(self, parent_window):
        """
        Initialize tracer mode manager
        
        Args:
            parent_window: Main window instance
        """
        self.parent = parent_window
    
    def toggle_mode(self):
        """Toggle between Tracer and Monitor mode"""
        from ..i18n import t
        
        # Store previous mode
        was_tracer_mode = self.parent.tracer_mode
        self.parent.tracer_mode = not self.parent.tracer_mode
        self.parent.btn_tracer.setChecked(False)
        
        if self.parent.tracer_mode:
            self.parent.btn_tracer.setText(f"📊 {t('btn_monitor')}")
            # Disable Diff button in Tracer mode (diff is Monitor-only)
            if hasattr(self.parent, 'btn_diff'):
                self.parent.btn_diff.setEnabled(False)
                self.parent._diff_was_enabled_before_tracer = bool(
                    self.parent.diff_config.enabled
                )
                if self.parent.diff_config.enabled:
                    self.parent.diff_config.enabled = False
                    self.parent.receive_table_mgr.diff_manager = None
                    self.parent.update_diff_button_state()
        else:
            self.parent.btn_tracer.setText(f"📊 {t('btn_tracer')}")
            # Enable Diff button in Monitor mode; restore diff if it was on before Tracer
            if hasattr(self.parent, 'btn_diff'):
                self.parent.btn_diff.setEnabled(True)
                if getattr(self.parent, '_diff_was_enabled_before_tracer', False):
                    self.parent.diff_config.enabled = True
                    self.parent._apply_diff_config(old_enabled=False)
                    self.parent._diff_was_enabled_before_tracer = False
        
        # If switching TO Tracer mode, disable split-screen
        if self.parent.tracer_mode and self.parent.split_screen_mode:
            self.parent.logger.info("Switching to Tracer mode: disabling split-screen")
            self._disable_split_screen_for_tracer()
        
        # If switching FROM Tracer TO Monitor, restore split-screen if it was active before
        if not self.parent.tracer_mode and was_tracer_mode and hasattr(self.parent, '_split_screen_was_active'):
            if self.parent._split_screen_was_active:
                self.parent.logger.info("Switching to Monitor mode: restoring split-screen")
                self._restore_split_screen_for_monitor()
        
        self.parent.receive_table.setUpdatesEnabled(False)
        self.parent.receive_table.setRowCount(0)
        self.parent.setup_receive_table()
        
        # Ensure context menu is connected
        from PyQt6.QtCore import Qt
        self.parent.receive_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        if self.parent.tracer_mode:
            # Tracer mode: only populate if we have recorded messages
            # Don't populate with all received_messages to avoid slowdown
            self._populate_tracer_mode()
        else:
            # Monitor mode: populate with all received messages
            self._populate_monitor_mode()
        
        self.parent.receive_table.setUpdatesEnabled(True)
        self.parent.tracer_controls_widget.setVisible(self.parent.tracer_mode)
    
    def _disable_split_screen_for_tracer(self):
        """Disable split-screen when entering Tracer mode"""
        # Store that split-screen was active
        self.parent._split_screen_was_active = True
        
        # Restore single screen view
        self.parent._setup_single_screen_view()
        self.parent.split_screen_mode = False
    
    def _restore_split_screen_for_monitor(self):
        """Restore split-screen when returning to Monitor mode"""
        if self.parent.can_bus_manager and len(self.parent.can_bus_manager.get_bus_names()) >= 2:
            # Re-enable split-screen with previous channels
            self.parent.split_screen_mode = True
            self.parent._setup_split_screen_view()
            self.parent._split_screen_was_active = False
    
    def _populate_tracer_mode(self):
        """Populate table in tracer mode - shows recorded messages only"""
        recorded_messages = self.parent.recording_mgr.get_recorded_messages()
        
        self.parent.logger.info(f"Populating Tracer mode with {len(recorded_messages)} recorded messages")
        
        if len(recorded_messages) == 0:
            return

        # Respect the ring-buffer limit and keep recorded indexes for playback.
        manager = self.parent.receive_table_mgr
        limit = getattr(manager, 'max_tracer_rows', 0) or 0
        start_index = 0
        if limit and len(recorded_messages) > limit:
            start_index = len(recorded_messages) - limit
            recorded_messages = recorded_messages[start_index:]

        manager.repopulate_tracer(
            self.parent.receive_table, recorded_messages, start_index=start_index
        )
    
    def _populate_monitor_mode(self):
        """Populate table in monitor mode - preserves all received messages"""
        # Clear counters to recalculate from scratch
        self.parent.message_counters.clear()
        self.parent.message_last_timestamp.clear()
        
        total_messages = len(self.parent.received_messages)
        
        self.parent.logger.info(f"Populating Monitor mode with {total_messages} received messages")
        
        if total_messages == 0:
            return
        
        id_data = {}
        
        for msg in self.parent.received_messages:
            if not self.parent.message_passes_filter(msg):
                continue
            
            counter_key = (msg.can_id, msg.source)
            
            self.parent.message_counters[counter_key] += 1
            count = self.parent.message_counters[counter_key]
            
            period_str = ""
            if counter_key in self.parent.message_last_timestamp:
                period_ms = int((msg.timestamp - self.parent.message_last_timestamp[counter_key]) * 1000)
                period_str = f"{period_ms}"
            
            self.parent.message_last_timestamp[counter_key] = msg.timestamp
            
            id_data[counter_key] = {
                'msg': msg,
                'count': count,
                'period': period_str
            }
        
        unique_ids = len(id_data)
        self.parent.receive_table.setRowCount(unique_ids)
        
        row_idx = 0
        for (can_id, source), data in sorted(id_data.items(), key=lambda x: (x[0][0], x[0][1])):
            msg = data['msg']
            count = data['count']
            period_str = data['period']
            
            pid_str = f"0x{can_id:03X}"
            data_str = " ".join([f"{b:02X}" for b in msg.data])
            ascii_str = msg.to_ascii()
            
            # Monitor mode columns: ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
            table_helpers.set_centered_item(self.parent.receive_table, row_idx, 0, str(row_idx + 1))  # ID (sequential)
            table_helpers.set_centered_item(self.parent.receive_table, row_idx, 1, str(count))        # Count
            table_helpers.set_centered_item(self.parent.receive_table, row_idx, 2, source)            # Channel
            self.parent.receive_table.setItem(row_idx, 3, QTableWidgetItem(pid_str))                  # PID
            table_helpers.set_centered_item(self.parent.receive_table, row_idx, 4, str(msg.dlc))      # DLC
            self.parent.receive_table.setItem(row_idx, 5, QTableWidgetItem(data_str))                 # Data
            table_helpers.set_centered_item(self.parent.receive_table, row_idx, 6, period_str)        # Period
            self.parent.receive_table.setItem(row_idx, 7, QTableWidgetItem(ascii_str))                # ASCII
            self.parent.receive_table.setItem(row_idx, 8, QTableWidgetItem(msg.comment))              # Comment
            
            row_idx += 1
