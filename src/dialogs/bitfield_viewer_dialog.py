"""
Bit Field Viewer Dialog - Visualize individual bits of a CAN message
"""

import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QFileDialog, QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt

from ..models import CANMessage
from ..theme import get_adaptive_colors, get_bit_style


class BitFieldViewerDialog(QDialog):
    """Dialog para visualizar bits individuais de uma mensagem CAN"""
    def __init__(self, parent=None, message: CANMessage = None):
        super().__init__(parent)
        self.message = message
        self.bit_labels = {}
        # Get theme from parent's config if available
        theme_pref = 'system'
        if parent and hasattr(parent, 'theme_preference'):
            theme_pref = parent.theme_preference
        self.colors = get_adaptive_colors(theme_pref)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Bit Field Viewer")
        self.setModal(False)
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Header with message information
        header_group = QGroupBox("Message Information")
        header_layout = QGridLayout()
        
        if self.message:
            header_layout.addWidget(QLabel("ID:"), 0, 0)
            header_layout.addWidget(QLabel(f"0x{self.message.can_id:03X}"), 0, 1)
            
            header_layout.addWidget(QLabel("DLC:"), 0, 2)
            header_layout.addWidget(QLabel(str(self.message.dlc)), 0, 3)
            
            header_layout.addWidget(QLabel("Data (Hex):"), 1, 0)
            data_hex = " ".join([f"{b:02X}" for b in self.message.data])
            header_layout.addWidget(QLabel(data_hex), 1, 1, 1, 3)
            
            header_layout.addWidget(QLabel("Data (Dec):"), 2, 0)
            data_dec = " ".join([f"{b:3d}" for b in self.message.data])
            header_layout.addWidget(QLabel(data_dec), 2, 1, 1, 3)
        
        header_group.setLayout(header_layout)
        layout.addWidget(header_group)
        
        # Scroll area para os bits
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Create bit visualization for each byte
        if self.message:
            for byte_idx, byte_val in enumerate(self.message.data):
                byte_group = self.create_byte_viewer(byte_idx, byte_val)
                scroll_layout.addWidget(byte_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_save_labels = QPushButton("💾 Save Labels")
        self.btn_save_labels.clicked.connect(self.save_labels)
        button_layout.addWidget(self.btn_save_labels)
        
        self.btn_load_labels = QPushButton("📂 Load Labels")
        self.btn_load_labels.clicked.connect(self.load_labels)
        button_layout.addWidget(self.btn_load_labels)
        
        button_layout.addStretch()
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
    
    def create_byte_viewer(self, byte_idx: int, byte_val: int):
        """Create visualization of one byte with its 8 bits"""
        group = QGroupBox(f"Byte {byte_idx} (0x{byte_val:02X} = {byte_val:3d})")
        layout = QGridLayout()
        
        # Header: bit numbers
        for bit in range(7, -1, -1):
            bit_label = QLabel(f"<b>Bit {bit}</b>")
            bit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(bit_label, 0, 7 - bit)
        
        # Valores dos bits (0 ou 1)
        for bit in range(7, -1, -1):
            bit_value = (byte_val >> bit) & 1
            bit_widget = QLabel(str(bit_value))
            bit_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bit_widget.setStyleSheet(get_bit_style(bit_value, self.colors))
            layout.addWidget(bit_widget, 1, 7 - bit)
        
        # Editable labels for each bit
        for bit in range(7, -1, -1):
            bit_key = f"{byte_idx}_{bit}"
            label_input = QLineEdit()
            label_input.setPlaceholderText(f"Label for bit {bit}")
            label_input.setMaximumWidth(100)
            self.bit_labels[bit_key] = label_input
            layout.addWidget(label_input, 2, 7 - bit)
        
        group.setLayout(layout)
        return group
    
    def save_labels(self):
        """Salva labels dos bits em arquivo JSON"""
        if not self.message:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Bit Labels",
            f"bit_labels_0x{self.message.can_id:03X}.json",
            "JSON Files (*.json)"
        )
        
        if filename:
            labels = {}
            for key, input_widget in self.bit_labels.items():
                text = input_widget.text()
                if text:
                    labels[key] = text
            
            data = {
                'can_id': self.message.can_id,
                'labels': labels
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            QMessageBox.information(self, "Save", f"Labels saved!")
    
    def load_labels(self):
        """Carrega labels dos bits de arquivo JSON"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Bit Labels",
            "",
            "JSON Files (*.json)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                labels = data.get('labels', {})
                for key, text in labels.items():
                    if key in self.bit_labels:
                        self.bit_labels[key].setText(text)
                
                QMessageBox.information(self, "Load", f"Labels loaded!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load labels: {str(e)}")
