"""
Receive Table Component - Manages the main CAN message display table
Extracted from main_window.py to reduce complexity
"""
from typing import List, Optional, Dict
from collections import defaultdict
from datetime import datetime
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                             QApplication, QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from ..models.can_message import CANMessage
from . import table_helpers


class ReceiveTable:
    """Manages the receive table display and interactions"""
    
    def __init__(self, table_widget: QTableWidget, tracer_mode: bool = False):
        """
        Initialize receive table manager
        
        Args:
            table_widget: QTableWidget to manage
            tracer_mode: True for Tracer mode, False for Monitor mode
        """
        self.table = table_widget
        self.tracer_mode = tracer_mode
        
        # Data tracking
        self.message_counters: Dict[tuple, int] = defaultdict(int)
        self.message_last_timestamp: Dict[tuple, float] = {}
        
        # Setup table
        self._setup_table()
    
    def _setup_table(self):
        """Setup table columns and appearance"""
        # Set font
        font = QFont("Courier New", 14)
        self.table.setFont(font)
        
        # Hide vertical header
        self.table.verticalHeader().setVisible(False)
        
        # Enable selection
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Configure columns based on mode
        if self.tracer_mode:
            self._setup_tracer_columns()
        else:
            self._setup_monitor_columns()
    
    def _setup_tracer_columns(self):
        """Setup columns for Tracer mode"""
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Time", "Channel", "PID", "DLC", "Data", "ASCII", "Comment"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Time
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Channel
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # PID
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # DLC
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Data
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # ASCII
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)          # Comment
    
    def _setup_monitor_columns(self):
        """Setup columns for Monitor mode"""
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Count", "Channel", "PID", "DLC", "Data", "Period", "ASCII", "Comment"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Count
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Channel
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # PID
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # DLC
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Data
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Period
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # ASCII
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)          # Comment
    
    def switch_mode(self, tracer_mode: bool):
        """
        Switch between Tracer and Monitor mode
        
        Args:
            tracer_mode: True for Tracer, False for Monitor
        """
        self.tracer_mode = tracer_mode
        self.table.setRowCount(0)
        self._setup_table()
    
    def add_tracer_message(self, row_idx: int, msg: CANMessage):
        """
        Add message in Tracer mode
        
        Args:
            row_idx: Row index
            msg: CAN message
        """
        dt = datetime.fromtimestamp(msg.timestamp)
        time_str = dt.strftime("%S.%f")[:-3]
        pid_str = table_helpers.format_can_id(msg.can_id, msg.is_extended_id)
        data_str = table_helpers.format_data_bytes(msg.data)
        ascii_str = table_helpers.format_ascii(msg.data)
        
        # Create items
        id_item = table_helpers.create_centered_item(str(row_idx + 1), user_data=row_idx)
        dlc_item = table_helpers.create_centered_item(str(msg.dlc))
        channel_item = table_helpers.create_centered_item(msg.source)
        
        # Set items
        self.table.setItem(row_idx, 0, id_item)
        self.table.setItem(row_idx, 1, QTableWidgetItem(time_str))
        self.table.setItem(row_idx, 2, channel_item)
        self.table.setItem(row_idx, 3, QTableWidgetItem(pid_str))
        self.table.setItem(row_idx, 4, dlc_item)
        self.table.setItem(row_idx, 5, QTableWidgetItem(data_str))
        self.table.setItem(row_idx, 6, QTableWidgetItem(ascii_str))
        self.table.setItem(row_idx, 7, QTableWidgetItem(msg.comment))
    
    def add_monitor_message(self, msg: CANMessage, highlight: bool = True) -> int:
        """
        Add or update message in Monitor mode
        
        Args:
            msg: CAN message
            highlight: Whether to highlight the row
            
        Returns:
            Row index where message was added/updated
        """
        counter_key = (msg.can_id, msg.source)
        
        # Increment counter
        self.message_counters[counter_key] += 1
        count = self.message_counters[counter_key]
        
        # Calculate period
        period_str = ""
        if counter_key in self.message_last_timestamp:
            period_ms = int((msg.timestamp - self.message_last_timestamp[counter_key]) * 1000)
            period_str = f"{period_ms}"
        
        # Update timestamp
        self.message_last_timestamp[counter_key] = msg.timestamp
        
        # Find existing row or create new
        row_idx = self._find_row_by_id_and_channel(msg.can_id, msg.source)
        
        if row_idx == -1:
            # Add new row
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
        
        # Format data
        pid_str = table_helpers.format_can_id(msg.can_id, msg.is_extended_id)
        data_str = table_helpers.format_data_bytes(msg.data)
        ascii_str = table_helpers.format_ascii(msg.data)
        
        # Create items
        id_item = table_helpers.create_centered_item(str(row_idx + 1))
        count_item = table_helpers.create_centered_item(str(count))
        channel_item = table_helpers.create_centered_item(msg.source)
        dlc_item = table_helpers.create_centered_item(str(msg.dlc))
        period_item = table_helpers.create_centered_item(period_str)
        
        # Set items
        self.table.setItem(row_idx, 0, id_item)
        self.table.setItem(row_idx, 1, count_item)
        self.table.setItem(row_idx, 2, channel_item)
        self.table.setItem(row_idx, 3, QTableWidgetItem(pid_str))
        self.table.setItem(row_idx, 4, dlc_item)
        self.table.setItem(row_idx, 5, QTableWidgetItem(data_str))
        self.table.setItem(row_idx, 6, period_item)
        self.table.setItem(row_idx, 7, QTableWidgetItem(ascii_str))
        self.table.setItem(row_idx, 8, QTableWidgetItem(msg.comment))
        
        # Highlight if requested
        if highlight:
            self._highlight_row(row_idx)
        
        return row_idx
    
    def _find_row_by_id_and_channel(self, can_id: int, channel: str) -> int:
        """
        Find row by CAN ID and channel
        
        Args:
            can_id: CAN ID to find
            channel: Channel name
            
        Returns:
            Row index or -1 if not found
        """
        pid_str = table_helpers.format_can_id(can_id, False)
        
        for row in range(self.table.rowCount()):
            pid_item = self.table.item(row, 3)
            channel_item = self.table.item(row, 2)
            
            if pid_item and channel_item:
                if pid_item.text() == pid_str and channel_item.text() == channel:
                    return row
        
        return -1
    
    def _highlight_row(self, row_idx: int):
        """Highlight a row temporarily"""
        highlight_color = QColor(255, 255, 200)  # Light yellow
        
        for col in range(self.table.columnCount()):
            item = self.table.item(row_idx, col)
            if item:
                item.setBackground(highlight_color)
    
    def clear(self):
        """Clear table and reset counters"""
        self.table.setRowCount(0)
        self.message_counters.clear()
        self.message_last_timestamp.clear()
    
    def get_selected_rows(self) -> List[int]:
        """Get list of selected row indices"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        return sorted(list(selected_rows))
    
    def get_message_at_row(self, row_idx: int) -> Optional[Dict]:
        """
        Get message data at specific row
        
        Args:
            row_idx: Row index
            
        Returns:
            Dictionary with message data or None
        """
        if row_idx < 0 or row_idx >= self.table.rowCount():
            return None
        
        # Extract data from row
        if self.tracer_mode:
            # Tracer mode columns: ID, Time, Channel, PID, DLC, Data, ASCII, Comment
            return {
                'row_id': self.table.item(row_idx, 0).text() if self.table.item(row_idx, 0) else "",
                'time': self.table.item(row_idx, 1).text() if self.table.item(row_idx, 1) else "",
                'channel': self.table.item(row_idx, 2).text() if self.table.item(row_idx, 2) else "",
                'pid': self.table.item(row_idx, 3).text() if self.table.item(row_idx, 3) else "",
                'dlc': self.table.item(row_idx, 4).text() if self.table.item(row_idx, 4) else "",
                'data': self.table.item(row_idx, 5).text() if self.table.item(row_idx, 5) else "",
                'ascii': self.table.item(row_idx, 6).text() if self.table.item(row_idx, 6) else "",
                'comment': self.table.item(row_idx, 7).text() if self.table.item(row_idx, 7) else ""
            }
        else:
            # Monitor mode columns: ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
            return {
                'row_id': self.table.item(row_idx, 0).text() if self.table.item(row_idx, 0) else "",
                'count': self.table.item(row_idx, 1).text() if self.table.item(row_idx, 1) else "",
                'channel': self.table.item(row_idx, 2).text() if self.table.item(row_idx, 2) else "",
                'pid': self.table.item(row_idx, 3).text() if self.table.item(row_idx, 3) else "",
                'dlc': self.table.item(row_idx, 4).text() if self.table.item(row_idx, 4) else "",
                'data': self.table.item(row_idx, 5).text() if self.table.item(row_idx, 5) else "",
                'period': self.table.item(row_idx, 6).text() if self.table.item(row_idx, 6) else "",
                'ascii': self.table.item(row_idx, 7).text() if self.table.item(row_idx, 7) else "",
                'comment': self.table.item(row_idx, 8).text() if self.table.item(row_idx, 8) else ""
            }
    
    def apply_filter(self, filter_func):
        """
        Apply filter to table rows
        
        Args:
            filter_func: Function that takes row_idx and returns True to show row
        """
        for row in range(self.table.rowCount()):
            should_show = filter_func(row)
            self.table.setRowHidden(row, not should_show)
    
    def get_row_count(self) -> int:
        """Get number of rows"""
        return self.table.rowCount()
    
    def get_unique_id_count(self) -> int:
        """Get number of unique CAN IDs"""
        return len(self.message_counters)
