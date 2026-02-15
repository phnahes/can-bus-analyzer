"""
Monitor Panel

UI component for Monitor mode (live message viewing with statistics).
Separated from main window for better organization.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTableWidgetItem
)
from PyQt6.QtGui import QColor
from typing import Dict
from ..models import CANMessage
from .base_message_panel import BaseMessagePanel


class MonitorPanel(BaseMessagePanel):
    """Monitor mode panel component"""
    
    def __init__(self, parent=None):
        """
        Initialize monitor panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.message_rows: Dict[int, int] = {}  # CAN ID -> row mapping
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components"""
        layout = self._create_base_layout()
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.btn_pause = self._create_control_button("⏸ Pause", checkable=True)
        control_layout.addWidget(self.btn_pause)
        
        self.btn_clear = self._create_control_button("🗑 Clear")
        control_layout.addWidget(self.btn_clear)
        
        control_layout.addStretch()
        
        self.stats_label = self._create_status_label("Messages: 0 | Unique IDs: 0")
        control_layout.addWidget(self.stats_label)
        
        layout.addLayout(control_layout)
        
        # Messages table
        columns = [
            "CAN ID", "Count", "Period (ms)", "DLC", "Data", 
            "Extended", "RTR", "Source"
        ]
        column_widths = {4: 'stretch'}  # Data column stretches
        self.table = self._create_table(columns, column_widths)
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def add_or_update_message(self, msg: CANMessage, count: int, period: float = 0.0, highlight: bool = True):
        """
        Add or update a message in the monitor table.
        
        Args:
            msg: CAN message
            count: Message count for this ID
            period: Message period in milliseconds
            highlight: Whether to highlight the row
        """
        can_id = msg.can_id
        
        # Check if message already exists
        if can_id in self.message_rows:
            row = self.message_rows[can_id]
        else:
            # Create new row
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.message_rows[can_id] = row
            
            # CAN ID (only set once)
            id_format = f"0x{msg.can_id:08X}" if msg.is_extended_id else f"0x{msg.can_id:03X}"
            self.table.setItem(row, 0, QTableWidgetItem(id_format))
        
        # Update dynamic fields
        self.table.setItem(row, 1, QTableWidgetItem(str(count)))
        
        # Period
        if period > 0:
            self.table.setItem(row, 2, QTableWidgetItem(f"{period:.1f}"))
        else:
            self.table.setItem(row, 2, QTableWidgetItem("-"))
        
        # DLC
        self.table.setItem(row, 3, QTableWidgetItem(str(msg.dlc)))
        
        # Data
        self.table.setItem(row, 4, QTableWidgetItem(msg.to_hex_string()))
        
        # Extended
        self.table.setItem(row, 5, QTableWidgetItem("Yes" if msg.is_extended_id else "No"))
        
        # RTR
        self.table.setItem(row, 6, QTableWidgetItem("Yes" if msg.is_remote_frame else "No"))
        
        # Source
        source = getattr(msg, 'source', 'N/A')
        self.table.setItem(row, 7, QTableWidgetItem(source))
        
        # Highlight if requested
        if highlight:
            self.highlight_row(row, QColor(200, 255, 200))
    
    def clear(self):
        """Clear all messages from the table"""
        super().clear()
        self.message_rows.clear()
    
    def get_unique_id_count(self) -> int:
        """Get number of unique CAN IDs"""
        return len(self.message_rows)
    
    def update_stats(self, total_messages: int, unique_ids: int):
        """Update statistics label"""
        self.stats_label.setText(f"Messages: {total_messages} | Unique IDs: {unique_ids}")
