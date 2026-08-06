"""
OBD-II Dialog - Interface for OBD-II monitoring
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QCheckBox, QSpinBox,
    QHeaderView, QTabWidget, QWidget, QListWidget, QListWidgetItem,
    QSplitter, QTextEdit, QComboBox, QMessageBox, QFileDialog, QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QColor
from typing import List, Dict, Optional, Set
import can
import time
import csv
from datetime import datetime
from ..models import CANMessage
from ..decoders.decoder_obd2 import OBD2_PIDS
from ..i18n import t
from ..storage_paths import dialog_path
from ..vag_uds import (
    DTC_STATUS_MASKS_GUI,
    DtcRecord,
    IsotpReassembler,
    MODULES,
    VagModule,
    VAG_TX_BASE,
    VAG_RX_OFFSET,
    build_flow_control_frame,
    build_single_frame,
    describe_negative,
    format_dtc_record_line,
    is_response_pending,
    module_at_logical_addr,
    parse_isotp_single,
    parse_read_dtc_response,
)


class OBD2Dialog(QDialog):
    """Dialog for OBD-II monitoring"""
    
    # Signal to process CAN messages in a thread-safe way
    message_received = pyqtSignal(str, object)
    
    def __init__(self, parent=None, can_bus_manager=None):
        super().__init__(parent)
        self.setWindowTitle(t('obd2_monitor_title'))
        self.resize(1200, 760)
        
        self.can_bus_manager = can_bus_manager
        self.selected_pids: Set[int] = set()
        self.pid_values: Dict[int, Dict] = {}  # {pid: {value, timestamp, ecu_id}}
        self.polling_active = False
        self.poll_interval = 1.0  # segundos
        self.available_pids: Set[int] = set()  # PIDs suportados pelo ECU
        self.checking_pids = False  # Flag for verification in progress
        self._poll_ui_locked = False  # Temporary lock (single-shot, etc.)
        
        # Statistics
        self.request_count = 0
        self.response_count = 0
        
        # Select first available bus
        self.active_bus = None
        if can_bus_manager and can_bus_manager.buses:
            self.active_bus = list(can_bus_manager.buses.values())[0]
        
        self._setup_ui()
        
        # Polling timer
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_pids)
        
        # Timer for UI updates (runs continuously to update connection status)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Atualiza a cada 500ms
        
        # Buffer to store received messages (for DTCs and single-shot)
        self.received_messages = []
        self.receiving_dtcs = False
        self.dtcs_found = []
        self.dtc_buffer = bytearray()  # Buffer para juntar frames multi-frame
        self.dtc_response_received = False  # Flag para rastrear se recebeu resposta de DTC
        self.dtc_expected_len: Optional[int] = None  # ISO-TP payload length (bytes after PCI)
        self.dtc_expected_bytes: Optional[int] = None  # DTC payload bytes (count*2) for non-ISO-TP split frames
        self._resume_polling_after_dtcs = False

        # VIN detection (Service 09 PID 02) - ISO-TP multi-frame
        self.receiving_vin = False
        self.vin_response_received = False
        self.vin_buffer = bytearray()
        self.vin_expected_len: Optional[int] = None
        self.vin_value: Optional[str] = None

        # VAG UDS per-module DTC session (Airbag, Painel, etc.)
        self.receiving_vag_uds = False
        self.vag_module: Optional[VagModule] = None
        self.vag_operation: Optional[str] = None  # 'read' | 'clear'
        self.vag_masks_queue: List[int] = []
        self.vag_dtcs_found: List[str] = []
        self.vag_dtc_by_raw: Dict[bytes, DtcRecord] = {}
        self.vag_isotp_stalls = 0
        self.vag_rx_queue: List[CANMessage] = []
        self.vag_current_mask: Optional[int] = None
        self.vag_mask_retries_left = 0
        self.vag_response_received = False
        self.vag_isotp = IsotpReassembler()
        self.vag_step_timer = QTimer(self)
        self.vag_step_timer.setSingleShot(True)
        self.vag_step_timer.timeout.connect(self._vag_on_step_timeout)
        self.vag_clear_phase: Optional[str] = None  # 'wait_54' | 'verify'
        self.vag_clear_attempts = 0
        self.vag_clear_max_attempts = 3

        self.receiving_vag_scan = False
        self.vag_scan_addrs: List[int] = []
        self.vag_scan_found: List[VagModule] = []
        self.vag_scan_expect_rx: Optional[int] = None
        self.vag_scan_current_addr: Optional[int] = None
        self.vag_scan_timer = QTimer(self)
        self.vag_scan_timer.setSingleShot(True)
        self.vag_scan_timer.timeout.connect(self._vag_scan_on_probe_timeout)
        
        # Connect signal to process messages in a thread-safe way
        self.message_received.connect(self._process_can_message)
    
    def on_can_message(self, bus_name: str, msg: CANMessage):
        """Recebe mensagens CAN de outra thread - emite sinal para processamento thread-safe"""
        if 0x7E8 <= msg.can_id <= 0x7EF:
            self.message_received.emit(bus_name, msg)
            return
        if self.receiving_vag_uds and self.vag_module and msg.can_id == self.vag_module.rx_id:
            self.message_received.emit(bus_name, msg)
            return
        if (
            self.receiving_vag_scan
            and self.vag_scan_expect_rx is not None
            and msg.can_id == self.vag_scan_expect_rx
        ):
            self.message_received.emit(bus_name, msg)
    
    def _process_can_message(self, bus_name: str, msg: CANMessage):
        """Processa mensagens CAN na thread principal da UI (thread-safe)"""
        # Filter by selected bus (if multiple)
        if self.active_bus:
            expected = self.active_bus.config.name
            from_active = True
            if hasattr(msg, "source") and msg.source:
                from_active = msg.source == expected
            elif bus_name:
                from_active = bus_name == expected
            if not from_active and not self.receiving_vag_uds and not self.receiving_vag_scan:
                return
            if not from_active and (self.receiving_vag_uds or self.receiving_vag_scan):
                self._log_message(
                    f"VAG: aviso — resposta 0x{msg.can_id:03X} em '{getattr(msg, 'source', bus_name)}', "
                    f"bus ativo '{expected}'"
                )
        
        # Store for DTC or single-shot processing
        self.received_messages.append(msg)

        # Always show ECU responses in Raw Messages.
        is_obd_response = 0x7E8 <= msg.can_id <= 0x7EF
        is_vag_response = (
            self.receiving_vag_uds
            and self.vag_module is not None
            and msg.can_id == self.vag_module.rx_id
        )
        if is_obd_response or is_vag_response:
            try:
                self._add_raw_message(msg, self._describe_obd2_response(msg))
            except Exception:
                pass
        
        if self.receiving_vag_uds and is_vag_response:
            self._process_vag_uds_response(msg)
            return

        if self.receiving_vag_scan and self.vag_scan_expect_rx == msg.can_id:
            self._vag_scan_on_response(msg)
            return
        
        # If receiving DTCs, process ALL frames (first and continuation)
        if self.receiving_dtcs and len(msg.data) >= 2:
            # Service 03 responses can be single-frame (0x43) or ISO-TP multi-frame (0x10/0x2N).
            if msg.data[1] == 0x43:
                self._process_dtc_response(msg)
            else:
                frame_type = msg.data[0] & 0xF0
                # ISO-TP First Frame: payload starts at data[2]
                if frame_type == 0x10 and len(msg.data) >= 3 and msg.data[2] == 0x43:
                    self._process_dtc_response(msg)
                # ISO-TP Consecutive Frames: only if we already started collecting DTC ISO-TP
                elif frame_type == 0x20 and self.dtc_expected_len is not None:
                    self._process_dtc_response(msg)
                # Fallback (Arduino simulator): a second "continuation" CAN frame carrying remaining DTC bytes.
                # Example from tools/arduino/arduino_obd2_ecu_simulator.ino:
                #   frame1: [0x06, 0x43, 0x04, 0x01, 0x71, 0x03, 0x00, 0x40]
                #   frame2: [0x04, 0x35, 0x92, 0x34, 0x00, 0x00, 0x00, 0x00]
                elif (
                    self.dtc_expected_bytes is not None
                    and self.dtc_expected_len is None
                    and len(self.dtc_buffer) > 0
                    and len(self.dtc_buffer) < self.dtc_expected_bytes
                    and msg.data[0] in (0x04, 0x05, 0x06, 0x07)
                    and msg.data[1] not in (0x41, 0x43)
                ):
                    self._process_dtc_response(msg)

        # VIN detection (ISO-TP): handle FF/CF frames (0x10/0x21..)
        elif self.receiving_vin and len(msg.data) >= 2:
            self._process_vin_response(msg)
        
        # If polling or single shot, process PID
        elif len(msg.data) >= 3 and msg.data[1] == 0x41:
            pid = msg.data[2]
            
            # If checking available PIDs, process support PIDs
            if self.checking_pids and pid in [0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xE0]:
                self._process_support_pid_response(msg, pid)
            
            # If polling or single shot, process normally
            if pid in self.selected_pids or self.polling_active:
                self._process_response(msg, pid)
                self.response_count += 1

    def _describe_obd2_response(self, msg: CANMessage) -> str:
        """Best-effort decode label for Raw Messages tab."""
        data = msg.data or b""

        # If we are in a specific acquisition flow, prefer a clearer label.
        if getattr(self, "receiving_vin", False) and len(data) >= 1:
            pci = (data[0] >> 4) & 0x0F
            if pci == 0x1:
                return "Response: VIN (ISO-TP First Frame)"
            if pci == 0x2:
                return "Response: VIN (ISO-TP Consecutive Frame)"
            return "Response: VIN"

        if getattr(self, "receiving_vag_uds", False):
            return "Response: VAG UDS"

        if getattr(self, "receiving_dtcs", False):
            # DTC responses can be single-frame (0x43) or multi-frame (ISO-TP).
            if len(data) >= 2 and data[1] == 0x43:
                return "Response: Read DTCs (Service 03)"
            if len(data) >= 1:
                pci = (data[0] >> 4) & 0x0F
                if pci == 0x1:
                    return "Response: DTCs (ISO-TP First Frame)"
                if pci == 0x2:
                    return "Response: DTCs (ISO-TP Consecutive Frame)"
            return "Response: DTCs"

        if len(data) >= 2:
            service = data[1]
            # Service 01 response (0x41) with PID
            if service == 0x41 and len(data) >= 3:
                pid = data[2]
                pid_info = OBD2_PIDS.get(pid, {})
                pid_name = pid_info.get('name', f"PID 0x{pid:02X}")
                # Include decoded value when possible (helps for quick debugging).
                try:
                    value_str = self._decode_pid_value(pid, data[3:])
                    return f"Response: {pid_name} (0x{pid:02X}) = {value_str}"
                except Exception:
                    return f"Response: {pid_name} (0x{pid:02X})"

            # Service 03 response (0x43) - DTCs
            if service == 0x43:
                return "Response: Read DTCs (Service 03)"

            # Service 04 response (0x44) - Clear DTCs
            if service == 0x44:
                return "Response: Clear DTCs (Service 04)"

            # Service 09 response (0x49) - Vehicle information
            if service == 0x49 and len(data) >= 3:
                info_type = data[2]
                if info_type == 0x02:
                    return "Response: VIN (Service 09 PID 02)"

        # ISO-TP framing hint (covers VIN and any multi-frame responses)
        if len(data) >= 1:
            pci = (data[0] >> 4) & 0x0F
            if pci == 0x1:
                return "Response: ISO-TP First Frame"
            if pci == 0x2:
                return "Response: ISO-TP Consecutive Frame"
            if pci == 0x3:
                return "Response: ISO-TP Flow Control"

        return "Response"
    
    def _setup_ui(self):
        """Configura interface"""
        layout = QVBoxLayout()
        layout.setSpacing(6)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Splitter principal (PID selector | Live values)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: PID selection
        left_panel = self._create_pid_selector()
        splitter.addWidget(left_panel)
        
        # Right side: Tabs
        tabs = QTabWidget()
        
        # Tab 1: Valores em tempo real
        tab_live = self._create_live_values_tab()
        tabs.addTab(tab_live, "Live Values")
        
        # Tab 2: Mensagens raw
        tab_raw = self._create_raw_messages_tab()
        tabs.addTab(tab_raw, "Raw Messages")
        
        # Tab 3: Statistics
        tab_stats = self._create_statistics_tab()
        tabs.addTab(tab_stats, "Statistics")
        
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 1)  # Painel esquerdo (PIDs)
        splitter.setStretchFactor(1, 3)  # Right panel (values) - more space
        
        # Define larguras iniciais
        splitter.setSizes([350, 850])  # 350px para PIDs, 850px para valores
        
        layout.addWidget(splitter, stretch=1)
        
        # Footer with controls (fixed height strip)
        footer = self._create_footer()
        layout.addWidget(footer, stretch=0)
        
        self.setLayout(layout)
        self._on_dtc_protocol_changed()
        self._refresh_polling_buttons()
    
    def _create_header(self) -> QWidget:
        """Single-line status bar: protocol, bus, VIN, stats."""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setMaximumHeight(34)
        frame.setStyleSheet(
            "QFrame { border: 1px solid #c8c8c8; border-radius: 3px; background: #fafafa; }"
        )
        row = QHBoxLayout(frame)
        row.setContentsMargins(6, 1, 6, 1)
        row.setSpacing(6)

        title_label = QLabel("<b>OBD-II</b>")
        title_label.setStyleSheet("font-size: 11px; border: none; background: transparent;")
        row.addWidget(title_label)

        self.protocol_info_label = QLabel("0x7DF → 0x7E8–0x7EF")
        self.protocol_info_label.setStyleSheet(
            "color: #555; font-size: 10px; font-family: Menlo, Consolas, monospace;"
            " border: none; background: transparent;"
        )
        row.addWidget(self.protocol_info_label)

        row.addStretch()

        compact_lbl = "font-size: 10px; border: none; background: transparent;"
        if self.can_bus_manager and len(self.can_bus_manager.buses) > 1:
            ch = QLabel("<b>Ch:</b>")
            ch.setStyleSheet(compact_lbl)
            row.addWidget(ch)
            self.bus_combo = QComboBox()
            self.bus_combo.setMinimumWidth(130)
            self.bus_combo.setMaximumHeight(22)
            self.bus_combo.setStyleSheet("font-size: 10px;")
            for bus_name, bus in self.can_bus_manager.buses.items():
                if bus.connected:
                    self.bus_combo.addItem(f"{bus_name} · OK")
                else:
                    self.bus_combo.addItem(f"{bus_name} · Sim")
            self.bus_combo.currentIndexChanged.connect(self._change_active_bus)
            row.addWidget(self.bus_combo)
            self.channel_label = None
        elif self.can_bus_manager and len(self.can_bus_manager.buses) == 1:
            bus_name = list(self.can_bus_manager.buses.keys())[0]
            bus = list(self.can_bus_manager.buses.values())[0]
            self.channel_label = QLabel()
            self.channel_label.setStyleSheet(compact_lbl)
            self._update_channel_status(bus_name, bus.connected)
            row.addWidget(self.channel_label)
        else:
            self.channel_label = QLabel(
                "<b>Ch:</b> <span style='color: red;'>—</span>"
            )
            self.channel_label.setStyleSheet(compact_lbl)
            row.addWidget(self.channel_label)

        vin_l = QLabel("<b>VIN</b>")
        vin_l.setStyleSheet(compact_lbl)
        row.addWidget(vin_l)
        self.vin_value_label = QLabel("-")
        self.vin_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.vin_value_label.setStyleSheet(
            "font-family: Menlo, Consolas, monospace; font-size: 10px; font-weight: bold;"
            " color: #222; border: none; background: transparent;"
        )
        row.addWidget(self.vin_value_label)

        self.stats_label = QLabel("Req 0 · Rsp 0 · 0%")
        self.stats_label.setStyleSheet(
            "color: #888; font-size: 9px; border: none; background: transparent;"
        )
        row.addWidget(self.stats_label)

        return frame
    
    def _create_pid_selector(self) -> QWidget:
        """Create PID selection panel"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<b>Select PIDs to Monitor</b>")
        layout.addWidget(title)
        
        # Button to check available PIDs
        self.check_pids_btn = QPushButton("🔍 " + t('obd2_check_available'))
        self.check_pids_btn.clicked.connect(self._check_available_pids)
        self.check_pids_btn.setToolTip("Query ECU to discover which PIDs are supported")
        layout.addWidget(self.check_pids_btn)
        
        # Verification status
        self.check_status_label = QLabel("")
        self.check_status_label.setWordWrap(True)
        layout.addWidget(self.check_status_label)
        
        # Quick Presets como dropdown
        presets_group = QGroupBox("Quick Presets")
        presets_layout = QVBoxLayout()
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "-- Select Preset --",
            "Basic (RPM, Speed, Temp, TPS)",
            "Extended (+ Load, MAF, Fuel)",
            "Lambda/O2 Sensors",
            "Fuel System"
        ])
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        presets_layout.addWidget(self.preset_combo)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        btn_select_all = QPushButton(t('obd2_select_all'))
        btn_select_all.clicked.connect(self._select_all)
        actions_layout.addWidget(btn_select_all)
        
        btn_clear = QPushButton(t('obd2_clear_all'))
        btn_clear.clicked.connect(self._clear_selection)
        actions_layout.addWidget(btn_clear)
        
        presets_layout.addLayout(actions_layout)
        
        presets_group.setLayout(presets_layout)
        layout.addWidget(presets_group)
        
        # Compact filter (inline)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "All PIDs",
            "Engine Basic",
            "Fuel System",
            "Air/Throttle",
            "Lambda/O2",
            "Temperatures",
            "Pressures",
            "Advanced"
        ])
        self.category_combo.currentTextChanged.connect(self._filter_pids)
        filter_layout.addWidget(self.category_combo)
        layout.addLayout(filter_layout)
        
        # Available PID list
        pids_label = QLabel("<b>Available PIDs:</b>")
        layout.addWidget(pids_label)
        
        self.pid_list = QListWidget()
        self.pid_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.pid_list.itemSelectionChanged.connect(self._on_pid_selection_changed)
        
        self._populate_pid_list()
        layout.addWidget(self.pid_list)
        
        # Contador de selecionados
        self.selection_label = QLabel("Selected: 0 PIDs")
        self.selection_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        layout.addWidget(self.selection_label)
        
        widget.setLayout(layout)
        return widget
    
    def _create_live_values_tab(self) -> QWidget:
        """Cria tab de valores em tempo real"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Values table
        self.values_table = QTableWidget()
        self.values_table.setColumnCount(6)
        self.values_table.setHorizontalHeaderLabels([
            "PID", "Name", "Value", "Unit", "ECU", "Last Update"
        ])
        
        # Optimized configuration for Name and Value
        header = self.values_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # PID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Name - ajustável
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Value - ajustável
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Unit
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # ECU
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Last Update
        
        # Set initial widths for Name and Value
        self.values_table.setColumnWidth(1, 250)  # Name - mais largo
        self.values_table.setColumnWidth(2, 120)  # Value - largo o suficiente
        
        # More compact rows while keeping normal font
        self.values_table.verticalHeader().setDefaultSectionSize(24)
        self.values_table.verticalHeader().setVisible(False)
        
        self.values_table.setAlternatingRowColors(True)
        layout.addWidget(self.values_table)
        
        # Clear button
        clear_btn = QPushButton(t('obd2_clear_values'))
        clear_btn.clicked.connect(self._clear_live_values)
        clear_btn.setToolTip("Clear all values from the table")
        layout.addWidget(clear_btn)
        
        widget.setLayout(layout)
        return widget
    
    def _create_raw_messages_tab(self) -> QWidget:
        """Cria tab de mensagens raw"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Messages table
        self.raw_table = QTableWidget()
        self.raw_table.setColumnCount(5)
        self.raw_table.setHorizontalHeaderLabels([
            "Timestamp", "ID", "Type", "Data", "Decoded"
        ])
        
        # Optimized configuration
        header = self.raw_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Timestamp
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Data
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Decoded
        
        # More compact rows while keeping normal font
        self.raw_table.verticalHeader().setDefaultSectionSize(24)
        self.raw_table.verticalHeader().setVisible(False)
        
        self.raw_table.setAlternatingRowColors(True)
        layout.addWidget(self.raw_table)
        
        # Limit to 500 messages
        self.raw_table.setRowCount(0)
        self.max_raw_messages = 500
        
        widget.setLayout(layout)
        return widget
    
    def _create_statistics_tab(self) -> QWidget:
        """Create statistics tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.stats_text)
        
        widget.setLayout(layout)
        return widget
    
    def _create_footer(self) -> QWidget:
        """
        Footer layout:
        ┌─ Live polling ──────────────┐  ┌─ Diagnostics (DTCs) ─────────────────────────────────────────┐
        │ ▶ Start │ ⏸ Stop │ Single  │  │ Protocol: [▼]  Module: [▼]  [Detect ECUs]                    │
        │ Interval: [1000 ms]         │  │ TX/RX hint                [Read DTCs] [Clear DTCs] [Det.VIN] │
        └─────────────────────────────┘  └──────────────────────────────────────────────────────────────┘
                                                                              [Save Results]  [Close]
        """
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        root = QVBoxLayout(widget)
        root.setContentsMargins(0, 2, 0, 4)
        root.setSpacing(0)

        # ── Top strip: polling + diagnostics ────────────────────────
        top = QHBoxLayout()
        top.setSpacing(8)
        top.setContentsMargins(0, 0, 0, 0)

        # ── Live polling ──────────────────────────────────────────
        poll_group = QGroupBox(t("obd2_polling_group"))
        poll_group.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        poll_group.setMinimumWidth(340)
        pl = QVBoxLayout()
        pl.setSpacing(3)
        pl.setContentsMargins(8, 4, 8, 5)

        poll_btns = QHBoxLayout()
        poll_btns.setSpacing(4)
        self.start_btn = QPushButton("▶ " + t("obd2_start_polling"))
        self.start_btn.clicked.connect(self._start_polling)
        self.start_btn.setEnabled(False)
        poll_btns.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏸ " + t("obd2_stop_polling"))
        self.stop_btn.clicked.connect(self._stop_polling)
        self.stop_btn.setEnabled(False)
        poll_btns.addWidget(self.stop_btn)

        self.single_shot_btn = QPushButton(t("obd2_single_shot"))
        self.single_shot_btn.clicked.connect(self._single_shot)
        self.single_shot_btn.setEnabled(False)
        self.single_shot_btn.setToolTip("Read selected PIDs once")
        poll_btns.addWidget(self.single_shot_btn)
        pl.addLayout(poll_btns)

        ivl = QHBoxLayout()
        ivl.setSpacing(4)
        ivl.addWidget(QLabel(t("obd2_interval") + ":"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 10000)
        self.interval_spin.setValue(1000)
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.setSingleStep(100)
        self.interval_spin.setFixedWidth(90)
        self.interval_spin.setMaximumHeight(24)
        self.interval_spin.valueChanged.connect(self._update_poll_interval)
        ivl.addWidget(self.interval_spin)
        ivl.addStretch()
        pl.addLayout(ivl)
        poll_group.setLayout(pl)
        top.addWidget(poll_group)

        # ── Diagnostics ────────────────────────────────────────────
        diag_group = QGroupBox(t("obd2_diagnostics_group"))
        diag_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        dl = QVBoxLayout()
        dl.setSpacing(4)
        dl.setContentsMargins(8, 4, 8, 5)

        # Row 1: protocol selector + (VAG) module + detect button
        r1 = QHBoxLayout()
        r1.setSpacing(6)

        lbl_proto = QLabel(t("obd2_dtc_protocol") + ":")
        lbl_proto.setStyleSheet("font-weight: bold;")
        r1.addWidget(lbl_proto)

        self.dtc_protocol_combo = QComboBox()
        self.dtc_protocol_combo.addItem(t("obd2_dtc_protocol_obd"), "obd")
        self.dtc_protocol_combo.addItem(t("obd2_dtc_protocol_vag"), "vag")
        self.dtc_protocol_combo.setFixedWidth(185)
        self.dtc_protocol_combo.setMaximumHeight(24)
        self.dtc_protocol_combo.setToolTip(
            "OBD-II: broadcast 0x7DF — motor / emissões\n"
            "VAG UDS: módulo individual (Airbag, Kombi, ABS…)"
        )
        self.dtc_protocol_combo.currentIndexChanged.connect(self._on_dtc_protocol_changed)
        r1.addWidget(self.dtc_protocol_combo)

        self.vag_module_label = QLabel(t("obd2_vag_module") + ":")
        self.vag_module_label.setVisible(False)
        r1.addWidget(self.vag_module_label)

        self.vag_module_combo = QComboBox()
        self.vag_module_combo.setMinimumWidth(200)
        self.vag_module_combo.setMaximumHeight(24)
        self.vag_module_combo.setVisible(False)
        self.vag_module_combo.setToolTip("Endereço lógico VAG. Use Detectar ECUs para atualizar.")
        self._vag_populate_module_combo(list(MODULES.values()))
        self.vag_module_combo.currentIndexChanged.connect(self._on_dtc_protocol_changed)
        r1.addWidget(self.vag_module_combo, stretch=1)

        self.vag_detect_ecus_btn = QPushButton("🔍 " + t("obd2_vag_detect_ecus"))
        self.vag_detect_ecus_btn.setMaximumHeight(24)
        self.vag_detect_ecus_btn.setVisible(False)
        self.vag_detect_ecus_btn.setToolTip("Varre 0x01–0x7F via TesterPresent e atualiza a lista")
        self.vag_detect_ecus_btn.clicked.connect(self._vag_detect_ecus)
        r1.addWidget(self.vag_detect_ecus_btn)

        r1.addStretch()
        dl.addLayout(r1)

        # Row 2: TX/RX info (VAG) + action buttons
        r2 = QHBoxLayout()
        r2.setSpacing(6)

        self.vag_target_label = QLabel("")
        self.vag_target_label.setStyleSheet(
            "color: #555; font-size: 10px; font-family: Menlo, Consolas, monospace;"
        )
        self.vag_target_label.setVisible(False)
        r2.addWidget(self.vag_target_label)
        r2.addStretch()

        self.read_dtc_btn = QPushButton("📋 " + t("obd2_read_dtcs"))
        self.read_dtc_btn.clicked.connect(self._read_dtcs)
        self.read_dtc_btn.setToolTip("Ler DTCs (Service 03 / UDS 19 02)")
        r2.addWidget(self.read_dtc_btn)

        self.clear_dtc_btn = QPushButton("🗑 " + t("obd2_clear_dtcs"))
        self.clear_dtc_btn.clicked.connect(self._clear_dtcs)
        self.clear_dtc_btn.setToolTip("Apagar DTCs (Service 04 / UDS 14 FF FF FF)")
        r2.addWidget(self.clear_dtc_btn)

        self.detect_vin_btn = QPushButton("🔑 " + t("obd2_detect_vin"))
        self.detect_vin_btn.clicked.connect(self._detect_vin)
        self.detect_vin_btn.setToolTip("Detectar VIN (Service 09 PID 02)")
        r2.addWidget(self.detect_vin_btn)

        dl.addLayout(r2)
        diag_group.setLayout(dl)
        top.addWidget(diag_group)
        root.addLayout(top)

        # ── Bottom strip: save / close (right-aligned) ──────────────
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 4, 0, 0)
        bottom.setSpacing(6)
        bottom.addStretch()

        save_btn = QPushButton(t("obd2_save_results"))
        save_btn.clicked.connect(self._save_results)
        save_btn.setToolTip("Exportar valores para CSV")
        save_btn.setMinimumWidth(110)
        bottom.addWidget(save_btn)

        close_btn = QPushButton(t("btn_close"))
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(80)
        bottom.addWidget(close_btn)

        root.addLayout(bottom)
        return widget
    
    def _populate_pid_list(self, filter_category: str = "All PIDs"):
        """Populate list of available PIDs"""
        self.pid_list.clear()
        
        # Categorias
        categories = {
            "Engine Basic": [0x04, 0x05, 0x0C, 0x0D, 0x0E, 0x0F, 0x11, 0x1F],
            "Fuel System": [0x03, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x22, 0x23, 0x51, 0x52, 0x5E],
            "Air/Throttle": [0x10, 0x11, 0x45, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x4C],
            "Lambda/O2": [0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x24, 0x25, 0x26, 0x27, 
                          0x28, 0x29, 0x2A, 0x2B, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x44],
            "Temperatures": [0x05, 0x0F, 0x46, 0x5C],
            "Pressures": [0x0A, 0x0B, 0x22, 0x23, 0x32, 0x33],
            "Advanced": [0x43, 0x5D, 0x61, 0x62, 0x63]
        }
        
        for pid, info in sorted(OBD2_PIDS.items()):
            # Pular PIDs de suporte
            if info['type'] == 'bitfield':
                continue
            
            # Filtrar por categoria
            if filter_category != "All PIDs":
                if filter_category not in categories:
                    continue
                if pid not in categories[filter_category]:
                    continue
            
            item_text = f"0x{pid:02X} - {info['name']} [{info['unit']}]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, pid)
            
            # Mark if already selected
            if pid in self.selected_pids:
                item.setSelected(True)
            
            self.pid_list.addItem(item)
    
    def _filter_pids(self, category: str):
        """Filtra PIDs por categoria"""
        self._populate_pid_list(category)
    
    def _on_preset_selected(self, index: int):
        """Callback when preset is selected in dropdown"""
        if index == 0:  # "-- Select Preset --"
            return
        
        preset_map = {
            1: 'basic',
            2: 'extended',
            3: 'lambda',
            4: 'fuel'
        }
        
        if index in preset_map:
            self._apply_preset(preset_map[index])
            # Reset dropdown to "-- Select Preset --"
            self.preset_combo.setCurrentIndex(0)
    
    def _apply_preset(self, preset: str):
        """Aplica preset de PIDs"""
        presets = {
            'basic': [0x0C, 0x0D, 0x05, 0x11],  # RPM, Speed, Temp, TPS
            'extended': [0x0C, 0x0D, 0x05, 0x11, 0x04, 0x10, 0x2F, 0x42],  # + Load, MAF, Fuel, Voltage
            'lambda': [0x14, 0x15, 0x24, 0x34, 0x44],  # O2 sensors
            'fuel': [0x03, 0x06, 0x07, 0x0A, 0x22, 0x2F, 0x51, 0x52, 0x5E]  # Fuel system
        }
        
        if preset in presets:
            self.selected_pids = set(presets[preset])
            self._update_pid_selection()
    
    def _select_all(self):
        """Select all visible PIDs"""
        self.selected_pids.clear()
        for i in range(self.pid_list.count()):
            item = self.pid_list.item(i)
            if not item.isHidden():  # Only visible PIDs (respecting filter)
                pid = item.data(Qt.ItemDataRole.UserRole)
                self.selected_pids.add(pid)
        self._update_pid_selection()
    
    def _clear_selection(self):
        """Clear PID selection"""
        self.selected_pids.clear()
        self._update_pid_selection()
    
    def _check_available_pids(self):
        """Check which PIDs are available on the ECU"""
        if not self.active_bus or not self.active_bus.bus:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Cannot check PIDs: Not connected to CAN bus."
            )
            return
        
        if self.checking_pids:
            return
        
        self.checking_pids = True
        self.check_pids_btn.setEnabled(False)
        self.check_status_label.setText("🔄 Checking available PIDs...")
        self.check_status_label.setStyleSheet("color: blue;")
        
        # Clear available PID list
        self.available_pids.clear()
        
        # PIDs de suporte: 0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xE0
        support_pids = [0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xE0]
        
        # Send requests for all supported PIDs
        for support_pid in support_pids:
            try:
                request = can.Message(
                    arbitration_id=0x7DF,
                    data=[0x02, 0x01, support_pid, 0x00, 0x00, 0x00, 0x00, 0x00],
                    is_extended_id=False
                )
                self.active_bus.send(request)
                self._add_raw_request(request, f"Check Support PID 0x{support_pid:02X}")
            except Exception as e:
                self._log_message(f"Error checking PID 0x{support_pid:02X}: {e}")
        
        # Wait 2 seconds to receive all responses
        QTimer.singleShot(2000, self._check_available_pids_complete)
    
    def _check_available_pids_complete(self):
        """Callback after PID verification completes"""
        self.checking_pids = False
        self.check_pids_btn.setEnabled(True)
        
        if self.available_pids:
            # Update PID list to show only available ones
            self._update_pid_list_availability()
            
            count = len(self.available_pids)
            self.check_status_label.setText(f"✅ Found {count} available PIDs")
            self.check_status_label.setStyleSheet("color: green; font-weight: bold;")
            self._log_message(f"Found {count} available PIDs: {sorted(self.available_pids)}")
        else:
            self.check_status_label.setText("⚠️ No PIDs found. ECU may not support OBD-II or wrong baudrate.")
            self.check_status_label.setStyleSheet("color: orange;")
            self._log_message("No available PIDs found")
    
    def _process_support_pid_response(self, msg: CANMessage, support_pid: int):
        """Process support PID response (0x00, 0x20, etc.) to discover available PIDs"""
        if len(msg.data) < 7:
            return
        
        # Data is in bytes 3-6 (4 bytes = 32 bits)
        data = msg.data[3:7]
        
        # Convert to 32-bit integer
        bits = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
        
        # Cada bit representa um PID (bit 31 = PID base+1, bit 30 = PID base+2, etc.)
        base_pid = support_pid
        for i in range(1, 33):
            if bits & (1 << (32 - i)):
                pid = base_pid + i
                self.available_pids.add(pid)
        
        self._log_message(f"Support PID 0x{support_pid:02X}: found {bin(bits).count('1')} PIDs")
    
    def _update_pid_list_availability(self):
        """Atualiza lista de PIDs para mostrar disponibilidade"""
        for i in range(self.pid_list.count()):
            item = self.pid_list.item(i)
            pid = item.data(Qt.ItemDataRole.UserRole)
            
            if pid in self.available_pids:
                # PID available - enable and check
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
                original_text = item.text().replace(" ✓", "").replace(" ✗", "")
                item.setText(f"{original_text} ✓")
                item.setForeground(QColor(0, 128, 0))  # Verde
            else:
                # PID unavailable - disable and check
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                original_text = item.text().replace(" ✓", "").replace(" ✗", "")
                item.setText(f"{original_text} ✗")
                item.setForeground(QColor(128, 128, 128))  # Cinza
    
    def _bus_ready(self) -> bool:
        """True when the active bus can send (same criterion as Read DTCs)."""
        return bool(self.active_bus and getattr(self.active_bus, "bus", None))

    def _diagnostics_busy(self) -> bool:
        return bool(
            getattr(self, "receiving_dtcs", False)
            or getattr(self, "receiving_vag_uds", False)
            or getattr(self, "receiving_vin", False)
            or getattr(self, "checking_pids", False)
            or getattr(self, "_poll_ui_locked", False)
        )

    def _refresh_polling_buttons(self) -> None:
        """Keep Live Polling buttons in sync with selection / bus / session state."""
        if not hasattr(self, "start_btn"):
            return
        has_selection = len(self.selected_pids) > 0
        ready = self._bus_ready()
        busy = self._diagnostics_busy()
        can_poll = has_selection and ready and not busy and not self.polling_active

        self.start_btn.setEnabled(can_poll)
        self.single_shot_btn.setEnabled(can_poll)
        if hasattr(self, "stop_btn"):
            self.stop_btn.setEnabled(self.polling_active and not busy)

    def _on_pid_selection_changed(self):
        """Callback when PID selection changes"""
        self.selected_pids.clear()
        for item in self.pid_list.selectedItems():
            pid = item.data(Qt.ItemDataRole.UserRole)
            self.selected_pids.add(pid)

        self.selection_label.setText(f"Selected: {len(self.selected_pids)} PIDs")
        self._refresh_polling_buttons()

    def _update_pid_selection(self):
        """Update visual PID selection"""
        self.pid_list.blockSignals(True)

        for i in range(self.pid_list.count()):
            item = self.pid_list.item(i)
            pid = item.data(Qt.ItemDataRole.UserRole)
            item.setSelected(pid in self.selected_pids)

        self.pid_list.blockSignals(False)

        self.selection_label.setText(f"Selected: {len(self.selected_pids)} PIDs")
        self._refresh_polling_buttons()
    
    def _start_polling(self):
        """Inicia polling de PIDs"""
        # Update selection based on the list
        self.selected_pids.clear()
        for item in self.pid_list.selectedItems():
            pid = item.data(Qt.ItemDataRole.UserRole)
            self.selected_pids.add(pid)
        
        if not self.selected_pids:
            return
        
        self.polling_active = True
        self.poll_timer.start(int(self.poll_interval * 1000))
        self.pid_list.setEnabled(False)
        self._refresh_polling_buttons()

        # Statistics
        self.request_count = 0
        self.response_count = 0
        
        self._log_message("✅ Polling started")
    
    def _stop_polling(self):
        """Para polling de PIDs"""
        self.polling_active = False
        self.poll_timer.stop()
        # Do not stop update_timer - keep it running to refresh connection status
        self.pid_list.setEnabled(True)
        self._refresh_polling_buttons()
        
        self._log_message("⏸ Polling stopped")
    
    def _single_shot(self):
        """Read selected PIDs once (no continuous polling)"""
        # Update selection based on the list
        self.selected_pids.clear()
        for item in self.pid_list.selectedItems():
            pid = item.data(Qt.ItemDataRole.UserRole)
            self.selected_pids.add(pid)
        
        if not self.selected_pids:
            return
        
        if not self.active_bus or not self.active_bus.bus:
            return
        
        self._log_message("Single shot - reading selected PIDs...")
        
        self._poll_ui_locked = True
        self._refresh_polling_buttons()
        self.read_dtc_btn.setEnabled(False)
        
        # Send all requests at once
        for pid in self.selected_pids:
            try:
                # Envia request (Service 01 = Current Data)
                request = can.Message(
                    arbitration_id=0x7DF,  # Broadcast
                    data=[0x02, 0x01, pid, 0x00, 0x00, 0x00, 0x00, 0x00],
                    is_extended_id=False
                )
                
                self.active_bus.send(request)
                self.request_count += 1
                
                # Add to raw table
                pid_info = OBD2_PIDS.get(pid, {})
                pid_name = pid_info.get('name', f'PID 0x{pid:02X}')
                self._add_raw_request(request, f"Request: {pid_name}")
                
            except Exception as e:
                self._log_message(f"Error reading PID 0x{pid:02X}: {e}")
        
        # Wait 1 second for responses (processed by the receive thread)
        QTimer.singleShot(1000, self._single_shot_complete)
    
    def _single_shot_complete(self):
        """Callback after single shot completes"""
        self._log_message(f"Single shot complete - requested {len(self.selected_pids)} PIDs")
        self._poll_ui_locked = False
        self.read_dtc_btn.setEnabled(True)
        self._refresh_polling_buttons()

    def _detect_vin(self):
        """Request VIN (Service 09 PID 02) and assemble ISO-TP multi-frame response."""
        if not self.active_bus or not self.active_bus.bus:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Cannot detect VIN: Not connected to CAN bus."
            )
            return

        if self.receiving_vin:
            return

        # Reset VIN state
        self.receiving_vin = True
        self.vin_response_received = False
        self.vin_buffer = bytearray()
        self.vin_expected_len = None
        self.vin_value = None
        if hasattr(self, 'vin_value_label'):
            self.vin_value_label.setText("(detecting...)")
        self._refresh_polling_buttons()

        try:
            # Service 09 (Vehicle information), PID 02 (VIN)
            request = can.Message(
                arbitration_id=0x7DF,  # Broadcast request
                data=[0x02, 0x09, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            self.active_bus.send(request)
            self.request_count += 1
            self._add_raw_request(request, "Request: VIN (Service 09 PID 02)")
            self._log_message("Requesting VIN (Service 09 PID 02)...")
        except Exception as e:
            self.receiving_vin = False
            if hasattr(self, 'vin_value_label'):
                self.vin_value_label.setText("-")
            self._log_message(f"Error requesting VIN: {e}")
            return

        # Timeout for VIN response
        QTimer.singleShot(1500, self._detect_vin_complete)

    def _detect_vin_complete(self):
        """Callback after VIN detection timeout."""
        # VIN is already logged when the ISO-TP payload is fully assembled in _process_vin_response().
        # This callback should only handle timeouts / UI cleanup.
        if not (self.vin_response_received and self.vin_value):
            self._log_message("VIN detection timed out (no complete response).")
            if not self.vin_value:
                if hasattr(self, 'vin_value_label'):
                    self.vin_value_label.setText("(not available)")
        self.receiving_vin = False
        self._refresh_polling_buttons()

    def _process_vin_response(self, msg: CANMessage):
        """Process ISO-TP VIN response frames (0x49 0x02 0x01 + 17 ASCII VIN bytes)."""
        if len(msg.data) < 2:
            return

        pci = msg.data[0]
        frame_type = pci & 0xF0

        # First Frame (FF): [0x10|len_hi, len_lo, payload0..5]
        if frame_type == 0x10 and len(msg.data) >= 8:
            total_len = ((pci & 0x0F) << 8) | msg.data[1]
            self.vin_expected_len = total_len
            self.vin_buffer = bytearray(msg.data[2:])  # 6 bytes payload

            # If this is indeed a VIN response, send Flow Control (FC) so ECU keeps sending.
            # Many ECUs expect FC to the physical tester->ECU ID (0x7E0).
            try:
                if len(self.vin_buffer) >= 2 and self.vin_buffer[0] == 0x49 and self.vin_buffer[1] == 0x02:
                    # Map response 0x7E8..0x7EF -> physical request 0x7E0..0x7E7
                    req_id = 0x7E0
                    if 0x7E8 <= msg.can_id <= 0x7EF:
                        req_id = msg.can_id - 0x8
                    fc = can.Message(
                        arbitration_id=req_id,
                        data=[0x30, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00],
                        is_extended_id=False
                    )
                    self.active_bus.send(fc)
                    self._add_raw_request(fc, "Flow Control (ISO-TP) for VIN")
            except Exception as e:
                self._log_message(f"VIN Flow Control send failed: {e}")

        # Consecutive Frame (CF): [0x2N, payload0..6]
        elif frame_type == 0x20 and self.vin_expected_len is not None:
            self.vin_buffer.extend(msg.data[1:])  # 7 bytes

        else:
            # Not ISO-TP or not part of VIN sequence; ignore.
            return

        # Check completion
        if self.vin_expected_len is not None and len(self.vin_buffer) >= self.vin_expected_len:
            payload = bytes(self.vin_buffer[:self.vin_expected_len])

            # Expected payload: 0x49 0x02 0x01 + 17 ASCII chars
            if len(payload) >= 3 and payload[0] == 0x49 and payload[1] == 0x02:
                vin_bytes = payload[3:3 + 17]
                try:
                    vin = bytes(vin_bytes).decode('ascii', errors='ignore').strip()
                except Exception:
                    vin = ""

                if vin:
                    self.vin_value = vin
                    if hasattr(self, 'vin_value_label'):
                        self.vin_value_label.setText(vin)
                    self.vin_response_received = True
                    self.response_count += 1
                    self._log_message(f"VIN detected: {vin}")
                else:
                    if hasattr(self, 'vin_value_label'):
                        self.vin_value_label.setText("(invalid response)")
            else:
                if hasattr(self, 'vin_value_label'):
                    self.vin_value_label.setText("(unexpected response)")
    
    def _process_dtc_response(self, msg: CANMessage):
        """Process Service 03 DTC responses (single-frame or ISO-TP multi-frame)."""
        if len(msg.data) < 2:
            return

        self.dtc_response_received = True
        data = msg.data

        # Single-frame response:
        #   [len, 0x43, count, dtc_hi, dtc_lo, ...]
        if len(data) >= 3 and data[1] == 0x43:
            count = int(data[2])
            self.dtc_expected_bytes = max(0, count * 2)

            # Some ECUs (and our Arduino simulator) may not fit all DTC bytes in a single frame.
            # Start/refresh the accumulation buffer with whatever arrived after the count byte.
            self.dtc_buffer = bytearray(data[3:])

            if self.dtc_expected_bytes > 0 and len(self.dtc_buffer) >= self.dtc_expected_bytes:
                self._ingest_dtc_pairs(bytes(self.dtc_buffer[:self.dtc_expected_bytes]))
                self.dtc_expected_bytes = None
                self.dtc_buffer = bytearray()
            return

        # ISO-TP multi-frame:
        #   FF: [0x10|len_hi, len_lo, payload0..5]
        #   CF: [0x2N, payload0..6]
        pci_type = data[0] & 0xF0

        if pci_type == 0x10 and len(data) >= 8:
            total_len = ((data[0] & 0x0F) << 8) | data[1]
            self.dtc_expected_len = total_len
            self.dtc_buffer = bytearray(data[2:])

            # Send Flow Control (some ECUs require it).
            try:
                if len(self.dtc_buffer) >= 1 and self.dtc_buffer[0] == 0x43:
                    # Map response 0x7E8..0x7EF -> physical request 0x7E0..0x7E7
                    req_id = 0x7E0
                    if 0x7E8 <= msg.can_id <= 0x7EF:
                        req_id = msg.can_id - 0x8
                    fc = can.Message(
                        arbitration_id=req_id,
                        data=[0x30, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00],
                        is_extended_id=False
                    )
                    self.active_bus.send(fc)
                    self._add_raw_request(fc, "Flow Control (ISO-TP) for DTCs")
            except Exception as e:
                self._log_message(f"DTC Flow Control send failed: {e}")

        elif pci_type == 0x20 and self.dtc_expected_len is not None:
            self.dtc_buffer.extend(data[1:])
        else:
            # Fallback continuation (non-ISO-TP): append bytes 1..7 (trim trailing zero padding)
            if self.dtc_expected_bytes is None or len(self.dtc_buffer) == 0:
                return

            cont = bytearray(data[1:])
            while cont and cont[-1] == 0x00:
                cont.pop()
            if cont:
                self.dtc_buffer.extend(cont)

            if len(self.dtc_buffer) >= self.dtc_expected_bytes:
                self._ingest_dtc_pairs(bytes(self.dtc_buffer[:self.dtc_expected_bytes]))
                self.dtc_expected_bytes = None
                self.dtc_buffer = bytearray()
            return

        if self.dtc_expected_len is not None and len(self.dtc_buffer) >= self.dtc_expected_len:
            payload = bytes(self.dtc_buffer[:self.dtc_expected_len])

            # Expected payload: [0x43, count, dtc_hi, dtc_lo, ...]
            if len(payload) >= 2 and payload[0] == 0x43:
                count = int(payload[1])
                dtc_bytes = payload[2:2 + (count * 2)]
                self._ingest_dtc_pairs(dtc_bytes)

            # Reset ISO-TP DTC state
            self.dtc_expected_len = None
            self.dtc_buffer = bytearray()
            self.dtc_expected_bytes = None

    def _ingest_dtc_pairs(self, dtc_bytes: bytes):
        """Decode and add DTC pairs to dtcs_found (deduped)."""
        if not dtc_bytes:
            return
        idx = 0
        while idx + 1 < len(dtc_bytes):
            dtc_high = dtc_bytes[idx]
            dtc_low = dtc_bytes[idx + 1]
            idx += 2

            if dtc_high == 0 and dtc_low == 0:
                continue

            dtc_code = self._decode_dtc(dtc_high, dtc_low)
            if dtc_code not in self.dtcs_found:
                self.dtcs_found.append(dtc_code)
                self._log_message(f"  • {dtc_code}")

    def _is_vag_dtc_protocol(self) -> bool:
        if not hasattr(self, "dtc_protocol_combo"):
            return False
        return self.dtc_protocol_combo.currentData() == "vag"

    def _selected_vag_module(self) -> Optional[VagModule]:
        if not hasattr(self, "vag_module_combo"):
            return None
        mod = self.vag_module_combo.currentData()
        return mod if isinstance(mod, VagModule) else None

    def _vag_populate_module_combo(self, modules: List[VagModule]) -> None:
        if not hasattr(self, "vag_module_combo"):
            return
        prev = self._selected_vag_module()
        prev_addr = prev.logical_addr if prev else None
        self.vag_module_combo.blockSignals(True)
        self.vag_module_combo.clear()
        if not modules:
            for mod in MODULES.values():
                label = f"0x{mod.logical_addr:02X}  {mod.name}  · TX 0x{mod.tx_id:03X}"
                self.vag_module_combo.addItem(label, mod)
        else:
            priority = {0x15: 0, 0x14: 1, 0x13: 2, 0x10: 3, 0x19: 4, 0x0E: 5}
            for mod in sorted(
                modules,
                key=lambda m: (priority.get(m.logical_addr, 100), m.logical_addr),
            ):
                label = f"0x{mod.logical_addr:02X}  {mod.name}  · TX 0x{mod.tx_id:03X}"
                self.vag_module_combo.addItem(label, mod)
        pick = prev_addr if prev_addr is not None else 0x14
        for i in range(self.vag_module_combo.count()):
            m = self.vag_module_combo.itemData(i)
            if isinstance(m, VagModule) and m.logical_addr == pick:
                self.vag_module_combo.setCurrentIndex(i)
                break
        self.vag_module_combo.blockSignals(False)

    def _vag_set_scan_ui_busy(self, busy: bool) -> None:
        if hasattr(self, "vag_detect_ecus_btn"):
            self.vag_detect_ecus_btn.setEnabled(not busy)
        self._set_dtc_buttons_enabled(not busy)
        if hasattr(self, "vag_module_combo"):
            self.vag_module_combo.setEnabled(not busy)

    def _vag_detect_ecus(self) -> None:
        if not self.active_bus or not self.active_bus.bus:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Conecte ao CAN antes de detectar ECUs VAG.",
            )
            return
        if self.receiving_vag_uds or self.receiving_vag_scan:
            return
        if self.polling_active:
            self._stop_polling()
        self.receiving_vag_scan = True
        self.vag_scan_found = []
        self.vag_scan_addrs = list(range(0x01, 0x80))
        self._vag_set_scan_ui_busy(True)
        self._log_message(t("obd2_vag_scanning"))
        self._vag_scan_probe_next()

    def _vag_scan_probe_next(self) -> None:
        if not self.receiving_vag_scan:
            return
        if not self.vag_scan_addrs:
            self._vag_scan_finish()
            return
        addr = self.vag_scan_addrs.pop(0)
        self.vag_scan_current_addr = addr
        tx_id = VAG_TX_BASE + addr
        self.vag_scan_expect_rx = tx_id + VAG_RX_OFFSET
        if self.active_bus and self.active_bus.bus:
            self.active_bus.send(
                can.Message(
                    arbitration_id=tx_id,
                    data=build_single_frame(bytes([0x3E, 0x00])),
                    is_extended_id=False,
                )
            )
        self.vag_scan_timer.start(80)

    def _vag_scan_on_response(self, msg: CANMessage) -> None:
        if not self.receiving_vag_scan or self.vag_scan_current_addr is None:
            return
        payload = parse_isotp_single(bytes(msg.data or b""))
        if payload is None:
            return
        self.vag_scan_timer.stop()
        mod = module_at_logical_addr(self.vag_scan_current_addr)
        if not any(m.logical_addr == mod.logical_addr for m in self.vag_scan_found):
            self.vag_scan_found.append(mod)
        self._vag_scan_probe_next()

    def _vag_scan_on_probe_timeout(self) -> None:
        if not self.receiving_vag_scan:
            return
        self._vag_scan_probe_next()

    def _vag_scan_finish(self) -> None:
        self.receiving_vag_scan = False
        self.vag_scan_expect_rx = None
        self.vag_scan_current_addr = None
        self.vag_scan_timer.stop()
        self._vag_populate_module_combo(self.vag_scan_found)
        self._vag_set_scan_ui_busy(False)
        self._refresh_polling_buttons()
        n = len(self.vag_scan_found)
        self._log_message(t("obd2_vag_scan_done").format(n=n))
        if n == 0:
            QMessageBox.information(
                self,
                t("obd2_vag_detect_ecus"),
                "Nenhum módulo respondeu (0x01–0x7F).\n"
                "Verifique ignição, 500 kbps e conexão ao OBD.",
            )

    def _on_dtc_protocol_changed(self, _index: int = 0) -> None:
        is_vag = self._is_vag_dtc_protocol()
        mod = self._selected_vag_module() if is_vag else None

        for attr in ("vag_module_label", "vag_module_combo", "vag_detect_ecus_btn"):
            w = getattr(self, attr, None)
            if w is not None:
                w.setVisible(is_vag)
        if hasattr(self, "vag_detect_ecus_btn"):
            self.vag_detect_ecus_btn.setEnabled(is_vag and not self.receiving_vag_scan)
        if hasattr(self, "vag_target_label"):
            if is_vag and mod:
                self.vag_target_label.setText(
                    f"TX 0x{mod.tx_id:03X} → RX 0x{mod.rx_id:03X}  ·  UDS 19 02 / 14 FF FF FF"
                )
                self.vag_target_label.setVisible(True)
            elif is_vag:
                self.vag_target_label.setText(t("obd2_vag_scan_prompt"))
                self.vag_target_label.setVisible(True)
            else:
                self.vag_target_label.clear()
                self.vag_target_label.setVisible(False)

        if hasattr(self, "protocol_info_label"):
            if is_vag and mod:
                self.protocol_info_label.setText(
                    f"VAG · 0x{mod.tx_id:03X}→0x{mod.rx_id:03X}"
                )
            else:
                self.protocol_info_label.setText("0x7DF → 0x7E8–0x7EF")

        if hasattr(self, "detect_vin_btn"):
            # VIN is OBD-II Service 09; keep available, but clearer in OBD mode
            self.detect_vin_btn.setVisible(True)

        if is_vag:
            self.read_dtc_btn.setToolTip(
                "Ler DTCs do módulo VAG selecionado (UDS 19 02)"
            )
            self.clear_dtc_btn.setToolTip(
                "Apagar DTCs só neste módulo (UDS 14 FF FF FF)"
            )
        else:
            self.read_dtc_btn.setToolTip(
                "Ler DTCs via broadcast OBD-II (Service 03 → 0x7DF)"
            )
            self.clear_dtc_btn.setToolTip(
                "Apagar DTCs via broadcast OBD-II (Service 04 → 0x7DF)"
            )

    def _vag_reset_session_state(self) -> None:
        self.vag_step_timer.stop()
        self.receiving_vag_uds = False
        self.vag_operation = None
        self.vag_clear_phase = None
        self.vag_clear_attempts = 0
        self.vag_masks_queue = []
        self.vag_rx_queue = []
        self.vag_isotp.reset()

    def _vag_is_reading_dtc_masks(self) -> bool:
        if self.vag_operation == "read":
            return True
        return (
            self.vag_operation == "clear"
            and self.vag_clear_phase == "verify"
        )

    def _vag_send_flow_control(self) -> None:
        if not self.active_bus or not self.vag_module:
            return
        # ISO-TP FC PCI — NOT a UDS Single Frame (see VAG-LeituraDTCPainel.json: 30000055…)
        fc = can.Message(
            arbitration_id=self.vag_module.tx_id,
            data=build_flow_control_frame(block_size=0, st_min=0),
            is_extended_id=False,
        )
        self.active_bus.send(fc)
        self._add_raw_request(fc, "Flow Control (ISO-TP) VAG")

    def _vag_send_uds(self, uds: bytes, label: str) -> None:
        if not self.active_bus or not self.vag_module:
            return
        request = can.Message(
            arbitration_id=self.vag_module.tx_id,
            data=build_single_frame(uds),
            is_extended_id=False,
        )
        self.active_bus.send(request)
        self._add_raw_request(request, label)

    def _vag_arm_step_timeout(self, ms: int = 5000) -> None:
        self.vag_step_timer.start(ms)

    def _vag_on_step_timeout(self) -> None:
        if not self.receiving_vag_uds:
            return
        if (
            self._vag_is_reading_dtc_masks()
            and self.vag_isotp.is_multiframe_pending
        ):
            self.vag_isotp_stalls += 1
            if self.vag_isotp_stalls < 8:
                self._log_message("VAG: aguardando frame ISO-TP (CF)…")
                self._vag_arm_step_timeout(800)
                return
            self._log_message("VAG: ISO-TP incompleto — repetindo máscara")
            self.vag_isotp.reset()
            self.vag_isotp_stalls = 0
            self.vag_rx_queue.clear()
            if (
                self.vag_current_mask is not None
                and self.vag_mask_retries_left > 0
            ):
                self.vag_mask_retries_left = 0
                self._vag_resend_current_read_mask()
                return
            self._log_message("VAG: ISO-TP incompleto — próxima máscara")
        if self._vag_is_reading_dtc_masks() and self.vag_masks_queue:
            self._log_message("VAG: timeout — próxima máscara DTC")
            self._vag_send_next_read_mask()
            return
        if self.vag_operation == "read":
            self._vag_read_complete()
        elif self.vag_operation == "clear":
            if self.vag_clear_phase == "verify":
                self._vag_on_clear_verify_done()
            else:
                self._vag_clear_complete(
                    success=False,
                    message="Sem resposta do módulo (timeout).",
                )

    def _vag_store_dtc_records(self, records: List[DtcRecord]) -> None:
        for rec in records:
            if rec.raw in self.vag_dtc_by_raw:
                continue
            self.vag_dtc_by_raw[rec.raw] = rec
            line = format_dtc_record_line(rec)
            self.vag_dtcs_found.append(line)
            self._log_message(f"  • {line}")

    def _process_vag_uds_response(self, msg: CANMessage) -> None:
        self.vag_rx_queue.append(msg)
        self._vag_drain_isotp_queue()

    def _vag_drain_isotp_queue(self) -> None:
        if not self.vag_module:
            return
        rx = self.vag_module.rx_id
        while True:
            idx = next(
                (i for i, m in enumerate(self.vag_rx_queue) if m.can_id == rx),
                None,
            )
            if idx is None:
                break
            queued = self.vag_rx_queue.pop(idx)
            data = bytes(queued.data or b"")
            if self.vag_isotp.needs_flow_control(data):
                self._vag_send_flow_control()
            payload = self.vag_isotp.feed(data)
            if payload is None:
                if self._vag_is_reading_dtc_masks() and self.vag_isotp.is_multiframe_pending:
                    self._vag_arm_step_timeout()
                continue
            self._vag_handle_uds_payload(payload)
            if is_response_pending(payload):
                continue
            break

    def _vag_handle_uds_payload(self, payload: bytes) -> None:
        if is_response_pending(payload):
            self._log_message("VAG: ECU ocupada (7F … 78), aguardando…")
            self.vag_isotp.reset()
            self.vag_rx_queue.clear()
            self._vag_arm_step_timeout()
            return

        self.vag_response_received = True
        self.vag_step_timer.stop()
        self.vag_isotp_stalls = 0

        if self._vag_is_reading_dtc_masks():
            if payload[0] == 0x59 and len(payload) >= 2 and payload[1] == 0x02:
                dtc_bytes = len(payload) - 3
                if dtc_bytes > 0 and dtc_bytes % 4 != 0:
                    self._log_message(
                        f"VAG: resposta 59 02 truncada ({len(payload)} B) — "
                        f"hex={payload.hex()}"
                    )
                    if (
                        self.vag_current_mask is not None
                        and self.vag_mask_retries_left > 0
                    ):
                        self.vag_mask_retries_left = 0
                        self.vag_masks_queue.insert(0, self.vag_current_mask)
                _avail, records = parse_read_dtc_response(payload)
                self._vag_store_dtc_records(records)
                self.vag_rx_queue.clear()
                self._vag_send_next_read_mask()
            elif payload[0] == 0x7F:
                self._log_message(f"VAG read: {describe_negative(payload)}")
                self.vag_rx_queue.clear()
                self._vag_send_next_read_mask()
            else:
                self._log_message(f"VAG read: resposta inesperada {payload.hex()}")
                self.vag_rx_queue.clear()
                self._vag_send_next_read_mask()
        elif self.vag_operation == "clear":
            if payload[0] == 0x54:
                self.vag_clear_attempts += 1
                self._log_message(
                    f"VAG: resposta 54 ({self.vag_clear_attempts}/"
                    f"{self.vag_clear_max_attempts}) — verificando DTCs…"
                )
                self._vag_start_clear_verify_read()
            elif payload[0] == 0x7F:
                self._vag_clear_complete(
                    success=False,
                    message=describe_negative(payload),
                )
            else:
                self._vag_clear_complete(
                    success=False,
                    message=f"Resposta inesperada: {payload.hex()}",
                )

    def _vag_start_clear_verify_read(self) -> None:
        self.vag_clear_phase = "verify"
        self.vag_dtc_by_raw = {}
        self.vag_dtcs_found = []
        self.vag_isotp.reset()
        self.vag_isotp_stalls = 0
        self.vag_rx_queue.clear()
        self.vag_masks_queue = [mask for mask, _label in DTC_STATUS_MASKS_GUI]
        self._vag_send_next_read_mask()

    def _vag_on_clear_verify_done(self) -> None:
        remaining = len(self.vag_dtc_by_raw)
        if remaining == 0:
            if self.vag_clear_attempts > 1:
                msg = (
                    f"DTCs apagadas ({self.vag_clear_attempts}× 14 FF FF FF, "
                    "verificação OK)."
                )
            else:
                msg = "DTCs apagadas (resposta 54, verificação OK)."
            self._vag_clear_complete(success=True, message=msg)
            return

        if self.vag_clear_attempts < self.vag_clear_max_attempts:
            self._log_message(
                f"VAG: ainda {remaining} DTC(s) — repetindo 14 FF FF FF…"
            )
            self.vag_clear_phase = "wait_54"
            self.vag_dtc_by_raw = {}
            self.vag_dtcs_found = []
            self.vag_isotp.reset()
            self.vag_rx_queue.clear()
            self._vag_send_uds(
                bytes([0x14, 0xFF, 0xFF, 0xFF]),
                "Request: VAG Clear DTCs retry (14 FF FF FF)",
            )
            self._vag_arm_step_timeout(10000)
            return

        lines = [
            format_dtc_record_line(rec)
            for rec in sorted(
                self.vag_dtc_by_raw.values(),
                key=lambda r: r.raw,
            )
        ]
        preview = "\n".join(f"• {line}" for line in lines[:8])
        self._vag_clear_complete(
            success=False,
            message=(
                f"Ainda {remaining} DTC(s) após {self.vag_clear_max_attempts} "
                f"tentativas de apagar:\n\n{preview}"
            ),
        )

    def _vag_send_next_read_mask(self) -> None:
        if not self.vag_masks_queue:
            if self.vag_operation == "clear" and self.vag_clear_phase == "verify":
                self._vag_on_clear_verify_done()
            else:
                self._vag_read_complete()
            return
        mask = self.vag_masks_queue.pop(0)
        self.vag_current_mask = mask
        self.vag_mask_retries_left = 1
        self.vag_isotp.reset()
        self.vag_isotp_stalls = 0
        self.vag_rx_queue.clear()
        self._vag_send_uds(
            bytes([0x19, 0x02, mask]),
            f"Request: VAG Read DTC (19 02 {mask:02X})",
        )
        self._vag_arm_step_timeout()

    def _vag_resend_current_read_mask(self) -> None:
        if self.vag_current_mask is None:
            self._vag_send_next_read_mask()
            return
        self.vag_isotp.reset()
        self.vag_isotp_stalls = 0
        self.vag_rx_queue.clear()
        mask = self.vag_current_mask
        self._vag_send_uds(
            bytes([0x19, 0x02, mask]),
            f"Request: VAG Read DTC retry (19 02 {mask:02X})",
        )
        self._vag_arm_step_timeout()

    def _vag_begin_session(self, operation: str) -> bool:
        if not self.active_bus or not self.active_bus.bus:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Cannot access ECU: not connected to CAN bus.",
            )
            return False
        mod = self._selected_vag_module()
        if mod is None:
            QMessageBox.warning(
                self,
                "VAG UDS",
                f"{t('obd2_vag_scan_prompt')}",
            )
            return False

        self._resume_polling_after_dtcs = bool(getattr(self, "polling_active", False))
        if self._resume_polling_after_dtcs:
            self._stop_polling()

        self.vag_module = mod
        self.vag_operation = operation
        self.vag_dtcs_found = []
        self.vag_dtc_by_raw = {}
        self.vag_isotp_stalls = 0
        self.vag_rx_queue = []
        self.vag_response_received = False
        self.vag_isotp.reset()
        self.receiving_vag_uds = True
        self._set_dtc_buttons_enabled(False)
        self._refresh_polling_buttons()
        return True

    def _set_dtc_buttons_enabled(self, enabled: bool) -> None:
        self.read_dtc_btn.setEnabled(enabled)
        if hasattr(self, "clear_dtc_btn"):
            self.clear_dtc_btn.setEnabled(enabled)
        if hasattr(self, "detect_vin_btn"):
            self.detect_vin_btn.setEnabled(enabled)

    def _vag_finish_session_reenable_buttons(self) -> None:
        self._vag_reset_session_state()
        self._set_dtc_buttons_enabled(True)
        self._refresh_polling_buttons()
        if getattr(self, "_resume_polling_after_dtcs", False):
            self._resume_polling_after_dtcs = False
            try:
                self._start_polling()
            except Exception:
                pass

    def _vag_read_dtcs(self) -> None:
        if not self._vag_begin_session("read"):
            return
        mod = self.vag_module
        assert mod is not None
        self._log_message(
            f"VAG: lendo DTCs — {mod.name} (TX 0x{mod.tx_id:03X}, RX 0x{mod.rx_id:03X})"
        )
        self.vag_isotp_stalls = 0
        self.vag_masks_queue = [mask for mask, _label in DTC_STATUS_MASKS_GUI]
        self._vag_send_next_read_mask()

    def _vag_read_complete(self) -> None:
        mod = self.vag_module
        title = mod.name if mod else "VAG"
        if not self.vag_response_received:
            QMessageBox.warning(
                self,
                "No Response",
                f"No response from {title}.\n\n"
                "Check ignition, gateway routing, and 500 kbps bitrate.",
            )
        elif self.vag_dtc_by_raw:
            lines = [
                format_dtc_record_line(rec)
                for rec in sorted(
                    self.vag_dtc_by_raw.values(),
                    key=lambda r: r.raw,
                )
            ]
            QMessageBox.warning(
                self,
                "DTCs Found",
                f"{title} — {len(lines)} DTC(s):\n\n"
                + "\n".join(f"• {d}" for d in lines),
            )
        else:
            QMessageBox.information(
                self,
                "No DTCs",
                f"{title}: no DTCs reported (UDS 19 02).",
            )
        self._vag_finish_session_reenable_buttons()

    def _vag_clear_dtcs(self) -> None:
        mod = self._selected_vag_module()
        if mod is None:
            return
        confirm = QMessageBox.question(
            self,
            "Clear DTCs",
            f"Clear all DTCs on {mod.name}?\n\n"
            f"UDS 14 FF FF FF → TX 0x{mod.tx_id:03X}\n"
            "This only affects this control unit, not the whole vehicle.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if not self._vag_begin_session("clear"):
            return
        self.vag_clear_phase = "wait_54"
        self.vag_clear_attempts = 0
        self.vag_clear_max_attempts = 3
        self._log_message(f"VAG: apagando DTCs — {mod.name}")
        self._vag_send_uds(
            bytes([0x14, 0xFF, 0xFF, 0xFF]),
            "Request: VAG Clear DTCs (14 FF FF FF)",
        )
        self._vag_arm_step_timeout(10000)

    def _vag_clear_complete(self, success: bool, message: str) -> None:
        mod = self.vag_module
        title = mod.name if mod else "VAG"
        if success:
            QMessageBox.information(self, "Clear DTCs", f"{title}: {message}")
        else:
            QMessageBox.warning(self, "Clear DTCs", f"{title}: {message}")
        self._vag_finish_session_reenable_buttons()
    
    def _read_dtcs(self):
        """Read Diagnostic Trouble Codes (Service 03)"""
        if self._is_vag_dtc_protocol():
            self._vag_read_dtcs()
            return
        if not self.active_bus or not self.active_bus.bus:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Cannot read DTCs: Not connected to CAN bus."
            )
            return

        # Pause polling to avoid mixing PID responses with DTC collection.
        self._resume_polling_after_dtcs = bool(getattr(self, "polling_active", False))
        if self._resume_polling_after_dtcs:
            self._stop_polling()

        self._log_message("Reading DTCs (Service 03)...")
        
        # Clear DTC buffer
        self.dtcs_found = []
        self.dtc_buffer.clear()
        self.dtc_expected_len = None
        self.dtc_expected_bytes = None
        self.dtc_response_received = False
        self.receiving_dtcs = True
        self._set_dtc_buttons_enabled(False)
        self._refresh_polling_buttons()
        
        try:
            # Envia request (Service 03 = Show stored DTCs)
            request = can.Message(
                arbitration_id=0x7DF,  # Broadcast
                data=[0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            
            self.active_bus.send(request)
            self._add_raw_request(request, "Request: Read DTCs (Service 03)")
            
            # Wait 1 second for responses (processed by on_can_message)
            QTimer.singleShot(1000, self._read_dtcs_complete)
        
        except Exception as e:
            self._log_message(f"Error reading DTCs: {e}")
            self.receiving_dtcs = False
            self._set_dtc_buttons_enabled(True)
            self._refresh_polling_buttons()
    
    def _read_dtcs_complete(self):
        """Callback after DTC read completes"""
        self.receiving_dtcs = False
        self.dtc_expected_len = None
        self.dtc_expected_bytes = None
        
        # Check if any response was received
        if not self.dtc_response_received:
            self._log_message("⚠️ No response from ECU (timeout)")
            QMessageBox.warning(
                self,
                "No Response",
                "No response received from ECU.\n\n"
                "Possible causes:\n"
                "• ECU is not connected or powered off\n"
                "• Wrong baudrate (OBD-II typically uses 500 kbps)\n"
                "• ECU does not support Service 03\n"
                "• Communication error on CAN bus"
            )
        # Show result in popup
        elif self.dtcs_found:
            self._log_message(f"Found {len(self.dtcs_found)} DTC(s)")
            QMessageBox.warning(
                self,
                "DTCs Found",
                f"Found {len(self.dtcs_found)} Diagnostic Trouble Code(s):\n\n" +
                "\n".join(f"• {dtc}" for dtc in self.dtcs_found) +
                "\n\nCheck the Statistics tab for details."
            )
        else:
            # Received a response but no DTCs
            self._log_message("No DTCs found - vehicle is healthy!")
            QMessageBox.information(
                self,
                "No DTCs",
                "No Diagnostic Trouble Codes found.\n\nVehicle is healthy! ✅"
            )
        
        self._set_dtc_buttons_enabled(True)
        self._refresh_polling_buttons()

        # Resume polling if it was active before reading DTCs.
        if getattr(self, "_resume_polling_after_dtcs", False):
            self._resume_polling_after_dtcs = False
            try:
                self._start_polling()
            except Exception:
                pass

    def _clear_dtcs(self):
        """Clear Diagnostic Trouble Codes (Service 04)"""
        if self._is_vag_dtc_protocol():
            self._vag_clear_dtcs()
            return
        if not self.active_bus or not self.active_bus.bus:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Cannot clear DTCs: Not connected to CAN bus."
            )
            return

        # Clearing DTCs resets emission readiness on many ECUs. Ask for confirmation.
        confirm = QMessageBox.question(
            self,
            "Clear DTCs",
            "This will request the ECU to clear stored Diagnostic Trouble Codes (Service 04).\n"
            "It may also reset readiness monitors.\n\n"
            "Do you want to continue?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Pause polling during clear to keep UI consistent and avoid flooding.
        self._resume_polling_after_dtcs = bool(getattr(self, "polling_active", False))
        if self._resume_polling_after_dtcs:
            self._stop_polling()

        self._log_message("Clearing DTCs (Service 04)...")
        self._poll_ui_locked = True
        self._set_dtc_buttons_enabled(False)
        self._refresh_polling_buttons()

        try:
            request = can.Message(
                arbitration_id=0x7DF,  # Broadcast
                data=[0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )

            self.active_bus.send(request)
            self._add_raw_request(request, "Request: Clear DTCs (Service 04)")

            # Give the ECU a moment; responses vary by vehicle (some may not answer).
            QTimer.singleShot(800, self._clear_dtcs_complete)
        except Exception as e:
            self._log_message(f"Error clearing DTCs: {e}")
            self._poll_ui_locked = False
            self._set_dtc_buttons_enabled(True)
            self._refresh_polling_buttons()

    def _clear_dtcs_complete(self):
        """Re-enable buttons after clear request window"""
        self._log_message("Clear DTCs request sent. If supported, DTCs should be cleared.")
        self._poll_ui_locked = False
        self._set_dtc_buttons_enabled(True)
        self._refresh_polling_buttons()

        # Resume polling if it was active before clearing DTCs.
        if getattr(self, "_resume_polling_after_dtcs", False):
            self._resume_polling_after_dtcs = False
            try:
                self._start_polling()
            except Exception:
                pass
    
    def _decode_dtc(self, high_byte: int, low_byte: int) -> str:
        """
        Decodifica DTC de 2 bytes para formato padrão
        
        Formato: CXXXX
        C = Character (P, C, B, U)
        XXXX = 4 dígitos hex
        """
        # Primeiro caractere (2 bits mais significativos)
        first_char_code = (high_byte >> 6) & 0x03
        first_chars = ['P', 'C', 'B', 'U']
        first_char = first_chars[first_char_code]
        
        # Remaining code (14 bits)
        code_value = ((high_byte & 0x3F) << 8) | low_byte
        
        return f"{first_char}{code_value:04X}"
    
    def _update_poll_interval(self, value_ms: int):
        """Atualiza intervalo de polling"""
        self.poll_interval = value_ms / 1000.0
        if self.polling_active:
            self.poll_timer.setInterval(value_ms)
    
    def _poll_pids(self):
        """Faz polling dos PIDs selecionados"""
        if not self.active_bus or not self.active_bus.bus:
            self._stop_polling()
            return
        
        for pid in self.selected_pids:
            try:
                # Envia request (Service 01 = Current Data)
                request = can.Message(
                    arbitration_id=0x7DF,  # Broadcast
                    data=[0x02, 0x01, pid, 0x00, 0x00, 0x00, 0x00, 0x00],
                    is_extended_id=False
                )
                
                self.active_bus.send(request)
                self.request_count += 1
                
                # Add to raw table
                pid_info = OBD2_PIDS.get(pid, {})
                pid_name = pid_info.get('name', f'PID 0x{pid:02X}')
                self._add_raw_request(request, f"Poll: {pid_name}")
                
                # Responses will be processed automatically by on_can_message()
                
            except Exception as e:
                self._log_message(f"Error polling PID 0x{pid:02X}: {e}")
    
    def _process_response(self, msg: CANMessage, pid: int):
        """Processa resposta OBD-II"""
        ecu_id = msg.can_id
        data = msg.data[3:]  # Pula length, service, pid
        
        # Decodifica valor
        value_str = self._decode_pid_value(pid, data)
        
        # Armazena
        self.pid_values[pid] = {
            'value': value_str,
            'timestamp': time.time(),
            'ecu_id': ecu_id,
            'raw_data': msg.data
        }
    
    def _decode_pid_value(self, pid: int, data: bytes) -> str:
        """Decodifica valor do PID (simplificado)"""
        pid_info = OBD2_PIDS.get(pid)
        if not pid_info:
            return f"Unknown PID"
        
        pid_type = pid_info.get('type', 'direct')
        
        try:
            if pid_type == 'direct':
                return f"{data[0]}"
            elif pid_type == 'percent':
                return f"{data[0] * 100 / 255:.1f}"
            elif pid_type == 'temp_offset':
                return f"{data[0] - 40}"
            elif pid_type == 'rpm':
                return f"{((data[0] << 8) | data[1]) / 4:.0f}"
            elif pid_type == 'uint16':
                return f"{(data[0] << 8) | data[1]}"
            elif pid_type == 'voltage':
                return f"{((data[0] << 8) | data[1]) / 1000:.2f}"
            elif pid_type == 'maf':
                return f"{((data[0] << 8) | data[1]) / 100:.2f}"
            else:
                return f"{data[0]}"
        except:
            return "Error"
    
    def _update_display(self):
        """Atualiza display de valores"""
        # Update values table (only if there is data or active polling)
        if self.pid_values and (self.polling_active or len(self.pid_values) > 0):
            self.values_table.setRowCount(len(self.pid_values))
            
            for row, (pid, data) in enumerate(sorted(self.pid_values.items())):
                pid_info = OBD2_PIDS.get(pid, {})
                
                # PID
                self.values_table.setItem(row, 0, QTableWidgetItem(f"0x{pid:02X}"))
                
                # Nome
                self.values_table.setItem(row, 1, QTableWidgetItem(pid_info.get('name', 'Unknown')))
                
                # Valor
                value_item = QTableWidgetItem(data['value'])
                
                # Do not colorize - keeps readability
                age = time.time() - data['timestamp']
                
                self.values_table.setItem(row, 2, value_item)
                
                # Unidade
                self.values_table.setItem(row, 3, QTableWidgetItem(pid_info.get('unit', '')))
                
                # ECU
                self.values_table.setItem(row, 4, QTableWidgetItem(f"0x{data['ecu_id']:03X}"))
                
                # Timestamp (updates only when polling is active)
                if self.polling_active:
                    self.values_table.setItem(row, 5, QTableWidgetItem(f"{age:.1f}s ago"))
                else:
                    # If polling is inactive, show a fixed timestamp
                    timestamp_str = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')
                    self.values_table.setItem(row, 5, QTableWidgetItem(timestamp_str))
        
        # Update statistics
        if self.request_count > 0:
            success_rate = (self.response_count / self.request_count) * 100
        else:
            success_rate = 0
        
        self.stats_label.setText(
            f"Req {self.request_count} · Rsp {self.response_count} · {success_rate:.0f}%"
        )
        
        # Update connection status (only if single-channel label exists)
        if hasattr(self, 'channel_label') and self.channel_label and self.active_bus:
            bus_name = self.active_bus.config.name if hasattr(self.active_bus, 'config') else "CAN"
            self._update_channel_status(bus_name, self.active_bus.connected)

        # Keep polling buttons consistent with bus / selection / busy state
        self._refresh_polling_buttons()
    
    def _add_raw_message(self, msg: CANMessage, decoded: str):
        """Add raw message to table"""
        # Limit number of messages
        if self.raw_table.rowCount() >= self.max_raw_messages:
            self.raw_table.removeRow(0)
        
        row = self.raw_table.rowCount()
        self.raw_table.insertRow(row)
        
        # Timestamp
        self.raw_table.setItem(row, 0, QTableWidgetItem(time.strftime("%H:%M:%S")))
        
        # ID
        self.raw_table.setItem(row, 1, QTableWidgetItem(f"0x{msg.can_id:03X}"))
        
        # Type
        msg_type = "Request" if msg.can_id == 0x7DF else "Response"
        self.raw_table.setItem(row, 2, QTableWidgetItem(msg_type))
        
        # Data
        data_hex = ' '.join(f"{b:02X}" for b in msg.data)
        self.raw_table.setItem(row, 3, QTableWidgetItem(data_hex))
        
        # Decoded
        self.raw_table.setItem(row, 4, QTableWidgetItem(decoded))
        
        # Auto-scroll
        self.raw_table.scrollToBottom()
    
    def _add_raw_request(self, request: can.Message, description: str):
        """Add sent request to raw table"""
        # Limit number of messages
        if self.raw_table.rowCount() >= self.max_raw_messages:
            self.raw_table.removeRow(0)
        
        row = self.raw_table.rowCount()
        self.raw_table.insertRow(row)
        
        # Timestamp
        self.raw_table.setItem(row, 0, QTableWidgetItem(time.strftime("%H:%M:%S")))
        
        # ID
        self.raw_table.setItem(row, 1, QTableWidgetItem(f"0x{request.arbitration_id:03X}"))
        
        # Type
        item_type = QTableWidgetItem("Request")
        item_type.setForeground(QColor(0, 0, 255))  # Azul para requests
        self.raw_table.setItem(row, 2, item_type)
        
        # Data
        data_hex = ' '.join(f"{b:02X}" for b in request.data)
        self.raw_table.setItem(row, 3, QTableWidgetItem(data_hex))
        
        # Decoded
        self.raw_table.setItem(row, 4, QTableWidgetItem(description))
        
        # Auto-scroll
        self.raw_table.scrollToBottom()
    
    def _log_message(self, message: str):
        """Add message to statistics log"""
        current = self.stats_text.toPlainText()
        timestamp = time.strftime("%H:%M:%S")
        new_line = f"[{timestamp}] {message}\n"
        self.stats_text.setPlainText(current + new_line)
        
        # Auto-scroll
        cursor = self.stats_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.stats_text.setTextCursor(cursor)
    
    def _update_channel_status(self, bus_name: str, connected: bool):
        """Update channel status label with colored status"""
        if connected:
            status_html = "<span style='color: #1a7f1a; font-weight: bold;'>OK</span>"
        else:
            status_html = "<span style='color: #0066cc;'>Sim</span>"
        self.channel_label.setText(f"<b>Ch:</b> {bus_name} {status_html}")
    
    def _change_active_bus(self, index: int):
        """Change active bus"""
        if self.can_bus_manager and index >= 0:
            bus_names = list(self.can_bus_manager.buses.keys())
            if index < len(bus_names):
                bus_name = bus_names[index]
                self.active_bus = self.can_bus_manager.buses[bus_name]
                self._log_message(f"🔄 Switched to {bus_name}")
    
    def set_can_bus_manager(self, can_bus_manager):
        """Define CAN bus manager"""
        self.can_bus_manager = can_bus_manager
        if can_bus_manager and can_bus_manager.buses:
            self.active_bus = list(can_bus_manager.buses.values())[0]
        self._refresh_polling_buttons()
    
    def _clear_live_values(self):
        """Limpa todos os valores da tabela Live Values"""
        self.pid_values.clear()
        self.values_table.setRowCount(0)
        self.request_count = 0
        self.response_count = 0
        self._log_message("Live values cleared")
    
    def _save_results(self):
        """Salva resultados em arquivo CSV"""
        if not self.pid_values:
            QMessageBox.information(
                self,
                "No Data",
                "No data to save. Please read some PIDs first."
            )
            return
        
        # Default name with timestamp
        default_name = f"obd2_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save OBD-II Results",
            dialog_path("obd2", default_name),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filename:
            return  # Usuário cancelou
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    'PID',
                    'Name',
                    'Value',
                    'Unit',
                    'ECU ID',
                    'Timestamp',
                    'Age (seconds)'
                ])
                
                # Data
                current_time = time.time()
                for pid in sorted(self.pid_values.keys()):
                    data = self.pid_values[pid]
                    pid_info = OBD2_PIDS.get(pid, {})
                    
                    age = current_time - data['timestamp']
                    
                    writer.writerow([
                        f"0x{pid:02X}",
                        pid_info.get('name', 'Unknown'),
                        data['value'],
                        pid_info.get('unit', ''),
                        f"0x{data['ecu_id']:03X}",
                        datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                        f"{age:.1f}"
                    ])
                
                # Add statistics at the end
                writer.writerow([])
                writer.writerow(['Statistics'])
                writer.writerow(['Total Requests', self.request_count])
                writer.writerow(['Total Responses', self.response_count])
                
                if self.request_count > 0:
                    success_rate = (self.response_count / self.request_count) * 100
                    writer.writerow(['Success Rate', f"{success_rate:.1f}%"])
            
            self._log_message(f"💾 Results saved to: {filename}")
            
            QMessageBox.information(
                self,
                "Saved",
                f"Results saved successfully!\n\n{filename}\n\n"
                f"PIDs: {len(self.pid_values)}\n"
                f"Requests: {self.request_count}\n"
                f"Responses: {self.response_count}"
            )
        
        except Exception as e:
            self._log_message(f"❌ Error saving results: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save results:\n\n{e}"
            )
    
    def closeEvent(self, event):
        """Cleanup ao fechar"""
        if self.polling_active:
            self._stop_polling()
        
        self.poll_timer.stop()
        self.update_timer.stop()
        
        super().closeEvent(event)
