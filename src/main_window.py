"""
Main Window - CAN Analyzer main window
"""

import sys
import json
import threading
import queue
import time
from datetime import datetime
from typing import Optional, List, Dict
from collections import defaultdict
from functools import partial

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QSpinBox, QCheckBox, QComboBox, QFileDialog,
    QMessageBox, QSplitter, QGroupBox, QHeaderView, QMenu, QDialog,
    QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont, QColor, QPalette

# Internal imports
from .models import CANMessage
from .dialogs import (
    SettingsDialog, BitFieldViewerDialog, FilterDialog, TriggerDialog, 
    GatewayDialog, DecoderManagerDialog, FTCANDialog, OBD2Dialog
)
from .decoders.base import get_decoder_manager
from .decoders.adapter_ftcan import FTCANProtocolDecoder
from .decoders.adapter_obd2 import OBD2ProtocolDecoder
from .file_operations import FileOperations
from .logger import get_logger
from .i18n import get_i18n, t
from .theme import detect_dark_mode, get_adaptive_colors, should_use_dark_mode
from .utils import get_platform_display_name
from .can_bus_manager import CANBusManager, CANBusConfig
from . import __version__, __build__

# CAN imports
try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False
    print("python-can not installed. Simulation mode activated.")


class CANAnalyzerWindow(QMainWindow):
    """CAN Analyzer main window"""
    
    def __init__(self):
        super().__init__()
        
        # Logger
        self.logger = get_logger()
        self.logger.info("Initializing CANAnalyzerWindow")
        
        # Configuration Manager
        from .config_manager import get_config_manager
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_all()
        self.logger.info(f"Configuration loaded: language={self.config.get('language', 'en')}")
        
        # Application state
        self.connected = False
        self.recording = False  # Tracer only: controls whether messages are saved for playback
        self.paused = False
        self.tracer_mode = False  # Tracer Mode
        self.recorded_messages: List[CANMessage] = []  # Recorded messages for playback (Tracer)
        self.can_bus: Optional[can.BusABC] = None  # Legacy single bus (kept for compatibility)
        self.can_bus_manager: Optional[CANBusManager] = None  # Multi-CAN manager
        self.receive_thread: Optional[threading.Thread] = None
        self.message_queue = queue.Queue()
        self.received_messages: List[CANMessage] = []
        self.transmit_messages: List[Dict] = []
        self.message_counters = defaultdict(int)  # Counter per ID
        self.message_last_timestamp = {}  # Last timestamp per ID for period calculation
        
        # Protocol analyzer dialogs
        self._ftcan_dialog = None
        self._obd2_dialog = None
        
        # Playback control
        self.playback_active = False
        self.playback_paused = False
        self.playback_thread: Optional[threading.Thread] = None
        self.playback_stop_event = threading.Event()
        self.current_playback_row = -1
        
        # Message filters
        self.message_filters = {
            'enabled': False,  # IMPORTANT: Filters disabled by default
            'id_filters': [],  # Legacy: IDs without specific channel
            'data_filters': [],
            'show_only': True,
            'channel_filters': {}  # Novo: {channel_name: {'ids': [list], 'show_only': bool}}
        }
        self.logger.info(f"Message filters initialized: enabled={self.message_filters['enabled']}")
        
        # Triggers for automatic transmission
        self.triggers = []
        self.triggers_enabled = False
        
        # Periodic transmission control
        self.periodic_send_active = False
        self.periodic_send_threads = {}  # {row_index: thread}
        self.periodic_send_stop_events = {}  # {row_index: threading.Event}
        
        # Transmit editing state
        self.editing_tx_row = -1  # -1 = adding new, >= 0 = editing existing row
        
        # Split-screen mode
        self.split_screen_mode = False
        self.split_screen_left_channel = None
        self.split_screen_right_channel = None
        self.receive_table_left: Optional[QTableWidget] = None
        self.receive_table_right: Optional[QTableWidget] = None
        
        # Gateway configuration
        from .models import GatewayConfig
        self.gateway_config = GatewayConfig()
        
        # Protocol Dialog references
        self._ftcan_dialog: Optional['FTCANDialog'] = None
        self._obd2_dialog: Optional['OBD2Dialog'] = None
        
        # Protocol Decoder Manager
        self.decoder_manager = get_decoder_manager()
        self._init_protocol_decoders()
        
        # USB Device Monitor
        from .usb_device_monitor import get_usb_monitor
        self.usb_monitor = get_usb_monitor()
        self.usb_monitor.on_device_connected = self.on_usb_device_connected
        self.usb_monitor.on_device_disconnected = self.on_usb_device_disconnected
        self.usb_monitor.start_monitoring()
        
        # Detect dark mode based on user preference
        self.theme_preference = self.config.get('theme', 'system')
        self.is_dark_mode = should_use_dark_mode(self.theme_preference)
        self.logger.info(f"Theme preference: {self.theme_preference}, Dark mode: {self.is_dark_mode}")
        
        self.init_ui()
        self.start_ui_update()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"{t('app_title')} - {get_platform_display_name()}")
        self.setGeometry(100, 100, 1200, 800)
        
        # Get adaptive colors based on theme preference
        self.colors = get_adaptive_colors(self.theme_preference)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.btn_connect = QPushButton()
        self.btn_connect.clicked.connect(self.toggle_connection)
        toolbar_layout.addWidget(self.btn_connect)
        
        self.btn_disconnect = QPushButton()
        self.btn_disconnect.clicked.connect(self.disconnect)
        self.btn_disconnect.setEnabled(False)
        toolbar_layout.addWidget(self.btn_disconnect)
        
        self.btn_reset = QPushButton()
        self.btn_reset.clicked.connect(self.reset)
        toolbar_layout.addWidget(self.btn_reset)
        
        toolbar_layout.addWidget(QLabel("|"))
        
        # Pause button (temporarily disabled - logic kept)
        self.btn_pause = QPushButton()
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setVisible(False)  # Hidden for now
        toolbar_layout.addWidget(self.btn_pause)
        
        # Tracer/Monitor Mode button (toggles between the two)
        self.btn_tracer = QPushButton()
        self.btn_tracer.setCheckable(True)
        self.btn_tracer.clicked.connect(self.toggle_tracer_mode)
        toolbar_layout.addWidget(self.btn_tracer)
        
        # Separator
        toolbar_layout.addWidget(QLabel("|"))
        
        # Gateway Enable/Disable button
        self.btn_gateway = QPushButton("🌉 Gateway: OFF")
        self.btn_gateway.setCheckable(True)
        self.btn_gateway.setToolTip("Enable/Disable CAN Gateway")
        self.btn_gateway.clicked.connect(self.toggle_gateway_from_toolbar)
        self.btn_gateway.setEnabled(False)  # Enabled only when connected
        toolbar_layout.addWidget(self.btn_gateway)
        
        # Expandable space to push TX button to the right
        toolbar_layout.addStretch()
        
        # Toggle Transmit Panel button (right side)
        self.btn_toggle_transmit = QPushButton("📤 Hide TX")
        self.btn_toggle_transmit.setToolTip("Mostrar/Ocultar painel de Transmissão")
        self.btn_toggle_transmit.clicked.connect(self.toggle_transmit_panel)
        toolbar_layout.addWidget(self.btn_toggle_transmit)
        self.transmit_panel_visible = True  # Panel state
        
        main_layout.addLayout(toolbar_layout)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Receive panel
        self.receive_group = QGroupBox("Receive (Monitor)")
        receive_layout = QVBoxLayout()
        
        # Container for tables (single or split)
        self.receive_container = QWidget()
        self.receive_container_layout = QVBoxLayout(self.receive_container)
        self.receive_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main table (normal mode)
        self.receive_table = QTableWidget()
        self.setup_receive_table()
        
        # Hide vertical header (default row numbers)
        self.receive_table.verticalHeader().setVisible(False)
        
        # Larger monospace font for better readability
        font = QFont("Courier New", 14)
        self.receive_table.setFont(font)
        
        # Enable multiple selection
        self.receive_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.receive_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Context menu (right-click)
        self.receive_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.receive_table.customContextMenuRequested.connect(self.show_receive_context_menu)
        
        self.receive_container_layout.addWidget(self.receive_table)
        receive_layout.addWidget(self.receive_container)
        
        # Tracer playback controls (initially hidden)
        self.tracer_controls_widget = QWidget()
        tracer_controls_layout = QHBoxLayout(self.tracer_controls_widget)
        tracer_controls_layout.setContentsMargins(0, 5, 0, 5)
        
        # Record button (Tracer only)
        self.btn_record = QPushButton("⏺ Record")
        self.btn_record.setCheckable(True)
        self.btn_record.setToolTip("Gravar mensagens para reprodução posterior")
        self.btn_record.clicked.connect(self.toggle_recording)
        tracer_controls_layout.addWidget(self.btn_record)
        
        # Clear button (clear recorded messages)
        self.btn_clear_tracer = QPushButton("🗑 Clear")
        self.btn_clear_tracer.setToolTip("Limpar mensagens gravadas")
        self.btn_clear_tracer.clicked.connect(self.clear_tracer_messages)
        tracer_controls_layout.addWidget(self.btn_clear_tracer)
        
        tracer_controls_layout.addWidget(QLabel("|"))
        
        self.btn_play_all = QPushButton("▶ Play All")
        self.btn_play_all.setToolTip("Reproduzir (enviar) todas as mensagens gravadas")
        self.btn_play_all.clicked.connect(self.play_all_messages)
        self.btn_play_all.setEnabled(False)  # Disabled until messages are recorded
        tracer_controls_layout.addWidget(self.btn_play_all)
        
        self.btn_play_selected = QPushButton("▶ Play Selected")
        self.btn_play_selected.setToolTip("Reproduzir (enviar) apenas as mensagens selecionadas")
        self.btn_play_selected.clicked.connect(self.play_selected_message)
        self.btn_play_selected.setEnabled(False)  # Disabled until messages are recorded
        tracer_controls_layout.addWidget(self.btn_play_selected)
        
        self.btn_stop_play = QPushButton("⏹ Stop")
        self.btn_stop_play.setToolTip("Parar reprodução")
        self.btn_stop_play.clicked.connect(self.stop_playback)
        self.btn_stop_play.setEnabled(False)
        tracer_controls_layout.addWidget(self.btn_stop_play)
        
        tracer_controls_layout.addWidget(QLabel("|"))
        
        self.btn_save_trace = QPushButton("💾 Save Trace")
        self.btn_save_trace.setToolTip("Salvar trace atual")
        self.btn_save_trace.clicked.connect(self.save_log)
        tracer_controls_layout.addWidget(self.btn_save_trace)
        
        self.btn_load_trace = QPushButton("📂 Load Trace")
        self.btn_load_trace.setToolTip("Carregar trace de arquivo")
        self.btn_load_trace.clicked.connect(self.load_log)
        tracer_controls_layout.addWidget(self.btn_load_trace)
        
        tracer_controls_layout.addStretch()
        
        self.playback_label = QLabel("Ready")
        tracer_controls_layout.addWidget(self.playback_label)
        
        self.tracer_controls_widget.setVisible(False)  # Hidden by default
        receive_layout.addWidget(self.tracer_controls_widget)
        
        self.receive_group.setLayout(receive_layout)
        splitter.addWidget(self.receive_group)
        
        # Transmit panel
        self.transmit_group = QGroupBox("Transmit")
        transmit_layout = QVBoxLayout()
        
        # Table of messages to transmit
        self.transmit_table = QTableWidget()
        self.transmit_table.setColumnCount(18)
        self.transmit_table.setHorizontalHeaderLabels([
            'PID', 'DLC', 'RTR', 'Period', 'TX Mode', 'Trigger ID', 'Trigger Data',
            'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'Count', 'Comment', t('col_channel')
        ])
        
        # Double-click to load message into edit fields
        self.transmit_table.itemDoubleClicked.connect(self.load_tx_message_to_edit)
        
        # Context menu for transmit table
        self.transmit_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.transmit_table.customContextMenuRequested.connect(self.show_transmit_context_menu)
        
        # Make table readonly
        self.transmit_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Larger font for transmit table
        font_tx = QFont("Courier New", 12)
        self.transmit_table.setFont(font_tx)
        
        # Permitir redimensionamento manual de todas as colunas
        header_tx = self.transmit_table.horizontalHeader()
        header_tx.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Definir larguras iniciais apropriadas
        header_tx.resizeSection(0, 70)   # ID
        header_tx.resizeSection(1, 50)   # DLC
        header_tx.resizeSection(2, 50)   # RTR
        header_tx.resizeSection(3, 70)   # Period
        header_tx.resizeSection(4, 80)   # TX Mode
        header_tx.resizeSection(5, 80)   # Trigger ID
        header_tx.resizeSection(6, 100)  # Trigger Data
        # Data bytes (D0-D7)
        for i in range(7, 15):
            header_tx.resizeSection(i, 40)
        header_tx.resizeSection(15, 60)  # Count
        header_tx.resizeSection(16, 150) # Comment
        header_tx.resizeSection(17, 70)  # Source
        
        transmit_layout.addWidget(self.transmit_table)
        
        # Transmit controls
        tx_controls = QWidget()
        tx_controls_layout = QVBoxLayout(tx_controls)
        
        # Row 1: PID | DLC | Data | Period
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("PID:"))
        self.tx_id_input = QLineEdit("000")
        self.tx_id_input.setMaximumWidth(80)
        self.tx_id_input.setPlaceholderText("000")
        row1.addWidget(self.tx_id_input)
        
        # Visual separator
        sep1 = QLabel("│")
        sep1.setStyleSheet(self.colors['separator'])
        row1.addWidget(sep1)
        
        row1.addWidget(QLabel("DLC:"))
        self.tx_dlc_input = QSpinBox()
        self.tx_dlc_input.setRange(0, 8)
        self.tx_dlc_input.setValue(8)
        self.tx_dlc_input.setMaximumWidth(60)
        self.tx_dlc_input.valueChanged.connect(self.on_dlc_changed)
        row1.addWidget(self.tx_dlc_input)
        
        # Visual separator
        sep2 = QLabel("│")
        sep2.setStyleSheet(self.colors['separator'])
        row1.addWidget(sep2)
        
        row1.addWidget(QLabel("Data:"))
        
        # Create 8 fields for each byte (no D0, D1 labels)
        self.tx_data_bytes = []
        for i in range(8):
            byte_input = QLineEdit("00")
            byte_input.setMaximumWidth(35)
            byte_input.setMaxLength(2)
            byte_input.setInputMask("HH")  # Hexadecimal only
            byte_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tx_data_bytes.append(byte_input)
            row1.addWidget(byte_input)
        
        # Visual separator
        sep3 = QLabel("│")
        sep3.setStyleSheet(self.colors['separator'])
        row1.addWidget(sep3)
        
        row1.addWidget(QLabel("Period:"))
        self.tx_period_input = QLineEdit("0")
        self.tx_period_input.setMaximumWidth(70)
        self.tx_period_input.setPlaceholderText("ms")
        row1.addWidget(self.tx_period_input)
        
        row1.addStretch()
        tx_controls_layout.addLayout(row1)
        
        # Row 2: Options: 29 Bit, RTR | Comment
        row2 = QHBoxLayout()
        
        row2.addWidget(QLabel("Options:"))
        
        self.tx_29bit_check = QCheckBox("29 Bit")
        row2.addWidget(self.tx_29bit_check)
        
        self.tx_rtr_check = QCheckBox("RTR")
        row2.addWidget(self.tx_rtr_check)
        
        # Visual separator
        sep4 = QLabel("│")
        sep4.setStyleSheet(self.colors['separator'])
        row2.addWidget(sep4)
        
        row2.addWidget(QLabel("Comment:"))
        self.tx_comment_input = QLineEdit()
        self.tx_comment_input.setPlaceholderText("Optional description")
        row2.addWidget(self.tx_comment_input)
        
        # Visual separator
        sep_source = QLabel("│")
        sep_source.setStyleSheet(self.colors['separator'])
        row2.addWidget(sep_source)
        
        row2.addWidget(QLabel(f"{t('col_channel')}:"))
        self.tx_source_combo = QComboBox()
        self.tx_source_combo.addItem("CAN1")  # Default, updated dynamically
        self.tx_source_combo.setMaximumWidth(100)
        row2.addWidget(self.tx_source_combo)
        
        row2.addStretch()
        tx_controls_layout.addLayout(row2)
        
        # Row 3: TX Mode, Trigger ID, Trigger Data
        row3 = QHBoxLayout()
        
        row3.addWidget(QLabel("TX Mode:"))
        self.tx_mode_combo = QComboBox()
        self.tx_mode_combo.addItems(["off", "on", "trigger"])
        self.tx_mode_combo.setMaximumWidth(100)
        row3.addWidget(self.tx_mode_combo)
        
        # Visual separator
        sep5 = QLabel("│")
        sep5.setStyleSheet(self.colors['separator'])
        row3.addWidget(sep5)
        
        row3.addWidget(QLabel("Trigger ID:"))
        self.trigger_id_input = QLineEdit("")
        self.trigger_id_input.setMaximumWidth(80)
        self.trigger_id_input.setPlaceholderText("000")
        row3.addWidget(self.trigger_id_input)
        
        row3.addWidget(QLabel("Trigger Data:"))
        self.trigger_data_input = QLineEdit("")
        self.trigger_data_input.setMaximumWidth(200)
        self.trigger_data_input.setPlaceholderText("00 00 00 00 00 00 00 00")
        row3.addWidget(self.trigger_data_input)
        
        row3.addStretch()
        tx_controls_layout.addLayout(row3)
        
        # Row 4: Buttons - Add/Save, Delete, Clear | Send, Send All/Stop All [space] Save, Load
        row4 = QHBoxLayout()
        
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_tx_message)
        row4.addWidget(self.btn_add)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_tx_message)
        row4.addWidget(self.btn_delete)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_tx_fields)
        row4.addWidget(self.btn_clear)
        
        # Visual separator
        separator = QLabel("|")
        separator.setStyleSheet(f"{self.colors['separator']}; font-size: 16px; padding: 0 10px;")
        row4.addWidget(separator)
        
        self.btn_single = QPushButton("Send")
        self.btn_single.clicked.connect(self.send_single)
        row4.addWidget(self.btn_single)
        
        self.btn_send_all = QPushButton("Send All")
        self.btn_send_all.clicked.connect(self.send_all)
        row4.addWidget(self.btn_send_all)
        
        # Expandable space to push Save/Load to the right
        row4.addStretch()
        
        # File buttons on the right
        self.btn_save_transmit = QPushButton("💾 Save")
        self.btn_save_transmit.clicked.connect(self.save_transmit_list)
        self.btn_save_transmit.setToolTip("Save transmit list to file")
        row4.addWidget(self.btn_save_transmit)
        
        self.btn_load_transmit = QPushButton("📂 Load")
        self.btn_load_transmit.clicked.connect(self.load_transmit_list)
        self.btn_load_transmit.setToolTip("Load transmit list from file")
        row4.addWidget(self.btn_load_transmit)
        
        tx_controls_layout.addLayout(row4)
        
        transmit_layout.addWidget(tx_controls)
        self.transmit_group.setLayout(transmit_layout)
        splitter.addWidget(self.transmit_group)
        
        # Set splitter proportions
        splitter.setSizes([500, 300])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        status_bar_layout = QHBoxLayout()
        
        # Left side: connection and status info
        self.connection_status = QLabel("Not Connected")
        status_bar_layout.addWidget(self.connection_status)
        
        status_bar_layout.addWidget(QLabel("|"))
        
        self.device_label = QLabel()
        status_bar_layout.addWidget(self.device_label)
        
        status_bar_layout.addWidget(QLabel("|"))
        
        # Label shows CAN operation mode (Listen Only / Normal)
        self.mode_label = QLabel()
        status_bar_layout.addWidget(self.mode_label)
        
        status_bar_layout.addWidget(QLabel("|"))
        
        self.filter_status_label = QLabel("Filter: Off")
        status_bar_layout.addWidget(self.filter_status_label)
        
        status_bar_layout.addWidget(QLabel("|"))
        
        self.msg_count_label = QLabel("Messages: 0")
        status_bar_layout.addWidget(self.msg_count_label)
        
        status_bar_layout.addStretch()
        
        # Right side: notification area
        self.notification_label = QLabel("")
        self.notification_label.setStyleSheet(self.colors['notification'])
        self.notification_label.setWordWrap(True)  # Wrap line only when needed
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.notification_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        status_bar_layout.addWidget(self.notification_label)
        
        main_layout.addLayout(status_bar_layout)
        
        # Update texts with translations (AFTER creating all elements)
        self.update_ui_translations()
    
    def setup_receive_table(self):
        """Configure the receive table based on mode"""
        if self.tracer_mode:
            # Tracer mode: ID, Time, Channel, PID, DLC, Data, ASCII, Comment
            self.receive_table.setColumnCount(8)
            self.receive_table.setHorizontalHeaderLabels(['ID', 'Time', t('col_channel'), 'PID', 'DLC', 'Data', 'ASCII', 'Comment'])
            
            # Tracer mode: allow editing (Comment only)
            self.receive_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
            
            # Allow manual resize of all columns
            header = self.receive_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            
            # Set appropriate initial widths
            header.resizeSection(0, 60)   # ID (sequential)
            header.resizeSection(1, 100)  # Time
            header.resizeSection(2, 70)   # Channel
            header.resizeSection(3, 80)   # PID (CAN ID)
            header.resizeSection(4, 60)   # DLC
            header.resizeSection(5, 250)  # Data
            header.resizeSection(6, 100)  # ASCII
            header.resizeSection(7, 150)  # Comment
            
            # Allow last column to expand when space is available
            header.setStretchLastSection(True)
        else:
            # Monitor mode: ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
            self.receive_table.setColumnCount(9)
            self.receive_table.setHorizontalHeaderLabels(['ID', 'Count', t('col_channel'), 'PID', 'DLC', 'Data', 'Period', 'ASCII', 'Comment'])
            
            # Monitor mode: do not allow editing (data is updated automatically)
            self.receive_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            
            # Allow manual resize of all columns
            header = self.receive_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            
            # Set appropriate initial widths
            header.resizeSection(0, 40)   # ID (sequential)
            header.resizeSection(1, 60)   # Count
            header.resizeSection(2, 70)   # Channel
            header.resizeSection(3, 80)   # PID (CAN ID)
            header.resizeSection(4, 50)   # DLC
            header.resizeSection(5, 250)  # Data
            header.resizeSection(6, 70)   # Period
            header.resizeSection(7, 100)  # ASCII
            header.resizeSection(8, 150)  # Comment
            
            # Allow last column to expand when space is available
            header.setStretchLastSection(True)
    
    def toggle_tracer_mode(self):
        """Toggle between Tracer (chronological) and Monitor (grouped) mode.
        
        Monitor Mode: Groups by ID, shows last message, count
        Tracer Mode: Lists all messages in chronological order
        """
        # Invert logic: when clicked, activates Tracer but visually "unchecks" the button
        self.tracer_mode = not self.tracer_mode
        self.btn_tracer.setChecked(False)  # Always keep visually "unchecked"
        
        # Update button text (shows the OPPOSITE mode to switch to)
        if self.tracer_mode:
            # In Tracer, button shows "Monitor" to go back
            self.btn_tracer.setText(f"📊 {t('btn_monitor')}")
        else:
            # In Monitor, button shows "Tracer" to activate
            self.btn_tracer.setText(f"📊 {t('btn_tracer')}")
        
        # Do not clear counters or messages - only reconfigure table
        # self.message_counters.clear()  # REMOVED - keeps data
        
        # OPTIMIZATION: Disable UI updates during repopulation
        self.receive_table.setUpdatesEnabled(False)
        
        # Clear table before reconfiguring
        self.receive_table.setRowCount(0)
        
        # Reconfigure table (columns and headers)
        self.setup_receive_table()
        
        # Repopulate table with existing data (optimized)
        if self.tracer_mode:
            # Tracer mode: Repopulate ONLY with recorded messages (if any)
            if len(self.recorded_messages) > 0:
                self.receive_table.setRowCount(len(self.recorded_messages))
                
                for row_idx, msg in enumerate(self.recorded_messages):
                    dt = datetime.fromtimestamp(msg.timestamp)
                    time_str = dt.strftime("%S.%f")[:-3]
                    pid_str = f"0x{msg.can_id:03X}"
                    data_str = " ".join([f"{b:02X}" for b in msg.data])
                    ascii_str = msg.to_ascii()
                    
                    # Create items with alignment
                    id_item = QTableWidgetItem(str(row_idx + 1))
                    id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # IMPORTANT: Store the real index in recorded_messages
                    id_item.setData(Qt.ItemDataRole.UserRole, row_idx)
                    
                    dlc_item = QTableWidgetItem(str(msg.dlc))
                    dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Insert items - Tracer: ID, Time, Channel, PID, DLC, Data, ASCII, Comment
                    self.receive_table.setItem(row_idx, 0, id_item)
                    self.receive_table.setItem(row_idx, 1, QTableWidgetItem(time_str))
                    
                    # Channel column
                    channel_item = QTableWidgetItem(msg.source)
                    channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.receive_table.setItem(row_idx, 2, channel_item)
                    
                    self.receive_table.setItem(row_idx, 3, QTableWidgetItem(pid_str))
                    self.receive_table.setItem(row_idx, 4, dlc_item)
                    self.receive_table.setItem(row_idx, 5, QTableWidgetItem(data_str))
                    self.receive_table.setItem(row_idx, 6, QTableWidgetItem(ascii_str))
                    self.receive_table.setItem(row_idx, 7, QTableWidgetItem(msg.comment))
        else:
            # Monitor mode: rebuild grouped view
            # Clear counters to rebuild from scratch
            self.message_counters.clear()
            self.message_last_timestamp.clear()
            
            # OPTIMIZATION: Group messages by ID first (in memory)
            # Then insert into table at once
            total_messages = len(self.received_messages)
            
            if total_messages > 0:
                # 1. Group messages by (ID, Channel) - much faster than inserting one by one
                id_data = {}  # {(can_id, source): {'last_msg': msg, 'count': N, 'period': X}}
                
                for msg in self.received_messages:
                    # Check filter
                    if not self.message_passes_filter(msg):
                        continue
                    
                    # Unique key: (ID, Channel)
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
                    
                    # Store data (last message per ID+Channel)
                    id_data[counter_key] = {
                        'msg': msg,
                        'count': count,
                        'period': period_str
                    }
                
                # 2. Create all rows at once
                unique_ids = len(id_data)
                self.receive_table.setRowCount(unique_ids)
                
                # 3. Populate table with grouped data (sorted by PID, then Channel)
                row_idx = 0
                for (can_id, source), data in sorted(id_data.items(), key=lambda x: (x[0][0], x[0][1])):
                    msg = data['msg']
                    count = data['count']
                    period_str = data['period']
                    
                    pid_str = f"0x{can_id:03X}"
                    data_str = " ".join([f"{b:02X}" for b in msg.data])
                    ascii_str = msg.to_ascii()
                    
                    # Create items with alignment
                    id_item = QTableWidgetItem(str(row_idx + 1))
                    id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    count_item = QTableWidgetItem(str(count))
                    count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    dlc_item = QTableWidgetItem(str(msg.dlc))
                    dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    period_item = QTableWidgetItem(period_str)
                    period_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Insert items - Monitor: ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
                    self.receive_table.setItem(row_idx, 0, id_item)                              # Sequential ID
                    self.receive_table.setItem(row_idx, 1, count_item)                           # Count
                    
                    # Channel column
                    channel_item = QTableWidgetItem(msg.source)
                    channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.receive_table.setItem(row_idx, 2, channel_item)                         # Channel
                    
                    self.receive_table.setItem(row_idx, 3, QTableWidgetItem(pid_str))            # PID
                    self.receive_table.setItem(row_idx, 4, dlc_item)                             # DLC
                    self.receive_table.setItem(row_idx, 5, QTableWidgetItem(data_str))           # Data
                    self.receive_table.setItem(row_idx, 6, period_item)                          # Period
                    self.receive_table.setItem(row_idx, 7, QTableWidgetItem(ascii_str))          # ASCII
                    self.receive_table.setItem(row_idx, 8, QTableWidgetItem(msg.comment))        # Comment
                    
                    row_idx += 1
                    
                    # Process events every 100 IDs
                    if row_idx % 100 == 0:
                        QApplication.processEvents()
        
        # OPTIMIZATION: Re-enable UI updates
        self.receive_table.setUpdatesEnabled(True)
        
        # Reconfigure context menu after recreating table
        self.receive_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.receive_table.customContextMenuRequested.connect(self.show_receive_context_menu)
        
        # Reconfigure multiple selection
        self.receive_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.receive_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Show/hide playback controls (Tracer only)
        self.tracer_controls_widget.setVisible(self.tracer_mode)
        
        # Update group label
        # Find parent QGroupBox
        parent = self.receive_table.parent()
        while parent and not isinstance(parent, QGroupBox):
            parent = parent.parent()
        
        if parent and isinstance(parent, QGroupBox):
            if self.tracer_mode:
                parent.setTitle(f"{t('label_receive').replace('Monitor', 'Tracer')}")
            else:
                parent.setTitle(t('label_receive'))
    
    def update_ui_translations(self):
        """Update all UI texts with current language translations"""
        # Window title (dynamic: CAN Analyzer - macOS / Linux / Windows)
        self.setWindowTitle(f"{t('app_title')} - {get_platform_display_name()}")
        
        # Toolbar buttons
        self.btn_connect.setText(f"🔌 {t('btn_connect')}")
        self.btn_disconnect.setText(f"⏹ {t('btn_disconnect')}")
        self.btn_reset.setText(f"🔄 {t('btn_reset')}")
        self.btn_pause.setText(f"⏸ {t('btn_pause')}")
        self.btn_clear_tracer.setText(f"🗑 {t('btn_clear')}")
        self.btn_tracer.setText(f"📊 {t('btn_tracer') if not self.tracer_mode else t('btn_monitor')}")
        
        # Status label removed - notifications via statusBar()
        
        # Mode label
        if hasattr(self, 'mode_label'):
            if self.config.get('listen_only', True):
                self.mode_label.setText(t('status_listen_only'))
            else:
                self.mode_label.setText(t('status_normal'))
        
        # Device label
        if hasattr(self, 'device_label'):
            if self.connected:
                device_info = self.config.get('channel', 'can0')
                self.device_label.setText(f"{t('status_device')}: {device_info}")
            else:
                self.device_label.setText(f"{t('status_device')}: N/A")
        
        # Playback buttons (if they exist)
        if hasattr(self, 'btn_play_all'):
            self.btn_play_all.setText(f"▶ {t('btn_play_all')}")
        if hasattr(self, 'btn_play_selected'):
            self.btn_play_selected.setText(f"▶ {t('btn_play_selected')}")
        if hasattr(self, 'btn_stop_play'):
            self.btn_stop_play.setText(f"⏹ {t('btn_stop')}")
        
        # Transmit buttons
        # Transmit buttons - texts are updated dynamically
        # btn_add muda entre "Add" e "Save"
        # btn_send_all muda entre "Send All" e "Stop All"
        pass
        
        # Group boxes
        if hasattr(self, 'receive_group'):
            if self.tracer_mode:
                self.receive_group.setTitle(t('label_receive').replace('Monitor', 'Tracer'))
            else:
                self.receive_group.setTitle(t('label_receive'))
        
        if hasattr(self, 'transmit_group'):
            self.transmit_group.setTitle(t('label_transmit'))
        
        # Update menu bar
        self.create_menu_bar()
    
    def apply_theme(self, theme_preference='system'):
        """Apply theme colors to all UI elements"""
        # Update theme preference and colors
        self.theme_preference = theme_preference
        self.is_dark_mode = should_use_dark_mode(theme_preference)
        self.colors = get_adaptive_colors(theme_preference)
        
        self.logger.info(f"Applying theme: {theme_preference}, Dark mode: {self.is_dark_mode}")
        
        # Apply the theme to the application
        from .theme import apply_theme_to_app
        app = QApplication.instance()
        if app:
            apply_theme_to_app(app, theme_preference)
        
        # Apply colors to receive table
        if hasattr(self, 'receive_table'):
            for row in range(self.receive_table.rowCount()):
                for col in range(self.receive_table.columnCount()):
                    item = self.receive_table.item(row, col)
                    if item:
                        # Reset background to normal
                        item.setBackground(self.colors['normal_bg'])
                        item.setForeground(self.colors['normal_text'])
        
        # Apply colors to transmit table
        if hasattr(self, 'transmit_table'):
            for row in range(self.transmit_table.rowCount()):
                for col in range(self.transmit_table.columnCount()):
                    item = self.transmit_table.item(row, col)
                    if item:
                        # Reset background to normal
                        item.setBackground(self.colors['normal_bg'])
                        item.setForeground(self.colors['normal_text'])
        
        # Force repaint
        self.update()
        
        self.logger.info("Theme applied successfully")
    
    def create_menu_bar(self):
        """Cria a barra de menu"""
        menubar = self.menuBar()
        menubar.clear()  # Clear existing menus before recreating
        
        # File Menu
        file_menu = menubar.addMenu(t('menu_file'))
        
        # Connection submenu
        connect_action = QAction(t('menu_connect'), self)
        connect_action.setShortcut("Ctrl+O")
        connect_action.triggered.connect(self.toggle_connection)
        file_menu.addAction(connect_action)
        
        disconnect_action = QAction(t('menu_disconnect'), self)
        disconnect_action.triggered.connect(self.disconnect)
        file_menu.addAction(disconnect_action)
        
        reset_action = QAction(t('menu_reset'), self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.triggered.connect(self.reset)
        file_menu.addAction(reset_action)
        
        file_menu.addSeparator()
        
        # Monitor submenu
        file_menu.addAction("--- Monitor ---").setEnabled(False)
        
        save_monitor_action = QAction(f"💾 Save Monitor Log...", self)
        save_monitor_action.setShortcut("Ctrl+M")
        save_monitor_action.triggered.connect(self.save_monitor_log)
        file_menu.addAction(save_monitor_action)
        
        load_monitor_action = QAction(f"📂 Load Monitor Log...", self)
        load_monitor_action.setShortcut("Ctrl+Shift+M")
        load_monitor_action.triggered.connect(self.load_monitor_log)
        file_menu.addAction(load_monitor_action)
        
        file_menu.addSeparator()
        
        # Tracer submenu
        file_menu.addAction("--- Tracer ---").setEnabled(False)
        
        save_tracer_action = QAction(f"💾 Save Tracer Log...", self)
        save_tracer_action.setShortcut("Ctrl+S")
        save_tracer_action.triggered.connect(self.save_log)
        file_menu.addAction(save_tracer_action)
        
        load_tracer_action = QAction(f"📂 Load Tracer Log...", self)
        load_tracer_action.setShortcut("Ctrl+L")
        load_tracer_action.triggered.connect(self.load_log)
        file_menu.addAction(load_tracer_action)
        
        file_menu.addSeparator()
        
        # Transmit submenu
        file_menu.addAction("--- Transmit ---").setEnabled(False)
        
        save_tx_action = QAction(f"💾 Save Transmit List...", self)
        save_tx_action.setShortcut("Ctrl+Shift+S")
        save_tx_action.triggered.connect(self.save_transmit_list)
        file_menu.addAction(save_tx_action)
        
        load_tx_action = QAction(f"📂 Load Transmit List...", self)
        load_tx_action.setShortcut("Ctrl+Shift+L")
        load_tx_action.triggered.connect(self.load_transmit_list)
        file_menu.addAction(load_tx_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(t('menu_exit'), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View Menu
        view_menu = menubar.addMenu(t('menu_view'))
        
        tracer_mode_action = QAction(t('menu_tracer_mode'), self)
        tracer_mode_action.setCheckable(True)
        tracer_mode_action.setShortcut("Ctrl+T")
        tracer_mode_action.triggered.connect(self.toggle_tracer_mode)
        view_menu.addAction(tracer_mode_action)
        
        view_menu.addSeparator()
        
        split_screen_action = QAction(t('split_screen_mode'), self)
        split_screen_action.setCheckable(True)
        split_screen_action.setShortcut("Ctrl+D")
        split_screen_action.triggered.connect(self.toggle_split_screen)
        view_menu.addAction(split_screen_action)
        
        view_menu.addSeparator()
        
        toggle_tx_action = QAction("Show/Hide Transmit Panel", self)
        toggle_tx_action.setShortcut("Ctrl+Shift+T")
        toggle_tx_action.triggered.connect(self.toggle_transmit_panel)
        view_menu.addAction(toggle_tx_action)
        
        # Tools Menu
        tools_menu = menubar.addMenu(t('menu_tools'))
        
        filters_action = QAction(f"🔍 {t('menu_filters')}...", self)
        filters_action.setShortcut("Ctrl+F")
        filters_action.triggered.connect(self.show_filter_dialog)
        tools_menu.addAction(filters_action)
        
        triggers_action = QAction(f"⚡ {t('menu_triggers')}...", self)
        triggers_action.setShortcut("Ctrl+G")
        triggers_action.triggered.connect(self.show_trigger_dialog)
        tools_menu.addAction(triggers_action)
        
        tools_menu.addSeparator()
        
        # Protocol Decoders submenu
        decoders_menu = tools_menu.addMenu("Protocol Decoders")
        
        # Decoder Manager
        decoder_manager_action = QAction("Manage Decoders...", self)
        decoder_manager_action.setShortcut("Ctrl+Shift+D")
        decoder_manager_action.triggered.connect(self.show_decoder_manager)
        decoders_menu.addAction(decoder_manager_action)
        
        decoders_menu.addSeparator()
        
        # FTCAN Protocol Analyzer
        ftcan_action = QAction("FTCAN 2.0 Analyzer...", self)
        ftcan_action.setShortcut("Ctrl+Shift+F")
        ftcan_action.triggered.connect(self.show_ftcan_dialog)
        decoders_menu.addAction(ftcan_action)
        
        # OBD-II Monitor
        obd2_action = QAction("OBD-II Monitor...", self)
        obd2_action.setShortcut("Ctrl+Shift+O")
        obd2_action.triggered.connect(self.show_obd2_dialog)
        decoders_menu.addAction(obd2_action)
        
        tools_menu.addSeparator()
        
        gateway_action = QAction(f"{t('menu_gateway')}...", self)
        gateway_action.setShortcut("Ctrl+W")
        gateway_action.triggered.connect(self.show_gateway_dialog)
        tools_menu.addAction(gateway_action)
        
        tools_menu.addSeparator()
        
        stats_action = QAction(f"📊 {t('menu_statistics')}", self)
        stats_action.triggered.connect(self.show_statistics)
        tools_menu.addAction(stats_action)
        
        # Settings Menu
        settings_menu = menubar.addMenu(t('menu_settings'))
        
        settings_action = QAction("Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)
        
        # About Menu
        about_menu = menubar.addMenu("About")
        
        about_app_action = QAction("About CAN Analyzer", self)
        about_app_action.triggered.connect(self.show_about)
        about_menu.addAction(about_app_action)
        
        # # Help Menu
        # help_menu = menubar.addMenu(t('menu_help'))
        
        # about_action = QAction(t('menu_about'), self)
        # about_action.triggered.connect(self.show_about)
        # help_menu.addAction(about_action)
    
    def _on_can_message_received(self, bus_name: str, msg: CANMessage):
        """Callback when a CAN message is received from any bus"""
        # Add message to queue for UI update
        self.message_queue.put(msg)
        
        # Forward to OBD2Dialog if open
        if hasattr(self, '_obd2_dialog') and self._obd2_dialog:
            self._obd2_dialog.on_can_message(bus_name, msg)
    
    def _send_can_message(self, can_msg: 'can.Message', target_bus: str = None):
        """Send CAN message to specified bus or all buses
        
        Args:
            can_msg: python-can Message object
            target_bus: Bus name to send to (None = send to all)
        """
        if self.can_bus_manager:
            # Multi-CAN mode
            if target_bus:
                self.can_bus_manager.send_to(target_bus, can_msg)
            else:
                # Send to all connected buses
                self.can_bus_manager.send_to_all(can_msg)
        elif self.can_bus:
            # Legacy single bus mode
            self.can_bus.send(can_msg)
    
    def toggle_connection(self):
        """Conecta ou desconecta do barramento CAN"""
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        """Conecta ao barramento CAN (com suporte multi-CAN)"""
        self.logger.info("Tentando conectar ao barramento CAN")
        
        try:
            simulation_mode = self.config.get('simulation_mode', False)
            
            # Initialize CANBusManager
            self.can_bus_manager = CANBusManager(
                message_callback=self._on_can_message_received,
                logger=self.logger
            )
            
            # Load CAN buses from config
            can_buses = self.config.get('can_buses', [])
            if not can_buses:
                # Fallback to legacy single-bus config
                can_buses = [{
                    'name': 'CAN1',
                    'channel': self.config.get('channel', 'can0'),
                    'baudrate': self.config.get('baudrate', 500000),
                    'interface': 'socketcan',
                    'listen_only': self.config.get('listen_only', True)
                }]
            
            # Add all CAN buses to manager
            for bus_cfg in can_buses:
                config = CANBusConfig(
                    name=bus_cfg['name'],
                    channel=bus_cfg['channel'],
                    baudrate=bus_cfg['baudrate'],
                    listen_only=bus_cfg.get('listen_only', True),
                    interface=bus_cfg.get('interface', 'socketcan')
                )
                self.can_bus_manager.add_bus(config)
            
            # Try real connection if not in simulation mode
            if not simulation_mode and CAN_AVAILABLE:
                self.logger.info("Tentando conectar todos os barramentos CAN")
                
                try:
                    # Connect all CAN buses
                    self.can_bus_manager.connect_all(simulation=False)
                    
                    # Check if at least one bus connected successfully
                    connected_buses = [name for name in self.can_bus_manager.get_bus_names() 
                                      if self.can_bus_manager.is_bus_connected(name)]
                    
                    if connected_buses:
                        self.logger.info(f"Conexão real estabelecida: {', '.join(connected_buses)}")
                        self.connected = True
                        
                        # Update TX source combo with CONNECTED buses only
                        self.tx_source_combo.clear()
                        for bus_name in connected_buses:
                            self.tx_source_combo.addItem(bus_name)
                        
                        # Update status with detailed info for each bus
                        if len(connected_buses) > 1:
                            # Multi-CAN: Show detailed status for each channel
                            status_parts = []
                            device_parts = []
                            
                            for bus_name in connected_buses:
                                # Find bus config
                                bus_config = next((b for b in can_buses if b['name'] == bus_name), None)
                                if bus_config:
                                    is_connected = self.can_bus_manager.is_bus_connected(bus_name)
                                    status_icon = "✓" if is_connected else "✗"
                                    baudrate_kb = bus_config['baudrate'] // 1000
                                    status_parts.append(f"{bus_name}: {status_icon} {baudrate_kb}k")
                                    device_parts.append(f"{bus_name}→{bus_config['channel']}")
                            
                            self.connection_status.setText(" | ".join(status_parts))
                            self.device_label.setText(" | ".join(device_parts))
                            
                            # Notification with summary
                            first_bus = can_buses[0]
                            self.show_notification(t('notif_connected', channel=', '.join(connected_buses), baudrate=first_bus['baudrate']//1000), 5000)
                        else:
                            # Single CAN: Show simple status
                            first_bus = can_buses[0]
                            baudrate = first_bus['baudrate']
                            channel = first_bus['channel']
                            self.connection_status.setText(f"Connected: {baudrate//1000} kbit/s")
                            self.device_label.setText(f"Device: {channel}")
                            self.show_notification(t('notif_connected', channel=connected_buses[0], baudrate=baudrate//1000), 5000)
                    else:
                        raise Exception("Nenhum barramento CAN conseguiu conectar")
                    
                except Exception as e:
                    self.logger.error(f"Erro ao conectar aos dispositivos reais: {str(e)}")
                    self.logger.warning("Tentando modo simulação como fallback")
                    
                    # Ask user if they want to use simulation
                    reply = QMessageBox.question(
                        self,
                        "Connection Error",
                        f"Não foi possível conectar aos dispositivos:\n{str(e)}\n\n"
                        f"Deseja conectar em modo simulação?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.No:
                        return
                    
                    # Enable simulation mode and save to config
                    simulation_mode = True
                    self.config['simulation_mode'] = True
                    self.config_manager.save(self.config)
                    self.logger.info("Simulation mode enabled via connection error dialog")
            
            # Simulation mode
            if simulation_mode or not CAN_AVAILABLE:
                self.logger.warning("Conectando em modo simulação")
                
                # Connect all buses in simulation mode
                self.can_bus_manager.connect_all(simulation=True)
                
                if not simulation_mode:
                    QMessageBox.information(
                        self,
                        "Simulation Mode",
                        f"{t('msg_simulation_mode')}\n\n"
                        f"Para usar um dispositivo real:\n"
                        f"1. Desmarque 'Simulation Mode' nas Settings\n"
                        f"2. Selecione o dispositivo correto\n"
                        f"3. Clique em Connect novamente"
                    )
                
                self.connected = True
                bus_names = self.can_bus_manager.get_bus_names()
                baudrate = can_buses[0]['baudrate'] if can_buses else 500000
                
                # Update TX source combo with all buses in simulation
                self.tx_source_combo.clear()
                for bus_name in bus_names:
                    self.tx_source_combo.addItem(bus_name)
                
                # Update status with detailed info for simulation
                if len(bus_names) > 1:
                    # Multi-CAN simulation: Show detailed status for each channel
                    status_parts = []
                    device_parts = []
                    
                    for bus_name in bus_names:
                        # Find bus config
                        bus_config = next((b for b in can_buses if b['name'] == bus_name), None)
                        if bus_config:
                            baudrate_kb = bus_config['baudrate'] // 1000
                            status_parts.append(f"{bus_name}: SIM {baudrate_kb}k")
                            device_parts.append(f"{bus_name}→{bus_config['channel']} (Sim)")
                    
                    self.connection_status.setText(" | ".join(status_parts))
                    self.device_label.setText(" | ".join(device_parts))
                else:
                    # Single CAN simulation
                    self.connection_status.setText(f"Simulation: {baudrate//1000} kbit/s")
                    device_info = can_buses[0]['channel'] if can_buses else 'can0'
                    self.device_label.setText(f"Device: {device_info} (Sim)")
                
                self.show_notification(t('notif_simulation_mode', baudrate=baudrate//1000), 5000)
            
            # Common settings
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.btn_pause.setEnabled(True)
            
            # Enable Gateway button if 2+ buses
            if self.can_bus_manager and len(self.can_bus_manager.get_bus_names()) >= 2:
                self.btn_gateway.setEnabled(True)
                self.update_gateway_button_state()
            
            # Update mode label
            if self.config.get('listen_only', True):
                self.mode_label.setText(t('status_listen_only'))
            else:
                self.mode_label.setText(t('status_normal'))
            
            # Start receive thread (legacy single-CAN mode only)
            # Multi-CAN uses its own threads in each CANBusInstance
            if not self.can_bus_manager and self.can_bus:
                self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
                self.receive_thread.start()
                self.logger.info("Thread de recepção iniciada (legacy mode)")
            elif self.can_bus_manager:
                self.logger.info("Usando threads de recepção do CANBusManager")
            
            # Generate sample data in simulation mode only
            if simulation_mode or not CAN_AVAILABLE:
                self.generate_sample_data()
            
            self.logger.info("Conexão estabelecida com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Connection Error", f"Erro ao conectar: {str(e)}")
    
    def disconnect(self):
        """Disconnect from CAN bus"""
        self.logger.info("Desconectando do barramento CAN")
        
        self.connected = False
        
        # Stop periodic send if active
        if self.periodic_send_active:
            self.stop_all()
        
        # Stop recording if active
        if self.recording:
            self.btn_record.setChecked(False)
            self.toggle_recording()
        
        # Disconnect all CAN buses
        if self.can_bus_manager:
            try:
                self.can_bus_manager.disconnect_all()
            except Exception as e:
                self.logger.warning(f"Erro ao fechar interfaces CAN (ignorado): {e}")
            finally:
                self.can_bus_manager = None
                self.logger.info("Todas as interfaces CAN encerradas")
        
        # Legacy single bus support
        if self.can_bus:
            try:
                self.can_bus.shutdown()
            except Exception as e:
                self.logger.warning(f"Erro ao fechar interface CAN (ignorado): {e}")
            finally:
                self.can_bus = None
        
        self.connection_status.setText("Not Connected")
        self.device_label.setText("Device: N/A")
        self.show_notification(t('notif_disconnected'), 3000)
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_gateway.setEnabled(False)  # Disable Gateway on disconnect
        
        # Reset mode label on disconnect
        if self.config.get('listen_only', True):
            self.mode_label.setText("Listen Only Mode")
        else:
            self.mode_label.setText("Normal Mode")
    
    def reset(self):
        """Reset the application without dropping the connection"""
        # Clear table(s)
        self.receive_table.setRowCount(0)
        
        # Clear split-screen tables if they exist
        if self.split_screen_mode:
            if self.receive_table_left:
                self.receive_table_left.setRowCount(0)
            if self.receive_table_right:
                self.receive_table_right.setRowCount(0)
        
        # Clear data
        self.received_messages.clear()
        self.message_counters.clear()
        self.message_last_timestamp.clear()
        
        # Clear recorded messages (Tracer)
        self.recorded_messages.clear()
        
        # Reset playback buttons
        if hasattr(self, 'btn_play_all'):
            self.btn_play_all.setEnabled(False)
            self.btn_play_selected.setEnabled(False)
        
        # Stop recording if active
        if self.recording:
            self.btn_record.setChecked(False)
            self.btn_record.setText("⏺ Record")
            self.btn_record.setStyleSheet("")
            self.recording = False
        
        self.update_message_count()
        self.show_notification(t('notif_reset'))
    
    def toggle_recording(self):
        """Start/stop recording messages for playback (Tracer only)"""
        self.recording = self.btn_record.isChecked()
        
        if self.recording:
            # Start recording
            self.recorded_messages.clear()  # Clear previous recordings
            self.receive_table.setRowCount(0)  # Clear table
            self.btn_record.setText("⏺ Recording")
            self.btn_record.setStyleSheet(self.colors['record_active'])
            self.btn_play_all.setEnabled(False)
            self.btn_play_selected.setEnabled(False)
            self.show_notification(t('notif_recording_started'), 3000)
        else:
            # Stop recording
            self.btn_record.setText("⏺ Record")
            self.btn_record.setStyleSheet("")
            
            # Do not clear table - keep recorded messages visible for replay
            
            # Enable playback buttons if there are recorded messages
            if len(self.recorded_messages) > 0:
                self.btn_play_all.setEnabled(True)
                self.btn_play_selected.setEnabled(True)
                self.show_notification(t('notif_recording_stopped', count=len(self.recorded_messages)), 3000)
            else:
                self.show_notification(t('notif_recording_stopped_empty'), 3000)
    
    def toggle_transmit_panel(self):
        """Show/hide the Transmit panel"""
        self.transmit_panel_visible = not self.transmit_panel_visible
        
        if self.transmit_panel_visible:
            # Show panel
            self.transmit_group.setVisible(True)
            self.btn_toggle_transmit.setText("📤 Hide TX")
            self.show_notification(t('notif_tx_panel_visible'), 2000)
        else:
            # Hide panel
            self.transmit_group.setVisible(False)
            self.btn_toggle_transmit.setText("📤 Show TX")
            self.show_notification(t('notif_tx_panel_hidden'), 2000)
    
    def show_notification(self, message: str, duration: int = 3000):
        """Show temporary notification in the bottom-right corner"""
        self.notification_label.setText(message)
        
        # Create timer to clear notification
        QTimer.singleShot(duration, lambda: self.notification_label.setText(""))
    
    def clear_tracer_messages(self):
        """Clear recorded messages in Tracer"""
        self.recorded_messages.clear()
        self.receive_table.setRowCount(0)
        self.btn_play_all.setEnabled(False)
        self.btn_play_selected.setEnabled(False)
        self.show_notification(t('notif_recorded_cleared'))
    
    def toggle_pause(self):
        """Pause/resume display"""
        self.paused = not self.paused
        if self.paused:
            self.btn_pause.setText("▶ Resume")
            self.btn_pause.setStyleSheet(self.colors['pause_active'])
        else:
            self.btn_pause.setText("⏸ Pause")
            self.btn_pause.setStyleSheet("")
    
    def clear_receive(self):
        """Clear the receive table (and split-screen if active)"""
        self.receive_table.setRowCount(0)
        
        # Clear split-screen tables if they exist
        if self.split_screen_mode:
            if self.receive_table_left:
                self.receive_table_left.setRowCount(0)
            if self.receive_table_right:
                self.receive_table_right.setRowCount(0)
        
        self.update_message_count()
    
    def receive_loop(self):
        """CAN message receive loop"""
        while self.connected:
            try:
                if self.can_bus:
                    message = self.can_bus.recv(timeout=0.1)
                    if message:
                        can_msg = CANMessage(
                            timestamp=message.timestamp,
                            can_id=message.arbitration_id,
                            dlc=message.dlc,
                            data=message.data,
                            comment=""
                        )
                        self.message_queue.put(can_msg)
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Erro na recepção: {e}")
                time.sleep(0.1)
    
    def generate_sample_data(self):
        """Gera dados de exemplo"""
        sample_messages = [
            (0x280, 8, bytes([0xBB, 0x8E, 0x00, 0x00, 0x29, 0xFA, 0x29, 0x29]), ""),
            (0x284, 6, bytes([0x06, 0x06, 0x00, 0x00, 0x00, 0x00]), ""),
            (0x286, 8, bytes([0xE8, 0x33, 0xD5, 0x00, 0x00, 0x75, 0x65, 0x5F]), ""),
            (0x288, 8, bytes([0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0xFE]), ""),
            (0x480, 8, bytes([0x54, 0x80, 0x00, 0x00, 0x19, 0x41, 0x00, 0x20]), ""),
            (0x4C5, 8, bytes([0xF7, 0x2C, 0x00, 0x00, 0x15, 0x41, 0x00, 0x20]), ""),
            (0x680, 8, bytes([0x81, 0x00, 0x00, 0x7F, 0x00, 0xF0, 0x47, 0x01]), ""),
            (0x688, 8, bytes([0x1B, 0x00, 0x7E, 0x00, 0x00, 0x80, 0x00, 0x00]), ""),
        ]
        
        for can_id, dlc, data, comment in sample_messages:
            msg = CANMessage(
                timestamp=time.time(),
                can_id=can_id,
                dlc=dlc,
                data=data,
                comment=comment
            )
            self.message_queue.put(msg)
            time.sleep(0.08)
    
    def start_ui_update(self):
        """Start timer for UI updates"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)  # Atualiza a cada 50ms
    
    def update_ui(self):
        """Atualiza a interface com novas mensagens"""
        if self.paused:
            return
        
        try:
            while not self.message_queue.empty():
                msg = self.message_queue.get_nowait()
                self.received_messages.append(msg)
                
                # Forward to FTCAN dialog if open
                if self._ftcan_dialog is not None:
                    self._ftcan_dialog.add_message(msg)
                
                # Check triggers (before adding to UI)
                if self.triggers_enabled and self.connected:
                    self.check_and_fire_triggers(msg)
                
                # Exibir mensagens na UI
                if self.split_screen_mode and self.receive_table_left and self.receive_table_right:
                    # Split-screen mode: route to appropriate table
                    if self.tracer_mode:
                        if self.recording:
                            self.recorded_messages.append(msg)
                            if msg.source == self.split_screen_left_channel:
                                self._add_message_to_table(msg, self.receive_table_left)
                            elif msg.source == self.split_screen_right_channel:
                                self._add_message_to_table(msg, self.receive_table_right)
                    else:
                        # Monitor mode in split-screen
                        if msg.source == self.split_screen_left_channel:
                            self.add_message_monitor_mode(msg, target_table=self.receive_table_left)
                        elif msg.source == self.split_screen_right_channel:
                            self.add_message_monitor_mode(msg, target_table=self.receive_table_right)
                else:
                    # Normal single-screen mode
                    if self.tracer_mode:
                        # Tracer: only show if recording (Record active)
                        if self.recording:
                            self.recorded_messages.append(msg)  # Add to list BEFORE displaying
                            self.add_message_tracer_mode(msg)
                    else:
                        # Monitor: sempre exibir
                        self.add_message_monitor_mode(msg)
                
                self.update_message_count()
        except queue.Empty:
            pass
    
    def add_message_tracer_mode(self, msg: CANMessage, highlight: bool = True):
        """Adiciona mensagem no modo Tracer
        
        Args:
            msg: Mensagem CAN a ser adicionada
            highlight: Se True, destaca linha atualizada (para recepção em tempo real)
        """
        # Check filter
        if not self.message_passes_filter(msg):
            return
        
        dt = datetime.fromtimestamp(msg.timestamp)
        time_str = dt.strftime("%S.%f")[:-3]  # Segundos.milissegundos
        pid_str = f"0x{msg.can_id:03X}"  # PID = CAN ID
        data_str = " ".join([f"{b:02X}" for b in msg.data])
        ascii_str = msg.to_ascii()
        
        row = self.receive_table.rowCount()
        self.receive_table.insertRow(row)
        
        # Create items with alignment
        id_item = QTableWidgetItem(str(row + 1))
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # IMPORTANT: Store the real index in recorded_messages as UserRole
        # This allows correct mapping of table row to message
        msg_index = len(self.recorded_messages) - 1  # Index of last message added
        id_item.setData(Qt.ItemDataRole.UserRole, msg_index)
        
        dlc_item = QTableWidgetItem(str(msg.dlc))
        dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # ID, Time, Channel, PID, DLC, Data, ASCII, Comment
        self.receive_table.setItem(row, 0, id_item)                          # ID sequencial
        self.receive_table.setItem(row, 1, QTableWidgetItem(time_str))      # Time
        
        # Channel column
        channel_item = QTableWidgetItem(msg.source)
        channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.receive_table.setItem(row, 2, channel_item)                    # Channel
        
        self.receive_table.setItem(row, 3, QTableWidgetItem(pid_str))       # PID
        self.receive_table.setItem(row, 4, dlc_item)                        # DLC
        self.receive_table.setItem(row, 5, QTableWidgetItem(data_str))      # Data
        self.receive_table.setItem(row, 6, QTableWidgetItem(ascii_str))     # ASCII
        self.receive_table.setItem(row, 7, QTableWidgetItem(msg.comment))   # Comment
        
        # NO TRACER MODE: Sem highlight (deixar fluir sem azul)
        # Highlight code removed so messages flow naturally
        
        # Auto-scroll
        self.receive_table.scrollToBottom()
    
    def add_message_monitor_mode(self, msg: CANMessage, highlight: bool = True, target_table: QTableWidget = None):
        """Adiciona mensagem no modo Monitor (agrupa por ID)
        
        Args:
            msg: Mensagem CAN a ser adicionada
            highlight: Se True, destaca linha atualizada (para recepção em tempo real)
                      Se False, não destaca (para carregamento de logs)
            target_table: Tabela alvo (para split-screen), None = usar self.receive_table
        """
        # Check filter
        if not self.message_passes_filter(msg):
            return
        
        # Use target table or default
        table = target_table if target_table else self.receive_table
        
        pid_str = f"0x{msg.can_id:03X}"
        data_str = " ".join([f"{b:02X}" for b in msg.data])
        ascii_str = msg.to_ascii()
        
        # Incrementar contador por ID+Channel
        counter_key = (msg.can_id, msg.source)
        self.message_counters[counter_key] += 1
        count = self.message_counters[counter_key]
        
        # Calculate period (time since last message for this ID+Channel)
        period_str = ""
        if counter_key in self.message_last_timestamp:
            period_ms = int((msg.timestamp - self.message_last_timestamp[counter_key]) * 1000)
            period_str = f"{period_ms}"
        
        # Update timestamp of last message for this ID+Channel
        self.message_last_timestamp[counter_key] = msg.timestamp
        
        # Check if row already exists for this PID and Channel
        existing_row = -1
        for row in range(table.rowCount()):
            pid_item = table.item(row, 3)  # Column 3 = PID
            channel_item = table.item(row, 2)  # Column 2 = Channel
            if pid_item and channel_item:
                if pid_item.text() == pid_str and channel_item.text() == msg.source:
                    existing_row = row
                    break
        
        if existing_row >= 0:
            # Update existing row
            # Monitor: ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # Centralizar Count
            table.setItem(existing_row, 1, count_item)                     # Count
            # Channel does not change (keeps original from first message)
            table.setItem(existing_row, 5, QTableWidgetItem(data_str))     # Data
            table.setItem(existing_row, 6, QTableWidgetItem(period_str))   # Period
            table.setItem(existing_row, 7, QTableWidgetItem(ascii_str))    # ASCII
            
            # In Monitor mode: highlight ONLY the Count cell in light blue when count > 1
            if highlight and count > 1:
                count_item.setBackground(self.colors['highlight'])
            else:
                # Manter cor normal se count == 1
                count_item.setBackground(self.colors['normal_bg'])
                
            # Clear background of other cells (in case they were highlighted before)
            for col in range(table.columnCount()):
                if col == 1:  # Pular a coluna Count
                    continue
                item = table.item(existing_row, col)
                if item:
                    item.setBackground(self.colors['normal_bg'])
        else:
            # Add new row at the correct position (sorted by PID)
            # Monitor: ID, Count, PID, DLC, Data, Period, ASCII, Comment
            
            # Find correct position to insert (sorted by PID, then Channel)
            insert_row = table.rowCount()  # By default, insert at end
            
            for row in range(table.rowCount()):
                existing_pid_item = table.item(row, 3)  # Column 3 = PID
                existing_channel_item = table.item(row, 2)  # Column 2 = Channel
                if existing_pid_item:
                    existing_pid_str = existing_pid_item.text()
                    # Comparar PIDs (remover "0x" e converter para int)
                    try:
                        existing_pid = int(existing_pid_str.replace("0x", ""), 16)
                        if msg.can_id < existing_pid:
                            insert_row = row
                            break
                        elif msg.can_id == existing_pid and existing_channel_item:
                            # Mesmo PID, ordenar por Channel
                            if msg.source < existing_channel_item.text():
                                insert_row = row
                                break
                    except ValueError:
                        continue
            
            table.insertRow(insert_row)
            row = insert_row
            
            # Criar items com alinhamento
            id_item = QTableWidgetItem(str(row + 1))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            dlc_item = QTableWidgetItem(str(msg.dlc))
            dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            period_item = QTableWidgetItem(period_str)
            period_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Inserir items - Monitor: ID, Count, Channel, PID, DLC, Data, Period, Protocol, ASCII, Comment
            table.setItem(row, 0, id_item)                            # ID sequencial
            table.setItem(row, 1, count_item)                         # Count
            
            # Channel column
            channel_item = QTableWidgetItem(msg.source)
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, channel_item)                       # Channel
            
            table.setItem(row, 3, QTableWidgetItem(pid_str))          # PID
            table.setItem(row, 4, dlc_item)                           # DLC
            table.setItem(row, 5, QTableWidgetItem(data_str))         # Data
            table.setItem(row, 6, period_item)                        # Period
            table.setItem(row, 7, QTableWidgetItem(ascii_str))        # ASCII
            table.setItem(row, 8, QTableWidgetItem(msg.comment))      # Comment
            
            # Do not highlight on first message (count == 1), keep normal color
            # Highlight should only appear when count > 1 (repeated message)
            count_item.setBackground(self.colors['normal_bg'])
            
            # Recalcular IDs sequenciais de todas as linhas (pois a ordem mudou)
            if table == self.receive_table:
                self.update_sequential_ids()
    
    def update_sequential_ids(self):
        """Atualiza os IDs sequenciais na coluna 0 do modo Monitor"""
        if not self.tracer_mode:  # Apenas no modo Monitor
            for row in range(self.receive_table.rowCount()):
                id_item = QTableWidgetItem(str(row + 1))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.receive_table.setItem(row, 0, id_item)
    
    def update_message_count(self):
        """Atualiza contador de mensagens"""
        if self.tracer_mode:
            count = self.receive_table.rowCount()
        else:
            count = sum(self.message_counters.values())
        self.msg_count_label.setText(f"Messages: {count}")
    
    def on_dlc_changed(self, value):
        """Habilita/desabilita campos de dados baseado no DLC"""
        for i in range(8):
            self.tx_data_bytes[i].setEnabled(i < value)
            if i >= value:
                self.tx_data_bytes[i].setText("00")
    
    def get_data_from_bytes(self):
        """Get data bytes from individual fields"""
        data_bytes = []
        dlc = self.tx_dlc_input.value()
        for i in range(dlc):
            byte_str = self.tx_data_bytes[i].text()
            if not byte_str or len(byte_str) == 0:
                byte_str = "00"
            data_bytes.append(byte_str)
        return bytes.fromhex(''.join(data_bytes))
    
    def set_data_to_bytes(self, data_str):
        """Define bytes de dados nos campos individuais"""
        # Strip spaces and convert
        data_clean = data_str.replace(' ', '')
        
        # Preencher campos byte a byte
        for i in range(8):
            if i * 2 < len(data_clean):
                byte_hex = data_clean[i*2:i*2+2]
                if len(byte_hex) == 1:
                    byte_hex = '0' + byte_hex
                self.tx_data_bytes[i].setText(byte_hex.upper())
            else:
                self.tx_data_bytes[i].setText("00")
    
    def get_tx_message_data_from_table(self, row):
        """Get data of a message from the transmit table"""
        # Columns: PID(0), DLC(1), RTR(2), Period(3), TX Mode(4), Trigger ID(5), Trigger Data(6), D0-D7(7-14), Count(15), Comment(16), Channel(17)
        
        # ID
        can_id_str = self.transmit_table.item(row, 0).text().replace('0x', '').replace('0X', '')
        can_id = int(can_id_str, 16)
        
        # DLC
        dlc = int(self.transmit_table.item(row, 1).text())
        
        # RTR
        rtr_item = self.transmit_table.item(row, 2)
        is_rtr = rtr_item and rtr_item.text() == "✓"
        
        # Period
        period_str = self.transmit_table.item(row, 3).text()
        
        # TX Mode
        tx_mode_item = self.transmit_table.item(row, 4)
        tx_mode = tx_mode_item.text() if tx_mode_item else "off"
        
        # Channel/Source
        source_item = self.transmit_table.item(row, 17)
        source = source_item.text() if source_item else "CAN1"
        
        # Data bytes (D0-D7)
        data_bytes = []
        for i in range(dlc):
            byte_item = self.transmit_table.item(row, 7 + i)
            if byte_item and byte_item.text():
                data_bytes.append(byte_item.text())
            else:
                data_bytes.append("00")
        
        data = bytes.fromhex(''.join(data_bytes)) if data_bytes else b''
        
        return {
            'can_id': can_id,
            'dlc': dlc,
            'is_rtr': is_rtr,
            'period': period_str,
            'tx_mode': tx_mode,
            'source': source,
            'data': data
        }
    
    def send_single(self):
        """Send a single message"""
        try:
            can_id = int(self.tx_id_input.text(), 16)
            dlc = self.tx_dlc_input.value()
            data = self.get_data_from_bytes()
            
            if self.can_bus_manager or self.can_bus:
                message = can.Message(
                    arbitration_id=can_id,
                    data=data[:dlc],
                    is_extended_id=self.tx_29bit_check.isChecked(),
                    is_remote_frame=self.tx_rtr_check.isChecked()
                )
                # Get target bus from TX source dropdown
                target_bus = self.tx_source_combo.currentText() if self.can_bus_manager else None
                self._send_can_message(message, target_bus)
                self.logger.info(f"Transmit: Enviado 0x{can_id:03X} para {target_bus or 'all'} - {data.hex()}")
                
                # Se estamos editando uma linha, incrementar o contador dela
                if self.editing_tx_row >= 0 and self.editing_tx_row < self.transmit_table.rowCount():
                    count_item = self.transmit_table.item(self.editing_tx_row, 15)
                    if count_item:
                        current_count = int(count_item.text()) if count_item.text().isdigit() else 0
                        count_item.setText(str(current_count + 1))
                    else:
                        # Create item if it does not exist
                        new_item = QTableWidgetItem("1")
                        new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.transmit_table.setItem(self.editing_tx_row, 15, new_item)
                        self.transmit_table.setItem(self.editing_tx_row, 15, new_item)
                
                # No popup - discrete notification only
                self.show_notification(t('notif_message_sent', id=can_id), 1000)
            else:
                self.show_notification(t('notif_simulation_sent', id=can_id), 2000)
        except Exception as e:
            self.logger.error(f"Erro ao enviar: {e}")
            self.show_notification(t('notif_error', error=str(e)), 3000)
    
    def clear_tx_fields(self):
        """Clear all transmit edit fields"""
        self.tx_id_input.setText("000")
        self.tx_dlc_input.setValue(8)
        self.tx_29bit_check.setChecked(False)
        self.tx_rtr_check.setChecked(False)
        for i in range(8):
            self.tx_data_bytes[i].setText("00")
        self.tx_period_input.setText("0")
        self.tx_mode_combo.setCurrentIndex(0)
        self.trigger_id_input.setText("")
        self.trigger_data_input.setText("")
        self.tx_comment_input.setText("")
        self.editing_tx_row = -1
        # Update button to "Add"
        self.btn_add.setText("Add")
    
    def add_tx_message(self):
        """Add or update message in the transmit list"""
        try:
            # Check if we are editing an existing row or adding new
            if self.editing_tx_row >= 0 and self.editing_tx_row < self.transmit_table.rowCount():
                # Editando linha existente
                row = self.editing_tx_row
            else:
                # Adicionando nova linha
                row = self.transmit_table.rowCount()
                self.transmit_table.insertRow(row)
            
            # Colunas: ID, DLC, RTR, Period, TX Mode, Trigger ID, Trigger Data, D0-D7, Count, Comment
            # 0: ID
            self.transmit_table.setItem(row, 0, QTableWidgetItem(self.tx_id_input.text()))
            
            # 1: DLC
            dlc = self.tx_dlc_input.value()
            self.transmit_table.setItem(row, 1, QTableWidgetItem(str(dlc)))
            
            # 2: RTR
            rtr = "✓" if self.tx_rtr_check.isChecked() else ""
            rtr_item = QTableWidgetItem(rtr)
            rtr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.transmit_table.setItem(row, 2, rtr_item)
            
            # 3: Period
            period = self.tx_period_input.text()
            self.transmit_table.setItem(row, 3, QTableWidgetItem(period if period != "0" else "off"))
            
            # 4: TX Mode
            tx_mode = self.tx_mode_combo.currentText()
            self.transmit_table.setItem(row, 4, QTableWidgetItem(tx_mode))
            
            # 5: Trigger ID
            trigger_id = self.trigger_id_input.text()
            self.transmit_table.setItem(row, 5, QTableWidgetItem(trigger_id if trigger_id else ""))
            
            # 6: Trigger Data
            trigger_data = self.trigger_data_input.text()
            self.transmit_table.setItem(row, 6, QTableWidgetItem(trigger_data if trigger_data else ""))
            
            # 7-14: Data bytes (D0-D7)
            for i in range(8):
                byte_val = self.tx_data_bytes[i].text() if i < dlc else ""
                byte_item = QTableWidgetItem(byte_val)
                byte_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.transmit_table.setItem(row, 7 + i, byte_item)
            
            # 15: Count - manter o valor existente se estiver editando
            if self.editing_tx_row >= 0:
                # Manter count existente ao editar
                count_item = self.transmit_table.item(row, 15)
                if not count_item:
                    self.transmit_table.setItem(row, 15, QTableWidgetItem("0"))
            else:
                # Nova mensagem, count = 0
                self.transmit_table.setItem(row, 15, QTableWidgetItem("0"))
            
            # 16: Comment
            self.transmit_table.setItem(row, 16, QTableWidgetItem(self.tx_comment_input.text()))
            
            # 17: Source
            source = self.tx_source_combo.currentText()
            source_item = QTableWidgetItem(source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.transmit_table.setItem(row, 17, source_item)
            
            # Reset edit state
            self.editing_tx_row = -1
            self.clear_tx_fields()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Erro ao adicionar: {str(e)}")
    
    def load_tx_message_to_edit(self, item=None):
        """Load message from table into edit fields (double-click or copy)"""
        current_row = self.transmit_table.currentRow()
        if current_row >= 0:
            try:
                # 0: ID
                self.tx_id_input.setText(self.transmit_table.item(current_row, 0).text())
                
                # 1: DLC
                dlc = int(self.transmit_table.item(current_row, 1).text())
                self.tx_dlc_input.setValue(dlc)
                
                # 2: RTR
                rtr_item = self.transmit_table.item(current_row, 2)
                self.tx_rtr_check.setChecked(rtr_item and rtr_item.text() == "✓")
                
                # 3: Period
                period = self.transmit_table.item(current_row, 3).text()
                self.tx_period_input.setText(period if period != "off" else "0")
                
                # 4: TX Mode
                tx_mode = self.transmit_table.item(current_row, 4).text()
                index = self.tx_mode_combo.findText(tx_mode)
                if index >= 0:
                    self.tx_mode_combo.setCurrentIndex(index)
                
                # 5: Trigger ID
                trigger_id_item = self.transmit_table.item(current_row, 5)
                self.trigger_id_input.setText(trigger_id_item.text() if trigger_id_item else "")
                
                # 6: Trigger Data
                trigger_data_item = self.transmit_table.item(current_row, 6)
                self.trigger_data_input.setText(trigger_data_item.text() if trigger_data_item else "")
                
                # 7-14: Data bytes (D0-D7)
                for i in range(8):
                    byte_item = self.transmit_table.item(current_row, 7 + i)
                    if byte_item and byte_item.text():
                        self.tx_data_bytes[i].setText(byte_item.text())
                    else:
                        self.tx_data_bytes[i].setText("00")
                
                # 16: Comment
                comment_item = self.transmit_table.item(current_row, 16)
                self.tx_comment_input.setText(comment_item.text() if comment_item else "")
                
                # 17: Source
                source_item = self.transmit_table.item(current_row, 17)
                if source_item:
                    source_text = source_item.text()
                    index = self.tx_source_combo.findText(source_text)
                    if index >= 0:
                        self.tx_source_combo.setCurrentIndex(index)
                
                # Definir que estamos editando esta linha
                self.editing_tx_row = current_row
                
                # Change button to "Save"
                self.btn_add.setText("Save")
                
            except Exception as e:
                self.logger.error(f"Erro ao carregar mensagem: {e}")
    
    def delete_tx_message(self):
        """Remove mensagem da lista"""
        current_row = self.transmit_table.currentRow()
        if current_row >= 0:
            self.transmit_table.removeRow(current_row)
    
    def send_all(self):
        """Start periodic send of all messages with TX Mode = 'on'"""
        if not self.connected or not self.can_bus_manager:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        if self.periodic_send_active:
            self.show_notification(t('notif_periodic_already_active'), 2000)
            return
        
        # Check if there are messages in the table
        if self.transmit_table.rowCount() == 0:
            self.show_notification(t('notif_no_messages_in_table'), 2000)
            return
        
        self.periodic_send_active = True
        messages_started = 0
        
        for row in range(self.transmit_table.rowCount()):
            try:
                # Obter dados da linha
                msg_data = self.get_tx_message_data_from_table(row)
                tx_mode = msg_data.get('tx_mode', 'off').lower()
                
                # Apenas processar mensagens com TX Mode = "on"
                if tx_mode != 'on':
                    continue
                
                # Check if period is configured
                if msg_data['period'] == "off" or msg_data['period'] == "0":
                    continue
                
                # Parse period (in ms)
                try:
                    period_ms = int(msg_data['period'])
                    if period_ms <= 0:
                        continue
                except ValueError:
                    continue
                
                # Create stop event for this thread
                stop_event = threading.Event()
                self.periodic_send_stop_events[row] = stop_event
                
                # Create and start periodic send thread
                thread = threading.Thread(
                    target=self._periodic_send_worker,
                    args=(row, msg_data['can_id'], msg_data['dlc'], msg_data['data'], period_ms, stop_event, msg_data['is_rtr']),
                    daemon=True
                )
                self.periodic_send_threads[row] = thread
                thread.start()
                messages_started += 1
                
                self.logger.info(f"Periodic Send: Iniciado 0x{msg_data['can_id']:03X} a cada {period_ms}ms")
                
            except Exception as e:
                self.logger.error(f"Erro ao iniciar envio periódico da linha {row}: {e}")
        
        if messages_started > 0:
            self.show_notification(t('notif_periodic_started', count=messages_started), 3000)
            # Change Send All button to Stop All
            self.btn_send_all.setText("Stop All")
            self.btn_send_all.setStyleSheet(self.colors['send_active'])
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.stop_all)
        else:
            self.periodic_send_active = False
            self.show_notification("⚠️ Nenhuma mensagem com TX Mode = 'on' e período válido", 2000)
    
    def stop_all(self):
        """Stop all periodic transmissions"""
        if not self.periodic_send_active:
            self.show_notification(t('notif_no_periodic_active'), 2000)
            return
        
        # Sinalizar todas as threads para parar
        for stop_event in self.periodic_send_stop_events.values():
            stop_event.set()
        
        # Aguardar threads finalizarem (com timeout)
        for thread in self.periodic_send_threads.values():
            if thread.is_alive():
                thread.join(timeout=1.0)
        
        # Clear structures
        self.periodic_send_threads.clear()
        self.periodic_send_stop_events.clear()
        self.periodic_send_active = False
        
        # Revert Stop All button to Send All
        self.btn_send_all.setText("Send All")
        self.btn_send_all.setStyleSheet("")
        self.btn_send_all.clicked.disconnect()
        self.btn_send_all.clicked.connect(self.send_all)
        
        self.show_notification(t('notif_periodic_stopped'), 2000)
        self.logger.info("Periodic Send: Todas as transmissões periódicas foram paradas")
    
    def _periodic_send_worker(self, row: int, can_id: int, dlc: int, data: bytes, period_ms: int, stop_event: threading.Event, is_rtr: bool = False):
        """Worker thread for periodic send of one message"""
        period_sec = period_ms / 1000.0
        
        try:
            while not stop_event.is_set():
                try:
                    # Send message
                    if self.can_bus_manager or self.can_bus:
                        # Garantir que data tenha o tamanho correto (dlc bytes)
                        data_to_send = data[:dlc] if len(data) >= dlc else data + b'\x00' * (dlc - len(data))
                        
                        can_msg = can.Message(
                            arbitration_id=can_id,
                            data=data_to_send,
                            is_extended_id=(can_id > 0x7FF),
                            is_remote_frame=is_rtr
                        )
                        # Get target bus from table (column 17)
                        source_item = self.transmit_table.item(row, 17)
                        target_bus = source_item.text() if source_item else None
                        self._send_can_message(can_msg, target_bus)
                        
                        # Incrementar contador na tabela (thread-safe via QTimer)
                        # Usar functools.partial para garantir captura correta do valor
                        QTimer.singleShot(0, partial(self._increment_tx_count, row))
                        
                except Exception as e:
                    self.logger.error(f"Erro ao enviar mensagem periódica 0x{can_id:03X}: {e}")
                
                # Wait for period or until stop_event is set
                stop_event.wait(period_sec)
                
        except Exception as e:
            self.logger.error(f"Erro no worker de envio periódico (row {row}): {e}")
    
    def _increment_tx_count(self, row: int):
        """Increment transmit counter in table (must be called from main thread)"""
        try:
            if row < self.transmit_table.rowCount():
                # Column 15 is Count in the new structure
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    # Incrementar contador existente
                    try:
                        current_count = int(count_item.text())
                        count_item.setText(str(current_count + 1))
                    except ValueError:
                        count_item.setText("1")
                else:
                    # Create item if it doesn't exist
                    new_item = QTableWidgetItem("1")
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 15, new_item)
        except Exception as e:
            self.logger.error(f"Erro ao incrementar contador: {e}")
    
    def _update_tx_count(self, row: int, count: int):
        """Update transmit counter in table (must be called from main thread)"""
        try:
            if row < self.transmit_table.rowCount():
                # Column 15 is Count in the new structure
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    count_item.setText(str(count))
                else:
                    # Create item if it doesn't exist
                    new_item = QTableWidgetItem(str(count))
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 15, new_item)
        except Exception as e:
            self.logger.error(f"Erro ao atualizar contador: {e}")
    
    def show_settings(self):
        """Show settings window"""
        try:
            self.logger.info("Abrindo dialog de configurações")
            dialog = SettingsDialog(self, self.config, self.usb_monitor)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_config = dialog.get_config()
                self.logger.info(f"Configurações atualizadas: {new_config}")
                
                # Check if language changed
                old_language = self.config.get('language', 'en')
                new_language = new_config.get('language', 'en')
                
                # Check if theme changed
                old_theme = self.config.get('theme', 'system')
                new_theme = new_config.get('theme', 'system')
                
                # Check if listen_only changed
                old_listen_only = self.config.get('listen_only', True)
                new_listen_only = new_config.get('listen_only', True)
                
                # Update local config and save to file
                self.config.update(new_config)
                self.config_manager.update(new_config)
                self.logger.info("Configuração salva em config.json")
                
                # Apply language change
                language_changed = False
                if old_language != new_language:
                    from .i18n import get_i18n
                    i18n = get_i18n()
                    i18n.set_language(new_language)
                    self.logger.info(f"Idioma alterado para: {new_language}")
                    
                    # Update interface with new language
                    self.update_ui_translations()
                    language_changed = True
                
                # Apply theme change
                theme_changed = False
                if old_theme != new_theme:
                    self.logger.info(f"Tema alterado para: {new_theme}")
                    # Apply theme immediately
                    self.apply_theme(new_theme)
                    theme_changed = True
                
                # Update mode label if connected or always update
                if self.config.get('listen_only', True):
                    self.mode_label.setText(t('status_listen_only'))
                else:
                    self.mode_label.setText(t('status_normal'))
                
                if old_listen_only != new_listen_only:
                    self.logger.info(f"Modo alterado para: {'Listen Only' if new_listen_only else 'Normal'}")
                
                # Show notification in bottom-right corner
                if language_changed and theme_changed:
                    self.show_notification(
                        f"✅ {t('msg_language_and_theme_applied')}",
                        5000  # 5 segundos
                    )
                elif language_changed:
                    self.show_notification(
                        f"✅ {t('msg_language_applied')}",
                        3000  # 3 segundos
                    )
                elif theme_changed:
                    self.show_notification(
                        f"✅ {t('msg_theme_applied')}",
                        3000  # 3 segundos
                    )
                else:
                    self.show_notification(
                        f"✅ {t('msg_settings_saved')}",
                        3000  # 3 segundos
                    )
                
        except Exception as e:
            self.logger.error(f"Erro ao abrir/processar settings: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Settings Error", f"Erro: {str(e)}")
    
    def change_language(self, language_code: str):
        """Change application language"""
        try:
            old_language = self.config.get('language', 'en')
            
            if old_language == language_code:
                return  # Already in selected language
            
            # Update configuration
            self.config['language'] = language_code
            self.config_manager.update(self.config)
            
            # Apply language change
            from .i18n import get_i18n
            i18n = get_i18n()
            i18n.set_language(language_code)
            self.logger.info(f"Idioma alterado para: {language_code}")
            
            # Update interface with new language
            self.update_ui_translations()
            
            # Show notification
            lang_name = {"en": "English", "pt": "Português", "es": "Español", "de": "Deutsch", "fr": "Français"}.get(language_code, language_code)
            self.show_notification(t('notif_language_changed', language=lang_name), 3000)
            
        except Exception as e:
            self.logger.error(f"Erro ao mudar idioma: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Language Error", f"Erro ao mudar idioma: {str(e)}")
    
    def show_filters(self):
        """Show filter configuration"""
        QMessageBox.information(self, "Filters", "Filtros em desenvolvimento")
    
    def show_statistics(self):
        """Show statistics"""
        total_msgs = sum(self.message_counters.values())
        unique_ids = len(self.message_counters)
        
        stats_text = f"Estatísticas do Barramento CAN\n\n"
        stats_text += f"Total de Mensagens: {total_msgs}\n"
        stats_text += f"IDs Únicos: {unique_ids}\n"
        stats_text += f"Conectado: {'Sim' if self.connected else 'Não'}\n"
        stats_text += f"Gravando: {'Sim' if self.recording else 'Não'}\n"
        stats_text += f"Modo: {'Tracer' if self.tracer_mode else 'Monitor'}\n\n"
        
        if self.message_counters:
            stats_text += "Top 5 IDs mais frequentes:\n"
            sorted_ids = sorted(self.message_counters.items(), key=lambda x: x[1], reverse=True)[:5]
            for can_id, count in sorted_ids:
                stats_text += f"  0x{can_id:03X}: {count} messages\n"
        
        QMessageBox.information(self, "Statistics", stats_text)
    
    def show_about(self):
        """Show application information"""
        platform_name = get_platform_display_name()
        about_text = f"""
        <h2>{t('about_heading', platform=platform_name)}</h2>
        <p><b>{t('about_version')}:</b> {__version__}</p>
        <p><b>{t('about_build')}:</b> {__build__}</p>
        
        <h3>{t('about_desc_heading')}:</h3>
        <p>{t('about_desc_text')}</p>
        
        <h3>{t('about_platforms_heading')}:</h3>
        <ul>
            <li>{t('about_platform_macos')}</li>
            <li>{t('about_platform_linux')}</li>
        </ul>
        
        <h3>{t('about_dependencies_heading')}:</h3>
        <p>{t('about_dependencies_text')}</p>
        
        <h3>{t('about_license_heading')}:</h3>
        <p>{t('about_license_text')}</p>
        
        <p>{t('about_copyright')}</p>
        """
        QMessageBox.about(self, t('dialog_about_title'), about_text)
    
    def save_log(self):
        """Salva log de mensagens recebidas"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Receive Log",
            "",
            "JSON Files (*.json);;Trace Files (*.trc);;CSV Files (*.csv);;All Files (*)"
        )
        if filename:
            try:
                self.logger.info(f"Salvando log: {filename}")
                
                # In Tracer mode, save only recorded messages (recorded_messages)
                # In Monitor mode, save all received messages
                messages_to_save = self.recorded_messages if self.tracer_mode else self.received_messages
                
                # Determine format by extension
                if filename.endswith('.csv'):
                    self._save_log_csv(filename, messages_to_save)
                    format_type = "CSV"
                elif filename.endswith('.trc'):
                    self._save_log_trace(filename, messages_to_save)
                    format_type = "TRC"
                else:
                    self._save_log_json(filename, messages_to_save)
                    format_type = "JSON"
                
                self.logger.info(f"Log salvo com sucesso: {len(messages_to_save)} mensagens em formato {format_type}")
                
                # Show notification
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_log_saved', filename=filename_short, count=len(messages_to_save)),
                    5000
                )
            except Exception as e:
                self.logger.error(f"Erro ao salvar log: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Save Error", f"Erro ao salvar: {str(e)}")
    
    def _save_log_json(self, filename: str, messages: List[CANMessage]):
        """Salva log em formato JSON com tipo de arquivo"""
        data = {
            'version': '1.0',
            'file_type': 'tracer' if self.tracer_mode else 'monitor',  # File type
            'mode': 'tracer' if self.tracer_mode else 'monitor',
            'config': self.config,
            'messages': [msg.to_dict() for msg in messages]
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_log_csv(self, filename: str, messages: List[CANMessage]):
        """Salva log em formato CSV"""
        import csv
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Channel', 'ID', 'DLC', 'Data', 'Comment'])
            for msg in messages:
                writer.writerow([
                    msg.timestamp,
                    msg.source,
                    f"0x{msg.can_id:03X}",
                    msg.dlc,
                    msg.to_hex_string(),
                    msg.comment
                ])
    
    def _save_log_trace(self, filename: str, messages: List[CANMessage]):
        """Save log in Trace format (SLCAN/trace compatible)"""
        with open(filename, 'w') as f:
            f.write(f"; CAN Trace File\n")
            f.write(f"; Generated by CAN Analyzer - {get_platform_display_name()}\n")
            f.write(f"; Mode: {'Tracer' if self.tracer_mode else 'Monitor'}\n")
            f.write(f"; Baudrate: {self.config.get('baudrate', 500000)} bps\n")
            f.write(f"; Messages: {len(messages)}\n")
            f.write(f";\n")
            
            for msg in messages:
                # Formato: timestamp channel id dlc data
                f.write(f"{msg.timestamp:.6f} {msg.source} {msg.can_id:03X} {msg.dlc} {msg.data.hex()}\n")
    
    def load_log(self):
        """Carrega log de mensagens"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Receive Log",
            "",
            "JSON Files (*.json);;Trace Files (*.trc);;CSV Files (*.csv);;All Files (*)"
        )
        if filename:
            try:
                self.logger.info(f"Load Log: Iniciando - tracer_mode={self.tracer_mode}")
                
                # If not in Tracer mode, switch automatically
                if not self.tracer_mode:
                    self.logger.info("Load Log: Mudando para modo Tracer")
                    self.toggle_tracer_mode()
                    self.logger.info(f"Load Log: Após toggle - tracer_mode={self.tracer_mode}")
                
                self.clear_receive()
                self.message_counters.clear()
                
                # Determine format by extension
                if filename.endswith('.csv'):
                    messages = self._load_log_csv(filename)
                elif filename.endswith('.trc'):
                    messages = self._load_log_trace(filename)
                else:
                    messages = self._load_log_json(filename)
                
                self.logger.info(f"Load Log: {len(messages)} mensagens carregadas")
                
                # Always add to Tracer, regardless of connection state
                # Load Trace should always load in Tracer mode
                self.logger.info(f"Load Log: Adicionando ao Tracer - tracer_mode={self.tracer_mode}")
                
                for msg in messages:
                    # Add to recorded messages BEFORE displaying
                    self.recorded_messages.append(msg)
                    self.add_message_tracer_mode(msg)
                
                self.logger.info(f"Load Log: recorded_messages={len(self.recorded_messages)}")
                
                # Enable playback buttons if there are messages
                if len(self.recorded_messages) > 0:
                    self.btn_play_all.setEnabled(True)
                    self.btn_play_selected.setEnabled(True)
                    self.logger.info("Load Log: Botões Play habilitados")
                
                self.update_message_count()
                
                # Show notification
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_log_loaded', filename=filename_short, count=len(messages)),
                    5000
                )
            except Exception as e:
                self.logger.error(f"Erro ao carregar log: {e}", exc_info=True)
                QMessageBox.critical(self, "Load Error", f"Erro ao carregar: {str(e)}")
    
    def _validate_file_type(self, data: dict, expected_type: str, filename: str) -> bool:
        """Valida o tipo de arquivo carregado
        
        Args:
            data: Dados carregados do JSON
            expected_type: Tipo esperado ('tracer', 'monitor', 'transmit', 'gateway')
            filename: Nome do arquivo (para mensagem de erro)
        
        Returns:
            True se válido, False caso contrário (mostra mensagem de erro)
        """
        if isinstance(data, list):
            # Formato antigo (sem tipo), permitir
            return True
        
        file_type = data.get('file_type', data.get('mode', None))
        
        if file_type is None:
            # File without type, allow (compatibility)
            return True
        
        if file_type != expected_type:
            # Tipo incorreto
            type_names = {
                'tracer': t('file_type_tracer'),
                'monitor': t('file_type_monitor'),
                'transmit': t('file_type_transmit'),
                'gateway': t('file_type_gateway')
            }
            
            import os
            filename_short = os.path.basename(filename)
            
            QMessageBox.warning(
                self,
                t('warning'),
                t('msg_wrong_file_type').format(
                    filename=filename_short,
                    expected=type_names.get(expected_type, expected_type),
                    found=type_names.get(file_type, file_type)
                )
            )
            return False
        
        return True
    
    def _load_log_json(self, filename: str) -> List[CANMessage]:
        """Load log from JSON format with type validation"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Validar tipo de arquivo
        expected_type = 'tracer' if self.tracer_mode else 'monitor'
        if not self._validate_file_type(data, expected_type, filename):
            return []
        
        # Support old format (list) and new (dict with metadata)
        if isinstance(data, list):
            messages_data = data
        else:
            messages_data = data.get('messages', [])
        
        messages = []
        for item in messages_data:
            msg = CANMessage(
                timestamp=item['timestamp'],
                can_id=item['can_id'],
                dlc=item['dlc'],
                data=bytes.fromhex(item['data']),
                comment=item.get('comment', ''),
                period=item.get('period', 0),
                count=item.get('count', 0),
                source=item.get('source', 'CAN1')
            )
            messages.append(msg)
        
        return messages
    
    def _load_log_csv(self, filename: str) -> List[CANMessage]:
        """Carrega log de formato CSV"""
        import csv
        messages = []
        
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse ID (remover 0x se presente)
                can_id_str = row['ID'].replace('0x', '')
                can_id = int(can_id_str, 16)
                
                # Parse data (strip spaces)
                data_str = row['Data'].replace(' ', '')
                data = bytes.fromhex(data_str)
                
                msg = CANMessage(
                    timestamp=float(row['Timestamp']),
                    can_id=can_id,
                    dlc=int(row['DLC']),
                    data=data,
                    comment=row.get('Comment', '')
                )
                messages.append(msg)
        
        return messages
    
    def _load_log_trace(self, filename: str) -> List[CANMessage]:
        """Carrega log de formato Trace"""
        messages = []
        
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Ignore comments
                if line.startswith(';') or not line:
                    continue
                
                # Parse: timestamp [channel] id dlc data
                # Suporta formato antigo (sem channel) e novo (com channel)
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        timestamp = float(parts[0])
                        
                        # Try to detect if channel (second field is not valid 3-digit hex)
                        if len(parts) >= 5 and not parts[1].isdigit() and len(parts[1]) <= 10:
                            # Novo formato: timestamp channel id dlc data
                            source = parts[1]
                            can_id = int(parts[2], 16)
                            dlc = int(parts[3])
                            data = bytes.fromhex(parts[4]) if len(parts) > 4 else b''
                        else:
                            # Formato antigo: timestamp id dlc data
                            source = "CAN1"  # Default
                            can_id = int(parts[1], 16)
                            dlc = int(parts[2])
                            data = bytes.fromhex(parts[3]) if len(parts) > 3 else b''
                        
                        msg = CANMessage(
                            timestamp=timestamp,
                            can_id=can_id,
                            dlc=dlc,
                            data=data,
                            source=source
                        )
                        messages.append(msg)
                    except Exception as e:
                        print(f"Erro ao parsear linha: {line} - {e}")
                        continue
        
        return messages
    
    def save_monitor_log(self):
        """Salva log do Monitor (received_messages)"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Monitor Log",
            "",
            "JSON Files (*.json);;Trace Files (*.trc);;CSV Files (*.csv);;All Files (*)"
        )
        if filename:
            try:
                self.logger.info(f"Salvando Monitor log: {filename}")
                
                # Save received messages (Monitor)
                messages_to_save = self.received_messages
                
                # Determine format by extension
                if filename.endswith('.csv'):
                    self._save_log_csv(filename, messages_to_save)
                    format_type = "CSV"
                elif filename.endswith('.trc'):
                    self._save_log_trace(filename, messages_to_save)
                    format_type = "TRC"
                else:
                    self._save_log_json(filename, messages_to_save)
                    format_type = "JSON"
                
                self.logger.info(f"Monitor log salvo: {len(messages_to_save)} mensagens em formato {format_type}")
                
                # Show notification
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_monitor_saved', filename=filename_short, count=len(messages_to_save)),
                    5000
                )
            except Exception as e:
                self.logger.error(f"Erro ao salvar Monitor log: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Save Error", f"Erro ao salvar: {str(e)}")
    
    def load_monitor_log(self):
        """Carrega log para o Monitor (received_messages)"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Monitor Log",
            "",
            "JSON Files (*.json);;Trace Files (*.trc);;CSV Files (*.csv);;All Files (*)"
        )
        if filename:
            try:
                self.logger.info(f"Carregando Monitor log: {filename}")
                
                # Se estiver em modo Tracer, mudar para Monitor
                if self.tracer_mode:
                    self.logger.info("Load Monitor: Mudando para modo Monitor")
                    self.toggle_tracer_mode()
                
                self.clear_receive()
                self.message_counters.clear()
                
                # Determine format by extension
                if filename.endswith('.csv'):
                    messages = self._load_log_csv(filename)
                elif filename.endswith('.trc'):
                    messages = self._load_log_trace(filename)
                else:
                    messages = self._load_log_json(filename)
                
                self.logger.info(f"Monitor log carregado: {len(messages)} mensagens")
                
                # Add to Monitor (received_messages)
                for msg in messages:
                    self.received_messages.append(msg)
                    self.add_message_monitor_mode(msg)
                
                self.update_message_count()
                
                # Show notification
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_monitor_loaded', filename=filename_short, count=len(messages)),
                    5000
                )
            except Exception as e:
                self.logger.error(f"Erro ao carregar Monitor log: {e}", exc_info=True)
                QMessageBox.critical(self, "Load Error", f"Erro ao carregar: {str(e)}")
    
    def save_transmit_list(self):
        """Save transmit message list"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Transmit List",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                transmit_data = []
                
                # Iterate over all rows of the transmit table
                for row in range(self.transmit_table.rowCount()):
                    # Get data using helper function
                    msg_data = self.get_tx_message_data_from_table(row)
                    
                    # Get other fields
                    tx_mode_item = self.transmit_table.item(row, 4)
                    trigger_id_item = self.transmit_table.item(row, 5)
                    trigger_data_item = self.transmit_table.item(row, 6)
                    count_item = self.transmit_table.item(row, 15)
                    comment_item = self.transmit_table.item(row, 16)
                    source_item = self.transmit_table.item(row, 17)
                    
                    item_data = {
                        'id': f"{msg_data['can_id']:03X}",
                        'dlc': msg_data['dlc'],
                        'rtr': msg_data['is_rtr'],
                        'data': msg_data['data'].hex().upper(),
                        'period': msg_data['period'],
                        'tx_mode': tx_mode_item.text() if tx_mode_item else 'off',
                        'trigger_id': trigger_id_item.text() if trigger_id_item else '',
                        'trigger_data': trigger_data_item.text() if trigger_data_item else '',
                        'count': int(count_item.text()) if count_item else 0,
                        'comment': comment_item.text() if comment_item else '',
                        'source': source_item.text() if source_item else 'CAN1'
                    }
                    transmit_data.append(item_data)
                
                # Save with metadata and type
                data = {
                    'version': '1.0',
                    'file_type': 'transmit',  # File type
                    'transmit_messages': transmit_data
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Show notification
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_tx_saved', filename=filename_short, count=len(transmit_data)),
                    5000
                )
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Erro ao salvar: {str(e)}")
    
    def show_receive_context_menu(self, position):
        """Show context menu on main receive table"""
        self._show_context_menu_for_table(self.receive_table, position)
    
    def _show_context_menu_for_table(self, table: QTableWidget, position):
        """Show context menu for any receive table"""
        # Check if there are selected rows
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Create menu
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        
        # Configure menu to close when clicking outside
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Menu actions
        add_to_tx_action = QAction("➕ Add to Transmit", self)
        add_to_tx_action.triggered.connect(lambda: self.add_selected_to_transmit(table))
        menu.addAction(add_to_tx_action)
        
        copy_id_action = QAction("📋 Copy ID", self)
        copy_id_action.triggered.connect(lambda: self.copy_selected_id(table))
        menu.addAction(copy_id_action)
        
        copy_data_action = QAction("📋 Copy Data", self)
        copy_data_action.triggered.connect(lambda: self.copy_selected_data(table))
        menu.addAction(copy_data_action)
        
        menu.addSeparator()
        
        # Bit Field Viewer (for a single selected message only)
        if len(selected_rows) == 1:
            bit_viewer_action = QAction("🔬 Bit Field Viewer", self)
            bit_viewer_action.triggered.connect(lambda: self.show_bit_field_viewer(table))
            menu.addAction(bit_viewer_action)
            menu.addSeparator()
        
        clear_selection_action = QAction("❌ Clear Selection", self)
        clear_selection_action.triggered.connect(table.clearSelection)
        menu.addAction(clear_selection_action)
        
        # Show menu at cursor position (exec is blocking and closes automatically)
        menu.exec(table.viewport().mapToGlobal(position))
    
    def show_transmit_context_menu(self, position):
        """Show context menu on transmit table"""
        # Check if there are selected rows
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Create menu
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        
        # Configure menu to close when clicking outside
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Menu actions
        send_once_action = QAction("📤 Send Once", self)
        send_once_action.triggered.connect(self.send_selected_tx_once)
        menu.addAction(send_once_action)
        
        menu.addSeparator()
        
        start_periodic_action = QAction("▶️ Start Periodic", self)
        start_periodic_action.triggered.connect(self.start_selected_periodic)
        menu.addAction(start_periodic_action)
        
        stop_periodic_action = QAction("⏹ Stop Periodic", self)
        stop_periodic_action.triggered.connect(self.stop_selected_periodic)
        menu.addAction(stop_periodic_action)
        
        menu.addSeparator()
        
        copy_action = QAction("📋 Copy to Edit", self)
        copy_action.triggered.connect(self.load_tx_message_to_edit)
        menu.addAction(copy_action)
        
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self.delete_selected_tx_messages)
        menu.addAction(delete_action)
        
        # Show menu at cursor position (exec is blocking and closes automatically)
        menu.exec(self.transmit_table.viewport().mapToGlobal(position))
    
    def send_selected_tx_once(self):
        """Send selected messages from transmit table once"""
        if not self.connected or not self.can_bus_manager:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        sent_count = 0
        for index in selected_rows:
            row = index.row()
            try:
                # Get row data using helper function
                msg_data = self.get_tx_message_data_from_table(row)
                
                # Garantir que data tenha o tamanho correto
                data_to_send = msg_data['data'][:msg_data['dlc']] if len(msg_data['data']) >= msg_data['dlc'] else msg_data['data'] + b'\x00' * (msg_data['dlc'] - len(msg_data['data']))
                
                # Enviar mensagem
                can_msg = can.Message(
                    arbitration_id=msg_data['can_id'],
                    data=data_to_send,
                    is_extended_id=(msg_data['can_id'] > 0x7FF),
                    is_remote_frame=msg_data['is_rtr']
                )
                # Get target bus from table (column 17)
                source_item = self.transmit_table.item(row, 17)
                target_bus = source_item.text() if source_item else None
                self._send_can_message(can_msg, target_bus)
                sent_count += 1
                self.logger.info(f"Send Once: Enviado 0x{msg_data['can_id']:03X} DLC={msg_data['dlc']} Data={data_to_send.hex()}")
                
                # Incrementar contador na tabela
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    current_count = int(count_item.text()) if count_item.text().isdigit() else 0
                    count_item.setText(str(current_count + 1))
                else:
                    # Create item if it doesn't exist
                    new_item = QTableWidgetItem("1")
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 15, new_item)
                
            except Exception as e:
                self.logger.error(f"Erro ao enviar mensagem da linha {row}: {e}")
        
        if sent_count > 0:
            self.show_notification(t('notif_messages_sent', count=sent_count), 2000)
    
    def start_selected_periodic(self):
        """Start periodic send of selected messages"""
        if not self.connected or not self.can_bus_manager:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        self.periodic_send_active = True
        started_count = 0
        
        for index in selected_rows:
            row = index.row()
            
            # Check if already running
            if row in self.periodic_send_threads:
                continue
            
            try:
                # Get row data using helper function
                msg_data = self.get_tx_message_data_from_table(row)
                
                # Check period
                if msg_data['period'] == "off" or msg_data['period'] == "0":
                    continue
                
                try:
                    period_ms = int(msg_data['period'])
                    if period_ms <= 0:
                        continue
                except ValueError:
                    continue
                
                # Create stop event
                stop_event = threading.Event()
                self.periodic_send_stop_events[row] = stop_event
                
                # Create and start thread
                thread = threading.Thread(
                    target=self._periodic_send_worker,
                    args=(row, msg_data['can_id'], msg_data['dlc'], msg_data['data'], period_ms, stop_event, msg_data['is_rtr']),
                    daemon=True
                )
                self.periodic_send_threads[row] = thread
                thread.start()
                started_count += 1
                
                self.logger.info(f"Periodic Send: Iniciado 0x{msg_data['can_id']:03X} a cada {period_ms}ms")
                
            except Exception as e:
                self.logger.error(f"Erro ao iniciar envio periódico da linha {row}: {e}")
        
        if started_count > 0:
            self.show_notification(t('notif_periodic_started', count=started_count), 2000)
            # Change Send All button to Stop All
            self.btn_send_all.setText("Stop All")
            self.btn_send_all.setStyleSheet(self.colors['send_active'])
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.stop_all)
    
    def stop_selected_periodic(self):
        """Stop periodic send of selected messages"""
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        stopped_count = 0
        for index in selected_rows:
            row = index.row()
            
            # Check if running
            if row in self.periodic_send_stop_events:
                # Signal to stop
                self.periodic_send_stop_events[row].set()
                
                # Aguardar thread finalizar
                if row in self.periodic_send_threads:
                    thread = self.periodic_send_threads[row]
                    if thread.is_alive():
                        thread.join(timeout=1.0)
                    del self.periodic_send_threads[row]
                
                del self.periodic_send_stop_events[row]
                stopped_count += 1
                
                # Reset counter (column 15)
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    count_item.setText("0")
        
        # If no more threads running, clear flag and revert button
        if len(self.periodic_send_threads) == 0:
            self.periodic_send_active = False
            # Revert Stop All button to Send All
            self.btn_send_all.setText("Send All")
            self.btn_send_all.setStyleSheet("")
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.send_all)
        
        if stopped_count > 0:
            self.show_notification(t('notif_periodic_stopped_count', count=stopped_count), 2000)
    
    def delete_selected_tx_messages(self):
        """Delete selected messages from transmit table"""
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Sort in descending order to avoid affecting indices when deleting
        rows_to_delete = sorted([index.row() for index in selected_rows], reverse=True)
        
        for row in rows_to_delete:
            # If periodic send is active, stop it first
            if row in self.periodic_send_stop_events:
                self.periodic_send_stop_events[row].set()
                if row in self.periodic_send_threads:
                    thread = self.periodic_send_threads[row]
                    if thread.is_alive():
                        thread.join(timeout=1.0)
                    del self.periodic_send_threads[row]
                del self.periodic_send_stop_events[row]
            
            # Deletar linha
            self.transmit_table.removeRow(row)
        
        self.show_notification(t('notif_messages_deleted', count=len(rows_to_delete)), 2000)
    
    def add_selected_to_transmit(self, table: QTableWidget = None):
        """Add selected messages to transmit list"""
        if table is None:
            table = self.receive_table
        
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        added_count = 0
        
        for index in selected_rows:
            row = index.row()
            
            try:
                # Extrair dados da linha selecionada
                if self.tracer_mode:
                    # Tracer mode: ID, Time, Channel, PID, DLC, Data, ASCII, Comment
                    id_str = table.item(row, 3).text()  # PID (coluna 3)
                    dlc_str = table.item(row, 4).text()  # DLC (coluna 4)
                    data_str = table.item(row, 5).text()  # Data (coluna 5)
                    comment_str = table.item(row, 7).text() if table.item(row, 7) else ""  # Comment
                    source_str = table.item(row, 2).text() if table.item(row, 2) else "CAN1"  # Channel (coluna 2)
                else:
                    # Monitor mode: ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
                    id_str = table.item(row, 3).text()  # PID (coluna 3)
                    dlc_str = table.item(row, 4).text()  # DLC (coluna 4)
                    data_str = table.item(row, 5).text()  # Data (coluna 5)
                    comment_str = table.item(row, 8).text() if table.item(row, 8) else ""  # Comment
                    source_str = table.item(row, 2).text() if table.item(row, 2) else "CAN1"  # Channel (coluna 2)
                
                # Remove "0x" from ID if present
                id_clean = id_str.replace("0x", "").replace("0X", "")
                dlc = int(dlc_str)
                
                # Add to transmit table
                tx_row = self.transmit_table.rowCount()
                self.transmit_table.insertRow(tx_row)
                
                # Columns: ID(0), DLC(1), RTR(2), Period(3), TX Mode(4), Trigger ID(5), Trigger Data(6), D0-D7(7-14), Count(15), Comment(16)
                
                # 0: ID
                self.transmit_table.setItem(tx_row, 0, QTableWidgetItem(id_clean))
                
                # 1: DLC
                self.transmit_table.setItem(tx_row, 1, QTableWidgetItem(dlc_str))
                
                # 2: RTR
                rtr_item = QTableWidgetItem("")
                rtr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.transmit_table.setItem(tx_row, 2, rtr_item)
                
                # 3: Period
                self.transmit_table.setItem(tx_row, 3, QTableWidgetItem("off"))
                
                # 4: TX Mode
                self.transmit_table.setItem(tx_row, 4, QTableWidgetItem("off"))
                
                # 5: Trigger ID
                self.transmit_table.setItem(tx_row, 5, QTableWidgetItem(""))
                
                # 6: Trigger Data
                self.transmit_table.setItem(tx_row, 6, QTableWidgetItem(""))
                
                # 7-14: Data bytes (D0-D7)
                data_clean = data_str.replace(' ', '')
                for i in range(8):
                    if i * 2 < len(data_clean):
                        byte_hex = data_clean[i*2:i*2+2]
                        byte_item = QTableWidgetItem(byte_hex.upper())
                    else:
                        byte_item = QTableWidgetItem("")
                    byte_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(tx_row, 7 + i, byte_item)
                
                # 15: Count
                self.transmit_table.setItem(tx_row, 15, QTableWidgetItem("0"))
                
                # 16: Comment
                self.transmit_table.setItem(tx_row, 16, QTableWidgetItem(comment_str if comment_str else "From Receive"))
                
                # 17: Source
                source_item = QTableWidgetItem(source_str)
                source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.transmit_table.setItem(tx_row, 17, source_item)
                
                added_count += 1
                
            except Exception as e:
                print(f"Erro ao adicionar linha {row}: {e}")
                continue
        
        if added_count > 0:
            # Show message in status bar instead of popup
            self.statusBar().showMessage(
                f"✅ {added_count} mensagem(ns) adicionada(s) à lista de transmissão!",
                3000  # 3 segundos
            )
    
    def copy_selected_id(self, table: QTableWidget = None):
        """Copia ID da mensagem selecionada"""
        if table is None:
            table = self.receive_table
        
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        if self.tracer_mode:
            id_str = table.item(row, 3).text()  # PID (coluna 3) no Tracer
        else:
            id_str = table.item(row, 3).text()  # PID (coluna 3) no Monitor
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(id_str)
        
        self.show_notification(t('notif_id_copied', id=id_str), 2000)
    
    def copy_selected_data(self, table: QTableWidget = None):
        """Copia dados da mensagem selecionada"""
        if table is None:
            table = self.receive_table
        
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        if self.tracer_mode:
            data_str = table.item(row, 5).text()  # Data (coluna 5) no Tracer
        else:
            data_str = table.item(row, 5).text()  # Data (coluna 5) no Monitor
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(data_str)
        
        self.show_notification(t('notif_data_copied', data=data_str), 2000)
    
    def load_transmit_list(self):
        """Load transmit message list with type validation"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Transmit List",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                # Validar tipo de arquivo
                if not self._validate_file_type(data, 'transmit', filename):
                    return
                
                # Support old format (list) and new (dict with metadata)
                if isinstance(data, list):
                    transmit_data = data
                else:
                    transmit_data = data.get('transmit_messages', [])
                
                # Clear current table (ask only if not empty)
                if self.transmit_table.rowCount() > 0:
                    reply = QMessageBox.question(
                        self,
                        "Load Transmit List",
                        "Limpar lista atual antes de carregar?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        self.transmit_table.setRowCount(0)
                else:
                    # Empty list, no need to ask
                    self.transmit_table.setRowCount(0)
                
                # Add messages to table
                for item in transmit_data:
                    row = self.transmit_table.rowCount()
                    self.transmit_table.insertRow(row)
                    
                    # Columns: ID(0), DLC(1), RTR(2), Period(3), TX Mode(4), Trigger ID(5), Trigger Data(6), D0-D7(7-14), Count(15), Comment(16)
                    
                    # 0: ID
                    self.transmit_table.setItem(row, 0, QTableWidgetItem(item.get('id', '000')))
                    
                    # 1: DLC
                    dlc = item.get('dlc', 8)
                    self.transmit_table.setItem(row, 1, QTableWidgetItem(str(dlc)))
                    
                    # 2: RTR
                    rtr = "✓" if item.get('rtr', False) else ""
                    rtr_item = QTableWidgetItem(rtr)
                    rtr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 2, rtr_item)
                    
                    # 3: Period
                    self.transmit_table.setItem(row, 3, QTableWidgetItem(item.get('period', 'off')))
                    
                    # 4: TX Mode
                    self.transmit_table.setItem(row, 4, QTableWidgetItem(item.get('tx_mode', 'off')))
                    
                    # 5: Trigger ID
                    self.transmit_table.setItem(row, 5, QTableWidgetItem(item.get('trigger_id', '')))
                    
                    # 6: Trigger Data
                    self.transmit_table.setItem(row, 6, QTableWidgetItem(item.get('trigger_data', '')))
                    
                    # 7-14: Data bytes (D0-D7)
                    data_str = item.get('data', '0000000000000000')
                    for i in range(8):
                        if i * 2 < len(data_str):
                            byte_hex = data_str[i*2:i*2+2]
                            byte_item = QTableWidgetItem(byte_hex.upper())
                        else:
                            byte_item = QTableWidgetItem("")
                        byte_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.transmit_table.setItem(row, 7 + i, byte_item)
                    
                    # 15: Count
                    self.transmit_table.setItem(row, 15, QTableWidgetItem(str(item.get('count', 0))))
                    
                    # 16: Comment
                    self.transmit_table.setItem(row, 16, QTableWidgetItem(item.get('comment', '')))
                    
                    # 17: Source
                    source = item.get('source', 'CAN1')
                    source_item = QTableWidgetItem(source)
                    source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 17, source_item)
                
                # Show notification
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_tx_loaded', filename=filename_short, count=len(transmit_data)),
                    5000
                )
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Erro ao carregar: {str(e)}")
    
    def toggle_playback_pause(self):
        """Pause or resume playback"""
        self.playback_paused = not self.playback_paused
        
        if self.playback_paused:
            self.btn_play_all.setText("▶ Continue")
            self.playback_label.setText("Paused")
            self.show_notification(t('notif_playback_paused'), 2000)
        else:
            self.btn_play_all.setText("⏸ Pause")
            self.playback_label.setText("Playing...")
            self.show_notification(t('notif_playback_resumed'), 2000)
    
    def highlight_playback_row(self, row: int):
        """Highlight current row during playback"""
        try:
            # Clear previous highlight
            if self.current_playback_row >= 0 and self.current_playback_row < self.receive_table.rowCount():
                for col in range(self.receive_table.columnCount()):
                    item = self.receive_table.item(self.current_playback_row, col)
                    if item:
                        item.setBackground(self.colors['normal_bg'])
            
            # Apply new highlight
            self.current_playback_row = row
            if row >= 0 and row < self.receive_table.rowCount():
                for col in range(self.receive_table.columnCount()):
                    item = self.receive_table.item(row, col)
                    if item:
                        item.setBackground(self.colors['highlight'])
                
                # Scroll to current row
                first_item = self.receive_table.item(row, 0)
                if first_item:
                    self.receive_table.scrollToItem(first_item)
        except Exception as e:
            print(f"Erro ao destacar linha {row}: {e}")
    
    def clear_playback_highlight(self):
        """Clear playback highlight"""
        if self.current_playback_row >= 0 and self.current_playback_row < self.receive_table.rowCount():
            for col in range(self.receive_table.columnCount()):
                item = self.receive_table.item(self.current_playback_row, col)
                if item:
                    item.setBackground(self.colors['normal_bg'])
        self.current_playback_row = -1
    
    def play_all_messages(self):
        """Reproduz (envia) todas as mensagens gravadas ou pausa/continua"""
        # If already playing, pause/resume
        if self.playback_active:
            self.toggle_playback_pause()
            return
        
        if not self.recorded_messages:
            QMessageBox.warning(self, "Playback", "Nenhuma mensagem gravada!\n\nClique em 'Record' para gravar mensagens primeiro.")
            return
        
        if not self.connected or not self.can_bus_manager:
            QMessageBox.warning(self, "Playback", "Conecte-se ao barramento CAN primeiro!")
            return
        
        self.logger.log_playback("iniciado (Play All)", len(self.recorded_messages))
        
        # Stop previous playback if any
        self.stop_playback()
        
        # Start playback in separate thread
        self.playback_active = True
        self.playback_stop_event.clear()
        self.playback_thread = threading.Thread(target=self._playback_worker, args=(self.recorded_messages,))
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        # Update UI
        self.btn_play_all.setText("⏸ Pause")
        self.btn_play_selected.setEnabled(False)
        self.btn_stop_play.setEnabled(True)
        self.playback_label.setText("Playing...")
        self.show_notification(t('notif_playback_playing', count=len(self.recorded_messages)), 3000)
    
    def play_selected_message(self):
        """Reproduz (envia) apenas as mensagens selecionadas"""
        selected_rows = self.receive_table.selectionModel().selectedRows()
        
        if not selected_rows:
            return  # No popup, just return
        
        if not self.connected or not self.can_bus_manager:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        # Get selected messages
        # In Tracer: use index stored in UserRole
        # If no UserRole, use row PID directly
        selected_messages = []
        
        for index in selected_rows:
            row = index.row()
            msg_added = False
            
            # Try to get by UserRole first (Tracer with Record)
            id_item = self.receive_table.item(row, 0)
            if id_item:
                msg_index = id_item.data(Qt.ItemDataRole.UserRole)
                self.logger.info(f"Play Selected: Linha {row}, UserRole={msg_index}, recorded_messages={len(self.recorded_messages)}")
                
                if msg_index is not None and msg_index < len(self.recorded_messages):
                    msg = self.recorded_messages[msg_index]
                    selected_messages.append(msg)
                    msg_added = True
                    self.logger.info(f"Play Selected: Usando UserRole - 0x{msg.can_id:03X}")
            
            # Fallback: create message from row data (if UserRole failed)
            if not msg_added:
                pid_item = self.receive_table.item(row, 2)  # PID column
                dlc_item = self.receive_table.item(row, 3)  # DLC column
                data_item = self.receive_table.item(row, 4)  # Data column
                
                if pid_item and dlc_item and data_item:
                    try:
                        # Parse PID (remover 0x)
                        pid_str = pid_item.text().replace('0x', '')
                        can_id = int(pid_str, 16)
                        
                        # Parse DLC
                        dlc = int(dlc_item.text())
                        
                        # Parse data (strip spaces and convert)
                        data_str = data_item.text().replace(' ', '')
                        data = bytes.fromhex(data_str) if data_str else b''
                        
                        self.logger.info(f"Play Selected Fallback: PID={pid_str}, DLC={dlc}, Data='{data_str}' -> bytes={data.hex()}")
                        
                        # Create temporary message
                        msg = CANMessage(
                            timestamp=time.time(),
                            can_id=can_id,
                            dlc=dlc,
                            data=data
                        )
                        selected_messages.append(msg)
                        self.logger.info(f"Play Selected: Usando Fallback - 0x{can_id:03X} DLC={dlc} Data={data.hex()}")
                    except Exception as e:
                        self.logger.error(f"Erro ao parsear linha {row}: {e}")
        
        if not selected_messages:
            return
        
        # Send messages immediately, no extra validation
        try:
            for msg in selected_messages:
                can_msg = can.Message(
                    arbitration_id=msg.can_id,
                    data=msg.data,
                    is_extended_id=(msg.can_id > 0x7FF)
                )
                # Send to original source bus
                self._send_can_message(can_msg, msg.source)
                self.logger.info(f"Play Selected: Enviado 0x{msg.can_id:03X} para {msg.source} - {msg.data.hex()}")
            
            # No popup, just discrete notification
            # self.show_notification(f"✅ {len(selected_messages)} msg sent", 1000)
        except Exception as e:
            self.logger.error(f"Erro ao enviar mensagens: {e}")
            self.show_notification(t('notif_error', error=str(e)), 3000)
    
    def stop_playback(self):
        """Stop message playback"""
        if self.playback_active:
            self.playback_stop_event.set()
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=2.0)
            self.playback_active = False
            self.playback_paused = False
        
        # Limpar highlight
        self.clear_playback_highlight()
        
        # Update UI - only enable if there are recorded messages
        has_recorded = len(self.recorded_messages) > 0
        self.btn_play_all.setText("▶ Play All")
        self.btn_play_all.setEnabled(has_recorded)
        self.btn_play_selected.setEnabled(has_recorded)
        self.btn_stop_play.setEnabled(False)
        self.playback_label.setText("Ready")
        self.show_notification(t('notif_playback_stopped'), 2000)
    
    def _playback_worker(self, messages: List[CANMessage]):
        """Worker thread para reproduzir mensagens com timing original"""
        try:
            if not messages:
                return
            
            self.logger.info(f"Playback Worker: Iniciando com {len(messages)} mensagens")
            
            # First message as time reference
            first_timestamp = messages[0].timestamp
            start_time = time.time()
            
            for i, msg in enumerate(messages):
                # Check if should stop
                if self.playback_stop_event.is_set():
                    self.logger.info(f"Playback Worker: Parado pelo usuário na mensagem {i+1}/{len(messages)}")
                    break
                
                # Check if paused
                while self.playback_paused and not self.playback_stop_event.is_set():
                    time.sleep(0.1)
                
                if self.playback_stop_event.is_set():
                    self.logger.info(f"Playback Worker: Parado durante pausa na mensagem {i+1}/{len(messages)}")
                    break
                
                # Highlight da linha atual (UI thread)
                QTimer.singleShot(0, partial(self.highlight_playback_row, i))
                
                # Calcular delay baseado no timestamp original
                if i > 0:
                    target_time = start_time + (msg.timestamp - first_timestamp)
                    current_time = time.time()
                    delay = target_time - current_time
                    
                    if delay > 0:
                        # Wait until the right time, checking stop_event
                        if self.playback_stop_event.wait(delay):
                            self.logger.info(f"Playback Worker: Parado durante delay na mensagem {i+1}/{len(messages)}")
                            break
                
                # Enviar mensagem
                try:
                    can_msg = can.Message(
                        arbitration_id=msg.can_id,
                        data=msg.data,
                        is_extended_id=(msg.can_id > 0x7FF)
                    )
                    # Send to original source bus
                    self._send_can_message(can_msg, msg.source)
                    self.logger.info(f"Playback: [{i+1}/{len(messages)}] Enviado 0x{msg.can_id:03X} para {msg.source} - {msg.data.hex()}")
                    
                    # Update progress in UI thread
                    progress = f"Playing {i+1}/{len(messages)}"
                    QTimer.singleShot(0, lambda p=progress: self.playback_label.setText(p))
                    
                except Exception as e:
                    self.logger.error(f"Erro ao enviar mensagem {i+1}: {e}")
            
            self.logger.info(f"Playback Worker: Finalizado - {i+1}/{len(messages)} mensagens processadas")
            
            # Clear highlight and finish playback
            QTimer.singleShot(0, self.clear_playback_highlight)
            QTimer.singleShot(0, self.stop_playback)
            
        except Exception as e:
            self.logger.error(f"Erro no playback worker: {e}")
            QTimer.singleShot(0, self.clear_playback_highlight)
            QTimer.singleShot(0, self.stop_playback)
    
    def show_bit_field_viewer(self, table: QTableWidget = None):
        """Mostra o Bit Field Viewer para a mensagem selecionada"""
        if table is None:
            table = self.receive_table
        
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Get message data from table
        if self.tracer_mode:
            # Tracer mode: reconstruct message from table
            pid_str = table.item(row, 3).text() if table.item(row, 3) else "0x000"
            dlc_str = table.item(row, 4).text() if table.item(row, 4) else "0"
            data_str = table.item(row, 5).text() if table.item(row, 5) else ""
            
            can_id = int(pid_str.replace('0x', ''), 16)
            dlc = int(dlc_str)
            data = bytes.fromhex(data_str.replace(' ', ''))
            
            message = CANMessage(
                timestamp=0,
                can_id=can_id,
                dlc=dlc,
                data=data
            )
        else:
            # Monitor mode: reconstruct from table
            pid_str = table.item(row, 3).text() if table.item(row, 3) else "0x000"
            dlc_str = table.item(row, 4).text() if table.item(row, 4) else "0"
            data_str = table.item(row, 5).text() if table.item(row, 5) else ""
            
            can_id = int(pid_str.replace('0x', ''), 16)
            dlc = int(dlc_str)
            data = bytes.fromhex(data_str.replace(' ', ''))
            
            message = CANMessage(
                timestamp=0,
                can_id=can_id,
                dlc=dlc,
                data=data
            )
        
        # Show bit field viewer
        if message:
            
            # Create and show dialog
            dialog = BitFieldViewerDialog(self, message)
            dialog.show()
        else:
            QMessageBox.warning(self, "Bit Field Viewer", "Mensagem não encontrada!")
    
    def show_filter_dialog(self):
        """Show filter configuration dialog"""
        dialog = FilterDialog(self, self.message_filters)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update filters
            self.message_filters = dialog.get_filters()
            
            # Apply filters immediately
            self.apply_message_filters()
            
            # Show notification sobre filtros
            if self.message_filters['enabled']:
                filter_count = len(self.message_filters['id_filters'])
                self.show_notification(
                    t('notif_filters_enabled', count=filter_count),
                    3000
                )
            else:
                self.show_notification(t('notif_filters_disabled'), 2000)
    
    def show_trigger_dialog(self):
        """Show trigger configuration dialog"""
        from PyQt6.QtWidgets import QDialog
        
        self.logger.info("Abrindo dialog de triggers")
        
        dialog = TriggerDialog(self, self.triggers)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update triggers
            trigger_config = dialog.get_triggers()
            self.triggers_enabled = trigger_config['enabled']
            self.triggers = trigger_config['triggers']
            
            self.logger.info(f"Triggers atualizados: {len(self.triggers)} configurados, Enabled={self.triggers_enabled}")
            
            # Feedback
            if self.triggers_enabled:
                self.statusBar().showMessage(
                    f"⚡ Triggers ativados: {len(self.triggers)} configurado(s)",
                    3000
                )
            else:
                self.show_notification(t('notif_triggers_disabled'), 2000)
    
    def apply_message_filters(self):
        """Apply filters to displayed messages"""
        if not self.message_filters['enabled']:
            # If filters disabled, show all rows
            for row in range(self.receive_table.rowCount()):
                self.receive_table.setRowHidden(row, False)
            return
        
        id_filters = self.message_filters['id_filters']
        show_only = self.message_filters['show_only']
        
        # Apply ID filter
        for row in range(self.receive_table.rowCount()):
            try:
                # Get PID and Channel from row
                # Tracer: ID(0), Time(1), Channel(2), PID(3), DLC(4), Data(5), ASCII(6), Comment(7)
                # Monitor: ID(0), Count(1), Channel(2), PID(3), DLC(4), Data(5), Period(6), ASCII(7), Comment(8)
                id_item = self.receive_table.item(row, 3)  # PID column (column 3)
                channel_item = self.receive_table.item(row, 2)  # Channel column (column 2)
                
                if not id_item:
                    continue
                
                id_str = id_item.text().replace("0x", "").replace("0X", "")
                msg_id = int(id_str, 16)
                channel = channel_item.text() if channel_item else "CAN1"
                
                # Apply filter logic (check channel_filters first)
                channel_filters = self.message_filters.get('channel_filters', {})
                should_hide = False
                
                if channel_filters and len(channel_filters) > 0:
                    # Usar filtros por canal
                    if channel in channel_filters:
                        # Filter specific to this channel
                        channel_filter = channel_filters[channel]
                        channel_ids = channel_filter.get('ids', [])
                        channel_show_only = channel_filter.get('show_only', True)
                        
                        if channel_ids:
                            if channel_show_only:
                                should_hide = msg_id not in channel_ids
                            else:
                                should_hide = msg_id in channel_ids
                    elif 'ALL' in channel_filters:
                        # "ALL" filter (applies to all channels)
                        channel_filter = channel_filters['ALL']
                        channel_ids = channel_filter.get('ids', [])
                        channel_show_only = channel_filter.get('show_only', True)
                        
                        if channel_ids:
                            if channel_show_only:
                                should_hide = msg_id not in channel_ids
                            else:
                                should_hide = msg_id in channel_ids
                else:
                    # Use global filters (legacy)
                    if show_only:
                        # Whitelist: show only IDs in list
                        should_hide = msg_id not in id_filters if id_filters else False
                    else:
                        # Blacklist: hide IDs in list
                        should_hide = msg_id in id_filters
                
                self.receive_table.setRowHidden(row, should_hide)
                
            except Exception as e:
                print(f"Erro ao aplicar filtro na linha {row}: {e}")
                continue
    
    def check_and_fire_triggers(self, msg: CANMessage):
        """Verifica se mensagem recebida ativa algum trigger e envia resposta"""
        if not self.triggers_enabled or not self.can_bus:
            return
        
        for trigger in self.triggers:
            if not trigger.get('enabled', True):
                continue
            
            try:
                # Parse trigger ID
                trigger_id_str = trigger.get('trigger_id', '0x000').replace('0x', '').replace('0X', '')
                trigger_id = int(trigger_id_str, 16)
                
                # Check if ID matches
                if msg.can_id != trigger_id:
                    continue
                
                # Check data (if specified)
                trigger_data = trigger.get('trigger_data', '')
                if trigger_data and trigger_data != 'Any':
                    # Parse trigger data
                    trigger_bytes = bytes.fromhex(trigger_data.replace(' ', ''))
                    # Compare only the specified bytes
                    if len(trigger_bytes) > 0:
                        if msg.data[:len(trigger_bytes)] != trigger_bytes:
                            continue
                
                # Trigger matched! Send TX message
                tx_id_str = trigger.get('tx_id', '0x000').replace('0x', '').replace('0X', '')
                tx_id = int(tx_id_str, 16)
                
                tx_data_str = trigger.get('tx_data', '00 00 00 00 00 00 00 00').replace(' ', '')
                tx_data = bytes.fromhex(tx_data_str)
                
                # Trigger log
                comment = trigger.get('comment', '')
                self.logger.log_trigger(trigger_id, tx_id, comment)
                
                # Enviar mensagem
                if CAN_AVAILABLE and (self.can_bus_manager or self.can_bus):
                    can_msg = can.Message(
                        arbitration_id=tx_id,
                        data=tx_data,
                        is_extended_id=(tx_id > 0x7FF)
                    )
                    # Send trigger to all buses
                    self._send_can_message(can_msg, None)
                    self.logger.log_can_message('TX', tx_id, tx_data, len(tx_data))
                    
                    # Feedback no status bar
                    self.statusBar().showMessage(
                        f"⚡ Trigger fired: 0x{trigger_id:03X} → 0x{tx_id:03X} {comment}",
                        2000
                    )
                
            except Exception as e:
                print(f"Erro ao processar trigger: {e}")
                continue
    
    def message_passes_filter(self, msg: CANMessage) -> bool:
        """Verifica se uma mensagem passa pelos filtros configurados"""
        if not self.message_filters['enabled']:
            return True
        
        id_filters = self.message_filters['id_filters']
        data_filters = self.message_filters['data_filters']
        show_only = self.message_filters['show_only']
        channel_filters = self.message_filters.get('channel_filters', {})
        
        # Filtro por Canal (prioridade sobre filtro global)
        # Only apply if filters are defined (non-empty)
        if channel_filters and len(channel_filters) > 0:
            # Check if there is a filter specific to this channel
            if msg.source in channel_filters:
                channel_filter = channel_filters[msg.source]
                channel_ids = channel_filter.get('ids', [])
                channel_show_only = channel_filter.get('show_only', True)
                
                if channel_ids:
                    id_match = msg.can_id in channel_ids
                    if channel_show_only:
                        # Whitelist: must be in list
                        if not id_match:
                            return False
                    else:
                        # Blacklist: must not be in list
                        if id_match:
                            return False
            # If no filter for this channel, check for "ALL" filter
            elif 'ALL' in channel_filters:
                channel_filter = channel_filters['ALL']
                channel_ids = channel_filter.get('ids', [])
                channel_show_only = channel_filter.get('show_only', True)
                
                if channel_ids:
                    id_match = msg.can_id in channel_ids
                    if channel_show_only:
                        if not id_match:
                            return False
                    else:
                        if id_match:
                            return False
            # If channel_filters exists but no filter for this channel nor "ALL",
            # let it pass (do not block channels without filter)
        
        # Global ID filter (legacy, applied when no per-channel filter)
        if id_filters and not channel_filters:
            id_match = msg.can_id in id_filters
            if show_only:
                # Whitelist: must be in list
                if not id_match:
                    return False
            else:
                # Blacklist: must not be in list
                if id_match:
                    return False
        
        # Data filter (always applied)
        for data_filter in data_filters:
            try:
                byte_index = data_filter['byte_index']
                value = int(data_filter['value'], 16)
                mask = int(data_filter['mask'], 16)
                
                if byte_index < len(msg.data):
                    byte_val = msg.data[byte_index]
                    if (byte_val & mask) != (value & mask):
                        return False
            except:
                continue
        
        return True
    
    def on_usb_device_connected(self, device):
        """Callback when a USB device is connected (thread-safe)"""
        self.logger.info(f"Dispositivo USB conectado: {device}")
        
        # Show notification (thread-safe)
        QTimer.singleShot(0, lambda: self.show_notification(
            f"🔌 {t('msg_device_connected').format(device=device.name)}",
            5000
        ))
    
    def on_usb_device_disconnected(self, device):
        """Callback when a USB device is disconnected (thread-safe)"""
        self.logger.info(f"Dispositivo USB desconectado: {device}")
        
        # Check if the disconnected device is the one in use
        current_device = self.config.get('channel', '')
        if device.path == current_device:
            self.logger.warning(f"Dispositivo em uso foi desconectado: {device.path}")
            
            # If connected, disconnect automatically
            if self.connected:
                self.logger.info("Desconectando automaticamente devido à remoção do dispositivo")
                
                # Executar na thread principal usando QTimer
                QTimer.singleShot(0, self._handle_device_disconnection)
        
        # Show notification (thread-safe)
        QTimer.singleShot(0, lambda: self.show_notification(
            f"🔌 {t('msg_device_disconnected').format(device=device.name)}",
            5000
        ))
    
    def _handle_device_disconnection(self):
        """Handle device disconnection in main thread"""
        try:
            self.disconnect()
            
            QMessageBox.warning(
                self,
                t('warning'),
                f"{t('msg_device_disconnected').format(device='USB Device')}\n\n"
                f"Connection has been closed."
            )
        except Exception as e:
            self.logger.error(f"Error in device disconnected callback: {e}")
    
    def _init_protocol_decoders(self):
        """Inicializa protocol decoders"""
        try:
            # Register available decoders (DISABLED by default)
            ftcan_decoder = FTCANProtocolDecoder()
            obd2_decoder = OBD2ProtocolDecoder()
            
            self.decoder_manager.register_decoder(ftcan_decoder)
            self.decoder_manager.register_decoder(obd2_decoder)
            
            # Load saved configuration (if exists)
            decoder_config = self.config.get('protocol_decoders', {})
            if decoder_config:
                # If saved config exists, use it
                self.decoder_manager.load_config(decoder_config)
            else:
                # If no config, DISABLE all by default
                self.decoder_manager.set_decoder_enabled('FTCAN 2.0', False)
                self.decoder_manager.set_decoder_enabled('OBD-II', False)
                self.logger.info("Protocol decoders initialized as DISABLED by default")
            
            self.logger.info(f"Protocol decoders initialized: {len(self.decoder_manager.get_all_decoders())} decoders")
        except Exception as e:
            self.logger.error(f"Error initializing protocol decoders: {e}")
    
    def show_decoder_manager(self):
        """Mostra o dialog do Decoder Manager"""
        dialog = DecoderManagerDialog(self)
        dialog.exec()
        
        # Save configuration on close
        decoder_config = self.decoder_manager.save_config()
        self.config['protocol_decoders'] = decoder_config
        self.config_manager.save(self.config)
    
    def show_ftcan_dialog(self):
        """Show FTCAN Protocol Analyzer dialog"""
        # Check simulation mode
        simulation_mode = self.config.get('simulation_mode', False)
        self.logger.info(f"=== FTCAN Dialog Opening ===")
        self.logger.info(f"Simulation mode: {simulation_mode}")
        self.logger.info(f"Connected: {self.connected}")
        self.logger.info(f"CAN_AVAILABLE: {CAN_AVAILABLE}")
        
        # Check if there is at least one bus at 1 Mbps
        buses_1mbps_connected = []  # Actually connected buses at 1Mbps
        buses_1mbps_config = []     # Configured for 1Mbps (for simulation mode)
        has_any_bus = False
        
        if self.can_bus_manager:
            for name, bus in self.can_bus_manager.buses.items():
                has_any_bus = True
                self.logger.info(f"Bus {name}: connected={bus.connected}, baudrate={bus.config.baudrate}")
                
                # Check if configured for 1Mbps
                if bus.config.baudrate == 1000000:
                    buses_1mbps_config.append((name, bus))
                    self.logger.info(f"  → Configured for 1Mbps")
                    # If connected, add to connected list
                    if bus.connected:
                        buses_1mbps_connected.append((name, bus))
                        self.logger.info(f"  → Connected and ready!")
        
        self.logger.info(f"Results: connected={len(buses_1mbps_connected)}, configured={len(buses_1mbps_config)}")
        
        # If no buses at all, show connection error
        if not has_any_bus:
            self.logger.warning("No buses found at all")
            QMessageBox.warning(
                self,
                t('decoder_not_connected_title'),
                t('decoder_not_connected_msg')
            )
            return
        
        # Determine which buses to use
        buses_to_use = []
        
        # Priority 1: Use connected 1Mbps buses (real connection)
        if buses_1mbps_connected:
            buses_to_use = buses_1mbps_connected
            self.logger.info(f"✓ Using {len(buses_to_use)} connected 1Mbps bus(es)")
        
        # Priority 2: In simulation mode, use configured 1Mbps buses
        elif (simulation_mode or not CAN_AVAILABLE) and buses_1mbps_config:
            self.logger.info(f"✓ Simulation mode: using {len(buses_1mbps_config)} configured 1Mbps bus(es)")
            buses_to_use = buses_1mbps_config
            # Auto-connect if not already connected
            if not self.connected:
                self.logger.info("Auto-connecting buses in simulation mode")
                self.can_bus_manager.connect_all(simulation=True)
                self.connected = True
        
        # Priority 3: Connected but buses show disconnected (connection failed) - try simulation
        elif self.connected and not buses_1mbps_connected and buses_1mbps_config:
            self.logger.warning("Connected flag is True but no buses actually connected - switching to simulation")
            buses_to_use = buses_1mbps_config
            self.can_bus_manager.connect_all(simulation=True)
        
        # If no buses at 1Mbps, show baudrate error
        if not buses_to_use:
            # Build detailed message with current bus status
            bus_status = []
            all_disconnected = True
            has_1mbps_config = False
            if self.can_bus_manager:
                for name, bus in self.can_bus_manager.buses.items():
                    status = "✓ connected" if bus.connected else "✗ disconnected"
                    if bus.connected:
                        all_disconnected = False
                    baudrate_kbps = bus.config.baudrate // 1000
                    # Check if this bus is configured for 1Mbps
                    if bus.config.baudrate == 1000000:
                        has_1mbps_config = True
                        bus_status.append(f"  • {name}: {status}, {baudrate_kbps} Kbps ✓ (correct baudrate)")
                    else:
                        bus_status.append(f"  • {name}: {status}, {baudrate_kbps} Kbps")
            
            status_text = "\n".join(bus_status) if bus_status else "  No buses configured"
            
            # Different message based on situation
            if all_disconnected and has_1mbps_config:
                # Has correct config but not connected - clearer message
                bus_with_1mbps = [name for name, kbps in [(n, b.config.baudrate // 1000) for n, b in self.can_bus_manager.buses.items()] if kbps == 1000]
                bus_name = bus_with_1mbps[0] if bus_with_1mbps else "CAN"
                
                message = (
                    f"✓ {bus_name} is correctly configured for FTCAN (1 Mbps)\n\n"
                    f"⚠️ Click the \"Connect\" button to start the CAN interface.\n\n"
                    f"{t('decoder_configured_buses')}\n{status_text}"
                )
            elif all_disconnected and not has_1mbps_config:
                # Not connected AND no 1Mbps config
                message = (
                    f"{t('ftcan_requires_1mbps')}\n\n"
                    f"{t('ftcan_all_disconnected')}\n\n"
                    f"{t('decoder_configured_buses')}\n{status_text}\n\n"
                    f"{t('ftcan_tip_configure')}"
                )
            else:
                # Connected but wrong baudrate
                message = (
                    f"{t('ftcan_requires_1mbps')}\n\n"
                    f"{t('ftcan_no_1mbps_bus')}\n\n"
                    f"{t('decoder_current_bus_status')}\n{status_text}\n\n"
                    f"{t('ftcan_tip_configure')}"
                )
            
            QMessageBox.warning(
                self,
                t('ftcan_invalid_baudrate_title'),
                message
            )
            return
        
        # If dialog already open, just bring to front
        if hasattr(self, '_ftcan_dialog') and self._ftcan_dialog:
            self._ftcan_dialog.raise_()
            self._ftcan_dialog.activateWindow()
            return
        
        # Log which buses will be used
        bus_names = [name for name, _ in buses_to_use]
        self.logger.info(f"Opening FTCAN Dialog with buses: {', '.join(bus_names)}")
        
        # Create dialog with list of available buses
        dialog = FTCANDialog(self, buses_1mbps=buses_to_use)
        
        # If there are already received messages, add them to dialog
        for msg in self.received_messages:
            dialog.add_message(msg)
        
        # Conecta para receber novas mensagens
        self._ftcan_dialog = dialog
        
        # Connect close signal to clear reference
        dialog.finished.connect(self._on_ftcan_dialog_closed)
        
        # Show non-modally (allows interaction with main window)
        dialog.show()
    
    def _on_ftcan_dialog_closed(self):
        """Callback when FTCAN Analyzer is closed"""
        self._ftcan_dialog = None
    
    def show_obd2_dialog(self):
        """Show OBD-II Monitor dialog"""
        # Check simulation mode
        simulation_mode = self.config.get('simulation_mode', False)
        
        # Check if there is at least one connected bus (or any bus in simulation mode)
        has_any_bus = False
        has_connected_bus = False
        
        if self.can_bus_manager:
            for name, bus in self.can_bus_manager.buses.items():
                has_any_bus = True
                if bus.connected:
                    has_connected_bus = True
                    break
        
        # In simulation mode OR if CAN not available, allow opening if we have any bus configured
        if (simulation_mode or not CAN_AVAILABLE) and has_any_bus:
            self.logger.info("Simulation/No-CAN mode: allowing OBD-II Monitor")
            # Auto-connect if not already connected
            if not has_connected_bus:
                self.logger.info("Auto-connecting buses in simulation mode for OBD-II")
                self.can_bus_manager.connect_all(simulation=True)
                self.connected = True
        # If connected but buses show as disconnected (connection failed), try simulation
        elif self.connected and not has_connected_bus and has_any_bus:
            self.logger.warning("Connected flag is True but no buses are actually connected - switching to simulation")
            self.can_bus_manager.connect_all(simulation=True)
        elif not has_connected_bus:
            # Not in simulation or no buses connected
            QMessageBox.warning(
                self,
                t('decoder_not_connected_title'),
                t('decoder_not_connected_msg')
            )
            return
        
        # If dialog already open, just bring to front
        if hasattr(self, '_obd2_dialog') and self._obd2_dialog:
            self._obd2_dialog.raise_()
            self._obd2_dialog.activateWindow()
            return
        
        dialog = OBD2Dialog(self, can_bus_manager=self.can_bus_manager)
        
        # Conecta para receber novas mensagens
        self._obd2_dialog = dialog
        
        # Connect close signal to clear reference
        dialog.finished.connect(self._on_obd2_dialog_closed)
        
        # Show non-modally (allows interaction with main window)
        dialog.show()
    
    def _on_obd2_dialog_closed(self):
        """Callback when OBD-II Monitor is closed"""
        self._obd2_dialog = None
    
    def show_gateway_dialog(self):
        """Show the Gateway configuration dialog"""
        if not self.can_bus_manager or len(self.can_bus_manager.get_bus_names()) < 2:
            QMessageBox.warning(
                self,
                t('warning'),
                "Gateway requires at least 2 CAN buses configured.\n"
                "Please configure multiple CAN buses in Settings first."
            )
            return
        
        bus_names = self.can_bus_manager.get_bus_names()
        dialog = GatewayDialog(self, self.gateway_config, bus_names)
        
        # Update stats periodically while dialog is open
        def update_stats():
            if self.can_bus_manager:
                stats = self.can_bus_manager.get_gateway_stats()
                dialog.update_stats(stats)
        
        # Create timer for stats update
        stats_timer = QTimer()
        stats_timer.timeout.connect(update_stats)
        stats_timer.start(1000)  # Update every second
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get updated config
            self.gateway_config = dialog.get_config()
            
            # Apply to CAN bus manager
            if self.can_bus_manager:
                self.can_bus_manager.set_gateway_config(self.gateway_config)
                self.logger.info(f"Gateway config updated: enabled={self.gateway_config.enabled}")
                
                # Update toolbar button
                self.update_gateway_button_state()
                
                # Show status in status bar
                if self.gateway_config.enabled:
                    route_count = len([r for r in self.gateway_config.routes if r.enabled])
                    block_count = len([r for r in self.gateway_config.block_rules if r.enabled])
                    modify_count = len([r for r in self.gateway_config.modify_rules if r.enabled])
                    
                    status_msg = f"🌉 Gateway ON | {route_count} route(s), {block_count} block(s), {modify_count} modify"
                    self.statusBar().showMessage(status_msg, 5000)
                    self.show_notification("Gateway enabled", 3000)
                else:
                    self.statusBar().showMessage("🌉 Gateway OFF", 3000)
                    self.show_notification("Gateway disabled", 3000)
        
        stats_timer.stop()
    
    def toggle_gateway_from_toolbar(self):
        """Toggle Gateway enable/disable from toolbar button"""
        if not self.can_bus_manager or len(self.can_bus_manager.get_bus_names()) < 2:
            QMessageBox.warning(
                self,
                t('warning'),
                "Gateway requires at least 2 CAN buses configured.\n"
                "Please configure multiple CAN buses in Settings first."
            )
            self.btn_gateway.setChecked(False)
            return
        
        # Toggle gateway state
        self.gateway_config.enabled = self.btn_gateway.isChecked()
        
        # Apply to CAN bus manager
        if self.can_bus_manager:
            self.can_bus_manager.set_gateway_config(self.gateway_config)
        
        # Update button appearance
        self.update_gateway_button_state()
        
        # Show notification and status bar
        if self.gateway_config.enabled:
            route_count = len([r for r in self.gateway_config.routes if r.enabled])
            status_msg = f"🌉 Gateway ON | {route_count} active route(s)"
            self.statusBar().showMessage(status_msg, 5000)
            self.show_notification("🌉 Gateway enabled", 2000)
            self.logger.info("Gateway enabled from toolbar")
        else:
            self.statusBar().showMessage("🌉 Gateway OFF", 3000)
            self.show_notification("Gateway disabled", 2000)
            self.logger.info("Gateway disabled from toolbar")
    
    def update_gateway_button_state(self):
        """Update gateway button text and style based on state"""
        if self.gateway_config.enabled:
            self.btn_gateway.setText("🌉 Gateway: ON")
            self.btn_gateway.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_gateway.setChecked(True)
        else:
            self.btn_gateway.setText("🌉 Gateway: OFF")
            self.btn_gateway.setStyleSheet("")
            self.btn_gateway.setChecked(False)
    
    def toggle_split_screen(self):
        """Toggle split-screen mode"""
        self.split_screen_mode = not self.split_screen_mode
        
        if self.split_screen_mode:
            # Enable split-screen
            if not self.can_bus_manager or len(self.can_bus_manager.get_bus_names()) < 2:
                QMessageBox.warning(
                    self,
                    t('warning'),
                    "Split-screen mode requires at least 2 CAN buses.\n"
                    "Please configure multiple CAN buses in Settings first."
                )
                self.split_screen_mode = False
                return
            
            # Show channel selection dialog
            bus_names = self.can_bus_manager.get_bus_names()
            
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle(t('split_screen_mode'))
            layout = QVBoxLayout(dialog)
            
            # Left panel channel
            left_layout = QHBoxLayout()
            left_layout.addWidget(QLabel(t('split_screen_left') + ":"))
            left_combo = QComboBox()
            for bus in bus_names:
                left_combo.addItem(bus)
            left_layout.addWidget(left_combo)
            layout.addLayout(left_layout)
            
            # Right panel channel
            right_layout = QHBoxLayout()
            right_layout.addWidget(QLabel(t('split_screen_right') + ":"))
            right_combo = QComboBox()
            for bus in bus_names:
                right_combo.addItem(bus)
            if len(bus_names) > 1:
                right_combo.setCurrentIndex(1)
            right_layout.addWidget(right_combo)
            layout.addLayout(right_layout)
            
            # Buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | 
                QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.split_screen_left_channel = left_combo.currentText()
                self.split_screen_right_channel = right_combo.currentText()
                
                # Rebuild receive panel with split view
                self._setup_split_screen_view()
                self.show_notification(f"Split-screen enabled: {self.split_screen_left_channel} | {self.split_screen_right_channel}", 3000)
            else:
                self.split_screen_mode = False
        else:
            # Disable split-screen
            self._setup_single_screen_view()
            self.show_notification("Split-screen disabled", 3000)
    
    def _setup_split_screen_view(self):
        """Setup split-screen view with two tables"""
        # Clear existing layout
        while self.receive_container_layout.count():
            item = self.receive_container_layout.takeAt(0)
            if item.widget():
                item.widget().setVisible(False)
        
        # Create horizontal splitter for two tables
        split_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel
        left_panel = QGroupBox(f"Channel: {self.split_screen_left_channel}")
        left_layout = QVBoxLayout(left_panel)
        
        self.receive_table_left = QTableWidget()
        self.setup_receive_table_for_widget(self.receive_table_left)
        left_layout.addWidget(self.receive_table_left)
        
        # Right panel
        right_panel = QGroupBox(f"Channel: {self.split_screen_right_channel}")
        right_layout = QVBoxLayout(right_panel)
        
        self.receive_table_right = QTableWidget()
        self.setup_receive_table_for_widget(self.receive_table_right)
        right_layout.addWidget(self.receive_table_right)
        
        # Add panels to splitter
        split_splitter.addWidget(left_panel)
        split_splitter.addWidget(right_panel)
        split_splitter.setSizes([500, 500])  # Equal split
        
        # Add splitter to container
        self.receive_container_layout.addWidget(split_splitter)
        
        # Update group box title
        self.receive_group.setTitle(f"Receive (Monitor) - Split: {self.split_screen_left_channel} | {self.split_screen_right_channel}")
        
        # Clear existing messages and reload with split
        self._reload_messages_split_screen()
        
        self.logger.info(f"Split-screen view activated: {self.split_screen_left_channel} | {self.split_screen_right_channel}")
    
    def _setup_single_screen_view(self):
        """Restore single screen view"""
        # Clear existing layout
        while self.receive_container_layout.count():
            item = self.receive_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Restore main table
        self.receive_table.setVisible(True)
        self.receive_container_layout.addWidget(self.receive_table)
        
        # Clear split tables
        self.receive_table_left = None
        self.receive_table_right = None
        
        # Update group box title
        mode_text = "Tracer" if self.tracer_mode else "Monitor"
        self.receive_group.setTitle(f"Receive ({mode_text})")
        
        # Reload all messages
        self._reload_all_messages()
        
        self.logger.info("Single screen view restored")
    
    def setup_receive_table_for_widget(self, table_widget):
        """Setup a receive table widget with proper configuration"""
        if self.tracer_mode:
            # Modo Tracer: ID, Time, Channel, PID, DLC, Data, ASCII, Comment
            table_widget.setColumnCount(8)
            table_widget.setHorizontalHeaderLabels(['ID', 'Time', t('col_channel'), 'PID', 'DLC', 'Data', 'ASCII', 'Comment'])
            table_widget.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        else:
            # Modo Monitor: ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
            table_widget.setColumnCount(9)
            table_widget.setHorizontalHeaderLabels(['ID', 'Count', t('col_channel'), 'PID', 'DLC', 'Data', 'Period', 'ASCII', 'Comment'])
            table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Common settings
        table_widget.verticalHeader().setVisible(False)
        font = QFont("Courier New", 14)
        table_widget.setFont(font)
        table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_widget.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # Connect context menu with lambda to pass the table
        table_widget.customContextMenuRequested.connect(
            lambda pos, t=table_widget: self._show_context_menu_for_table(t, pos)
        )
        
        # Column sizing
        header = table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        if self.tracer_mode:
            header.resizeSection(0, 60)   # ID
            header.resizeSection(1, 100)  # Time
            header.resizeSection(2, 70)   # Channel
            header.resizeSection(3, 80)   # PID
            header.resizeSection(4, 60)   # DLC
            header.resizeSection(5, 250)  # Data
            header.resizeSection(6, 100)  # ASCII
            header.resizeSection(7, 150)  # Comment
        else:
            header.resizeSection(0, 40)   # ID
            header.resizeSection(1, 60)   # Count
            header.resizeSection(2, 70)   # Channel
            header.resizeSection(3, 80)   # PID
            header.resizeSection(4, 50)   # DLC
            header.resizeSection(5, 250)  # Data
            header.resizeSection(6, 70)   # Period
            header.resizeSection(7, 100)  # ASCII
            header.resizeSection(8, 150)  # Comment
        
        header.setStretchLastSection(True)
    
    def _reload_messages_split_screen(self):
        """Reload all messages in split-screen mode"""
        if not self.split_screen_mode or not self.receive_table_left or not self.receive_table_right:
            return
        
        # Clear both tables
        self.receive_table_left.setRowCount(0)
        self.receive_table_right.setRowCount(0)
        
        # Reload messages from received_messages
        for msg in self.received_messages:
            if self.tracer_mode:
                if msg.source == self.split_screen_left_channel:
                    self._add_message_to_table(msg, self.receive_table_left, highlight=False)
                elif msg.source == self.split_screen_right_channel:
                    self._add_message_to_table(msg, self.receive_table_right, highlight=False)
            else:
                # Monitor mode - need to regroup
                pass  # Will be handled by normal monitor logic
    
    def _reload_all_messages(self):
        """Reload all messages in single screen mode"""
        self.receive_table.setRowCount(0)
        self.message_counters.clear()
        self.message_last_timestamp.clear()
        
        # Reload messages
        for msg in self.received_messages:
            if self.tracer_mode:
                self.add_message_tracer_mode(msg, highlight=False)
            else:
                self.add_message_monitor_mode(msg, highlight=False)
    
    def _add_message_to_table(self, msg: CANMessage, table: QTableWidget, highlight: bool = True):
        """Add message to a specific table (for split-screen)"""
        if self.tracer_mode:
            # Tracer mode
            dt = datetime.fromtimestamp(msg.timestamp)
            time_str = dt.strftime("%S.%f")[:-3]
            pid_str = f"0x{msg.can_id:03X}"
            data_str = " ".join([f"{b:02X}" for b in msg.data])
            ascii_str = msg.to_ascii()
            
            row = table.rowCount()
            table.insertRow(row)
            
            id_item = QTableWidgetItem(str(row + 1))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            dlc_item = QTableWidgetItem(str(msg.dlc))
            dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            table.setItem(row, 0, id_item)
            table.setItem(row, 1, QTableWidgetItem(time_str))
            
            channel_item = QTableWidgetItem(msg.source)
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, channel_item)
            
            table.setItem(row, 3, QTableWidgetItem(pid_str))
            table.setItem(row, 4, dlc_item)
            table.setItem(row, 5, QTableWidgetItem(data_str))
            table.setItem(row, 6, QTableWidgetItem(ascii_str))
            table.setItem(row, 7, QTableWidgetItem(msg.comment))
            
            table.scrollToBottom()
        else:
            # Monitor mode - similar to add_message_monitor_mode but for specific table
            # This would need more complex logic to maintain per-table counters
            pass
    
    def closeEvent(self, event):
        """Evento chamado ao fechar a janela"""
        # Stop USB monitor
        if hasattr(self, 'usb_monitor'):
            self.usb_monitor.stop_monitoring()
        
        # Disconnect if connected
        if self.connected:
            self.disconnect()
        
        # Accept close event
        event.accept()


