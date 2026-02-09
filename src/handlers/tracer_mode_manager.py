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
        
        self.parent.tracer_mode = not self.parent.tracer_mode
        self.parent.btn_tracer.setChecked(False)
        
        if self.parent.tracer_mode:
            self.parent.btn_tracer.setText(f"📊 {t('btn_monitor')}")
        else:
            self.parent.btn_tracer.setText(f"📊 {t('btn_tracer')}")
        
        self.parent.receive_table.setUpdatesEnabled(False)
        self.parent.receive_table.setRowCount(0)
        self.parent.setup_receive_table()
        
        # Ensure context menu is connected
        from PyQt6.QtCore import Qt
        self.parent.receive_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        if self.parent.tracer_mode:
            self._populate_tracer_mode()
        else:
            self._populate_monitor_mode()
        
        self.parent.receive_table.setUpdatesEnabled(True)
        self.parent.tracer_controls_widget.setVisible(self.parent.tracer_mode)
    
    def _populate_tracer_mode(self):
        """Populate table in tracer mode"""
        recorded_messages = self.parent.recording_mgr.get_recorded_messages()
        
        if len(recorded_messages) == 0:
            return
        
        self.parent.receive_table.setRowCount(len(recorded_messages))
        
        for row_idx, msg in enumerate(recorded_messages):
            dt = datetime.fromtimestamp(msg.timestamp)
            time_str = dt.strftime("%S.%f")[:-3]
            pid_str = f"0x{msg.can_id:03X}"
            data_str = " ".join([f"{b:02X}" for b in msg.data])
            ascii_str = msg.to_ascii()
            
            id_item = table_helpers.create_centered_item(str(row_idx + 1), user_data=row_idx)
            
            self.parent.receive_table.setItem(row_idx, 0, id_item)
            self.parent.receive_table.setItem(row_idx, 1, QTableWidgetItem(time_str))
            table_helpers.set_centered_item(self.parent.receive_table, row_idx, 2, msg.source)
            
            self.parent.receive_table.setItem(row_idx, 3, QTableWidgetItem(pid_str))
            table_helpers.set_centered_item(self.parent.receive_table, row_idx, 4, str(msg.dlc))
            self.parent.receive_table.setItem(row_idx, 5, QTableWidgetItem(data_str))
            self.parent.receive_table.setItem(row_idx, 6, QTableWidgetItem(ascii_str))
            self.parent.receive_table.setItem(row_idx, 7, QTableWidgetItem(msg.comment))
    
    def _populate_monitor_mode(self):
        """Populate table in monitor mode"""
        self.parent.message_counters.clear()
        self.parent.message_last_timestamp.clear()
        
        total_messages = len(self.parent.received_messages)
        
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
