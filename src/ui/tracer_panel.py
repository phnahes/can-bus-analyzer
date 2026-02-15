"""
Tracer Panel

UI component for Tracer mode (recording and playback).
Separated from main window for better organization.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTableWidgetItem
)
from PyQt6.QtGui import QColor
from typing import List
from ..models import CANMessage
from .base_message_panel import BaseMessagePanel


class TracerPanel(BaseMessagePanel):
    """Tracer mode panel component"""
    
    def __init__(self, parent=None):
        """
        Initialize tracer panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components"""
        layout = self._create_base_layout()
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.btn_record = self._create_control_button("⏺ Record", checkable=True)
        control_layout.addWidget(self.btn_record)
        
        self.btn_play = self._create_control_button("▶ Play")
        control_layout.addWidget(self.btn_play)
        
        self.btn_stop = self._create_control_button("⏹ Stop")
        control_layout.addWidget(self.btn_stop)
        
        self.btn_clear = self._create_control_button("🗑 Clear")
        control_layout.addWidget(self.btn_clear)
        
        control_layout.addStretch()
        
        self.status_label = self._create_status_label("Ready")
        control_layout.addWidget(self.status_label)
        
        layout.addLayout(control_layout)
        
        # Messages table
        columns = ["Timestamp", "Source", "CAN ID", "DLC", "Data", "Extended", "RTR"]
        column_widths = {4: 'stretch'}  # Data column stretches
        self.table = self._create_table(columns, column_widths)
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def add_message(self, msg: CANMessage, highlight: bool = True):
        """
        Add a message to the tracer table.
        
        Args:
            msg: CAN message to add
            highlight: Whether to highlight the row
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Timestamp
        self.table.setItem(row, 0, QTableWidgetItem(f"{msg.timestamp:.6f}"))
        
        # Source
        source = getattr(msg, 'source', 'N/A')
        self.table.setItem(row, 1, QTableWidgetItem(source))
        
        # CAN ID
        id_format = f"0x{msg.can_id:08X}" if msg.is_extended_id else f"0x{msg.can_id:03X}"
        self.table.setItem(row, 2, QTableWidgetItem(id_format))
        
        # DLC
        self.table.setItem(row, 3, QTableWidgetItem(str(msg.dlc)))
        
        # Data
        self.table.setItem(row, 4, QTableWidgetItem(msg.to_hex_string()))
        
        # Extended
        self.table.setItem(row, 5, QTableWidgetItem("Yes" if msg.is_extended_id else "No"))
        
        # RTR
        self.table.setItem(row, 6, QTableWidgetItem("Yes" if msg.is_remote_frame else "No"))
        
        # Highlight if requested
        if highlight:
            self.highlight_row(row, QColor(255, 255, 200))
        
        # Auto-scroll to bottom
        self.scroll_to_bottom()
