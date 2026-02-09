"""
Transmit Panel

UI component for CAN message transmission.
Separated from main window for better organization.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QGroupBox, QHeaderView
)
from PyQt6.QtCore import Qt
from typing import List, Dict


class TransmitPanel(QWidget):
    """Transmit panel component"""
    
    def __init__(self, parent=None):
        """
        Initialize transmit panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Input group
        input_group = QGroupBox("New Message")
        input_layout = QHBoxLayout()
        
        # CAN ID
        input_layout.addWidget(QLabel("ID:"))
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("0x123")
        self.id_input.setMaximumWidth(100)
        input_layout.addWidget(self.id_input)
        
        # Extended checkbox
        self.extended_check = QCheckBox("Extended")
        input_layout.addWidget(self.extended_check)
        
        # RTR checkbox
        self.rtr_check = QCheckBox("RTR")
        input_layout.addWidget(self.rtr_check)
        
        # DLC
        input_layout.addWidget(QLabel("DLC:"))
        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 8)
        self.dlc_spin.setValue(8)
        self.dlc_spin.setMaximumWidth(60)
        input_layout.addWidget(self.dlc_spin)
        
        # Data
        input_layout.addWidget(QLabel("Data:"))
        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText("00 11 22 33 44 55 66 77")
        input_layout.addWidget(self.data_input)
        
        # Period
        input_layout.addWidget(QLabel("Period (ms):"))
        self.period_spin = QSpinBox()
        self.period_spin.setRange(0, 10000)
        self.period_spin.setValue(100)
        self.period_spin.setMaximumWidth(80)
        input_layout.addWidget(self.period_spin)
        
        # Source bus
        input_layout.addWidget(QLabel("Bus:"))
        self.source_combo = QComboBox()
        self.source_combo.setMaximumWidth(100)
        input_layout.addWidget(self.source_combo)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.btn_send = QPushButton("📤 Send")
        control_layout.addWidget(self.btn_send)
        
        self.btn_add = QPushButton("➕ Add to List")
        control_layout.addWidget(self.btn_add)
        
        self.btn_clear_fields = QPushButton("🗑 Clear Fields")
        control_layout.addWidget(self.btn_clear_fields)
        
        control_layout.addStretch()
        
        self.btn_send_all = QPushButton("📤 Send All")
        control_layout.addWidget(self.btn_send_all)
        
        self.btn_stop_all = QPushButton("⏹ Stop All")
        control_layout.addWidget(self.btn_stop_all)
        
        layout.addLayout(control_layout)
        
        # Transmit list table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "CAN ID", "DLC", "Data", "Period (ms)", "Count", 
            "Extended", "RTR", "Bus", "Actions"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def add_message_to_list(self, message_data: Dict):
        """
        Add a message to the transmit list.
        
        Args:
            message_data: Dictionary with message data
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # CAN ID
        id_str = f"0x{message_data['can_id']:X}"
        self.table.setItem(row, 0, QTableWidgetItem(id_str))
        
        # DLC
        self.table.setItem(row, 1, QTableWidgetItem(str(message_data['dlc'])))
        
        # Data
        data_str = " ".join(f"{b:02X}" for b in message_data['data'])
        self.table.setItem(row, 2, QTableWidgetItem(data_str))
        
        # Period
        self.table.setItem(row, 3, QTableWidgetItem(str(message_data.get('period', 0))))
        
        # Count
        self.table.setItem(row, 4, QTableWidgetItem("0"))
        
        # Extended
        self.table.setItem(row, 5, QTableWidgetItem("Yes" if message_data.get('extended', False) else "No"))
        
        # RTR
        self.table.setItem(row, 6, QTableWidgetItem("Yes" if message_data.get('rtr', False) else "No"))
        
        # Bus
        self.table.setItem(row, 7, QTableWidgetItem(message_data.get('bus', 'All')))
        
        # Actions (buttons will be added by parent)
        self.table.setItem(row, 8, QTableWidgetItem(""))
    
    def remove_message(self, row: int):
        """Remove a message from the list"""
        if 0 <= row < self.table.rowCount():
            self.table.removeRow(row)
    
    def clear_list(self):
        """Clear all messages from the list"""
        self.table.setRowCount(0)
    
    def update_count(self, row: int, count: int):
        """Update the count for a message"""
        if 0 <= row < self.table.rowCount():
            self.table.setItem(row, 4, QTableWidgetItem(str(count)))
    
    def get_message_data(self) -> Dict:
        """
        Get message data from input fields.
        
        Returns:
            Dictionary with message data
        """
        try:
            can_id = int(self.id_input.text(), 16)
        except:
            can_id = 0
        
        # Parse data
        data_str = self.data_input.text().replace(" ", "").replace("0x", "")
        try:
            data = bytes.fromhex(data_str)
        except:
            data = bytes([0] * self.dlc_spin.value())
        
        return {
            'id': can_id,
            'dlc': self.dlc_spin.value(),
            'data': data,
            'period': self.period_spin.value(),
            'extended': self.extended_check.isChecked(),
            'rtr': self.rtr_check.isChecked(),
            'bus': self.source_combo.currentText()
        }
    
    def clear_fields(self):
        """Clear input fields"""
        self.id_input.clear()
        self.data_input.clear()
        self.dlc_spin.setValue(8)
        self.period_spin.setValue(100)
        self.extended_check.setChecked(False)
        self.rtr_check.setChecked(False)
    
    def update_bus_list(self, buses: List[str]):
        """Update the bus selection combo"""
        current = self.source_combo.currentText()
        self.source_combo.clear()
        self.source_combo.addItems(buses)
        
        # Restore selection if possible
        index = self.source_combo.findText(current)
        if index >= 0:
            self.source_combo.setCurrentIndex(index)
