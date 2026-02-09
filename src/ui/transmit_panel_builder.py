"""
Transmit Panel Builder

Builds the transmit panel UI with table and controls.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QPushButton, QLabel, QLineEdit, QSpinBox, QCheckBox, 
    QComboBox, QWidget, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TransmitPanelBuilder:
    """Builds transmit panel UI"""
    
    @staticmethod
    def create_panel(parent, colors, callbacks) -> QGroupBox:
        """
        Create transmit panel with message list and controls
        
        Args:
            parent: Parent window
            colors: Color dictionary
            callbacks: Dictionary with callback functions
            
        Returns:
            QGroupBox with transmit panel
        """
        from ..i18n import t
        
        transmit_group = QGroupBox("Transmit")
        transmit_layout = QVBoxLayout()
        
        # Create table
        transmit_table = TransmitPanelBuilder._create_table(parent, callbacks)
        transmit_layout.addWidget(transmit_table)
        
        # Create controls
        tx_controls = TransmitPanelBuilder._create_controls(parent, colors, callbacks)
        transmit_layout.addWidget(tx_controls)
        
        transmit_group.setLayout(transmit_layout)
        return transmit_group, transmit_table
    
    @staticmethod
    def _create_table(parent, callbacks):
        """Create transmit table"""
        from ..i18n import t
        
        table = QTableWidget()
        table.setColumnCount(18)
        table.setHorizontalHeaderLabels([
            'PID', 'DLC', 'RTR', 'Period', 'TX Mode', 'Trigger ID', 'Trigger Data',
            'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'Count', 'Comment', t('col_channel')
        ])
        
        table.itemDoubleClicked.connect(callbacks['load_to_edit'])
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(callbacks['show_context_menu'])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        font_tx = QFont("Courier New", 12)
        table.setFont(font_tx)
        
        header_tx = table.horizontalHeader()
        header_tx.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        header_tx.resizeSection(0, 70)
        header_tx.resizeSection(1, 50)
        header_tx.resizeSection(2, 50)
        header_tx.resizeSection(3, 70)
        header_tx.resizeSection(4, 80)
        header_tx.resizeSection(5, 80)
        header_tx.resizeSection(6, 100)
        for i in range(7, 15):
            header_tx.resizeSection(i, 40)
        header_tx.resizeSection(15, 60)
        header_tx.resizeSection(16, 150)
        header_tx.resizeSection(17, 70)
        
        return table
    
    @staticmethod
    def _create_controls(parent, colors, callbacks):
        """Create transmit controls"""
        from ..i18n import t
        
        tx_controls = QWidget()
        tx_controls_layout = QVBoxLayout(tx_controls)
        
        # Row 1: PID, DLC, Data, Period
        row1, data_bytes = TransmitPanelBuilder._create_row1(parent, colors, callbacks)
        tx_controls_layout.addLayout(row1)
        
        # Row 2: Options, Comment, Source
        row2 = TransmitPanelBuilder._create_row2(parent, colors)
        tx_controls_layout.addLayout(row2)
        
        # Row 3: TX Mode, Trigger ID, Trigger Data
        row3 = TransmitPanelBuilder._create_row3(parent, colors)
        tx_controls_layout.addLayout(row3)
        
        # Row 4: Buttons
        row4 = TransmitPanelBuilder._create_row4(parent, colors, callbacks)
        tx_controls_layout.addLayout(row4)
        
        return tx_controls
    
    @staticmethod
    def _create_row1(parent, colors, callbacks):
        """Create row 1: PID, DLC, Data, Period"""
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("PID:"))
        parent.tx_id_input = QLineEdit("000")
        parent.tx_id_input.setMaximumWidth(80)
        parent.tx_id_input.setPlaceholderText("000")
        row1.addWidget(parent.tx_id_input)
        
        row1.addWidget(QLabel("│"))
        
        row1.addWidget(QLabel("DLC:"))
        parent.tx_dlc_input = QSpinBox()
        parent.tx_dlc_input.setRange(0, 8)
        parent.tx_dlc_input.setValue(8)
        parent.tx_dlc_input.setMaximumWidth(60)
        parent.tx_dlc_input.valueChanged.connect(callbacks['on_dlc_changed'])
        row1.addWidget(parent.tx_dlc_input)
        
        row1.addWidget(QLabel("│"))
        row1.addWidget(QLabel("Data:"))
        
        parent.tx_data_bytes = []
        for i in range(8):
            byte_input = QLineEdit("00")
            byte_input.setMaximumWidth(35)
            byte_input.setMaxLength(2)
            byte_input.setInputMask("HH")
            byte_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            parent.tx_data_bytes.append(byte_input)
            row1.addWidget(byte_input)
        
        row1.addWidget(QLabel("│"))
        row1.addWidget(QLabel("Period:"))
        parent.tx_period_input = QLineEdit("0")
        parent.tx_period_input.setMaximumWidth(70)
        parent.tx_period_input.setPlaceholderText("ms")
        row1.addWidget(parent.tx_period_input)
        
        row1.addStretch()
        return row1, parent.tx_data_bytes
    
    @staticmethod
    def _create_row2(parent, colors):
        """Create row 2: Options, Comment, Source"""
        from ..i18n import t
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Options:"))
        
        parent.tx_29bit_check = QCheckBox("29 Bit")
        row2.addWidget(parent.tx_29bit_check)
        
        parent.tx_rtr_check = QCheckBox("RTR")
        parent.tx_rtr_check.setToolTip("Remote Transmission Request - solicita dados sem enviar payload")
        parent.tx_rtr_check.stateChanged.connect(parent.on_rtr_changed)
        row2.addWidget(parent.tx_rtr_check)
        
        row2.addWidget(QLabel("│"))
        row2.addWidget(QLabel("Comment:"))
        parent.tx_comment_input = QLineEdit()
        parent.tx_comment_input.setPlaceholderText("Optional description")
        row2.addWidget(parent.tx_comment_input)
        
        row2.addWidget(QLabel("│"))
        row2.addWidget(QLabel(f"{t('col_channel')}:"))
        parent.tx_source_combo = QComboBox()
        parent.tx_source_combo.addItem("CAN1")
        parent.tx_source_combo.setMaximumWidth(100)
        row2.addWidget(parent.tx_source_combo)
        
        row2.addStretch()
        return row2
    
    @staticmethod
    def _create_row3(parent, colors):
        """Create row 3: TX Mode, Trigger ID, Trigger Data"""
        row3 = QHBoxLayout()
        
        row3.addWidget(QLabel("TX Mode:"))
        parent.tx_mode_combo = QComboBox()
        parent.tx_mode_combo.addItems(["off", "on", "trigger"])
        parent.tx_mode_combo.setCurrentText("on")  # Default to "on"
        parent.tx_mode_combo.setMaximumWidth(100)
        row3.addWidget(parent.tx_mode_combo)
        
        row3.addWidget(QLabel("│"))
        row3.addWidget(QLabel("Trigger ID:"))
        parent.trigger_id_input = QLineEdit("")
        parent.trigger_id_input.setMaximumWidth(80)
        parent.trigger_id_input.setPlaceholderText("000")
        row3.addWidget(parent.trigger_id_input)
        
        row3.addWidget(QLabel("Trigger Data:"))
        parent.trigger_data_input = QLineEdit("")
        parent.trigger_data_input.setMaximumWidth(200)
        parent.trigger_data_input.setPlaceholderText("00 00 00 00 00 00 00 00")
        row3.addWidget(parent.trigger_data_input)
        
        row3.addStretch()
        return row3
    
    @staticmethod
    def _create_row4(parent, colors, callbacks):
        """Create row 4: Buttons"""
        row4 = QHBoxLayout()
        
        parent.btn_add = QPushButton("Add")
        parent.btn_add.clicked.connect(callbacks['add_message'])
        row4.addWidget(parent.btn_add)
        
        parent.btn_delete = QPushButton("Delete")
        parent.btn_delete.clicked.connect(callbacks['delete_message'])
        row4.addWidget(parent.btn_delete)
        
        parent.btn_clear = QPushButton("Clear")
        parent.btn_clear.clicked.connect(callbacks['clear_fields'])
        row4.addWidget(parent.btn_clear)
        
        row4.addWidget(QLabel("|"))
        
        parent.btn_single = QPushButton("Send")
        parent.btn_single.clicked.connect(callbacks['send_single'])
        row4.addWidget(parent.btn_single)
        
        parent.btn_send_all = QPushButton("Send All")
        parent.btn_send_all.clicked.connect(callbacks['send_all'])
        row4.addWidget(parent.btn_send_all)
        
        row4.addStretch()
        
        parent.btn_save_transmit = QPushButton("💾 Save")
        parent.btn_save_transmit.clicked.connect(callbacks['save_list'])
        parent.btn_save_transmit.setToolTip("Save transmit list to file")
        row4.addWidget(parent.btn_save_transmit)
        
        parent.btn_load_transmit = QPushButton("📂 Load")
        parent.btn_load_transmit.clicked.connect(callbacks['load_list'])
        parent.btn_load_transmit.setToolTip("Load transmit list from file")
        row4.addWidget(parent.btn_load_transmit)
        
        return row4
