"""
OBD-II Dialog - Interface for OBD-II monitoring
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QCheckBox, QSpinBox,
    QHeaderView, QTabWidget, QWidget, QListWidget, QListWidgetItem,
    QSplitter, QTextEdit, QComboBox, QMessageBox, QFileDialog
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


class OBD2Dialog(QDialog):
    """Dialog for OBD-II monitoring"""
    
    # Signal to process CAN messages in a thread-safe way
    message_received = pyqtSignal(str, object)
    
    def __init__(self, parent=None, can_bus_manager=None):
        super().__init__(parent)
        self.setWindowTitle(t('obd2_monitor_title'))
        self.resize(1200, 700)  # Mais compacto
        
        self.can_bus_manager = can_bus_manager
        self.selected_pids: Set[int] = set()
        self.pid_values: Dict[int, Dict] = {}  # {pid: {value, timestamp, ecu_id}}
        self.polling_active = False
        self.poll_interval = 1.0  # segundos
        self.available_pids: Set[int] = set()  # PIDs suportados pelo ECU
        self.checking_pids = False  # Flag for verification in progress
        
        # Statistics
        self.request_count = 0
        self.response_count = 0
        
        # Select first available bus
        self.active_bus = None
        if can_bus_manager and can_bus_manager.buses:
            self.active_bus = list(can_bus_manager.buses.values())[0]
        
        self._setup_ui()
        
        # Timer para polling
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_pids)
        
        # Timer for UI updates (runs continuously to update connection status)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Atualiza a cada 500ms
        
        # Buffer para armazenar mensagens recebidas (para DTCs e single shot)
        self.received_messages = []
        self.receiving_dtcs = False
        self.dtcs_found = []
        self.dtc_buffer = bytearray()  # Buffer para juntar frames multi-frame
        self.dtc_response_received = False  # Flag para rastrear se recebeu resposta de DTC
        
        # Conecta sinal para processar mensagens de forma thread-safe
        self.message_received.connect(self._process_can_message)
    
    def on_can_message(self, bus_name: str, msg: CANMessage):
        """Recebe mensagens CAN de outra thread - emite sinal para processamento thread-safe"""
        # Check if OBD-II response (0x7E8-0x7EF)
        if 0x7E8 <= msg.can_id <= 0x7EF:
            # Emite sinal para processar na thread principal da UI
            self.message_received.emit(bus_name, msg)
    
    def _process_can_message(self, bus_name: str, msg: CANMessage):
        """Processa mensagens CAN na thread principal da UI (thread-safe)"""
        # Filter by selected bus (if multiple)
        if self.active_bus and hasattr(msg, 'source') and msg.source != self.active_bus.config.name:
            return
        
        # Armazena para processamento por DTCs ou single shot
        self.received_messages.append(msg)
        
        # If receiving DTCs, process ALL frames (first and continuation)
        if self.receiving_dtcs and len(msg.data) >= 2:
            # Primeiro frame: [Length, 0x43, ...]
            # Continuation frames: [Length, data...]
            if msg.data[1] == 0x43 or (len(msg.data) > 1 and msg.data[0] in [0x04, 0x05, 0x06, 0x07]):
                self._process_dtc_response(msg)
        
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
    
    def _setup_ui(self):
        """Configura interface"""
        layout = QVBoxLayout()
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Splitter principal (PID selector | Live values)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: PID selection
        left_panel = self._create_pid_selector()
        splitter.addWidget(left_panel)
        
        # Lado direito: Tabs
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
        
        layout.addWidget(splitter)
        
        # Footer with controls
        footer = self._create_footer()
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QWidget:
        """Create header with information"""
        group = QGroupBox("OBD-II Protocol Information")
        main_layout = QVBoxLayout()
        
        # Top row: info on left, status/bus on right
        top_layout = QHBoxLayout()
        
        # Left side: Protocol title
        title_label = QLabel("<b style='font-size: 14px;'>On-Board Diagnostics II</b>")
        top_layout.addWidget(title_label)
        
        top_layout.addStretch()
        
        # Right side: Channel selector with status
        right_layout = QHBoxLayout()
        
        # Channel selection with integrated status
        if self.can_bus_manager and len(self.can_bus_manager.buses) > 1:
            # Multiple buses - show dropdown
            right_layout.addWidget(QLabel("<b>Channel:</b>"))
            self.bus_combo = QComboBox()
            self.bus_combo.setMinimumWidth(180)
            for bus_name, bus in self.can_bus_manager.buses.items():
                if bus.connected:
                    self.bus_combo.addItem(f"{bus_name} - Connected")
                else:
                    self.bus_combo.addItem(f"{bus_name} - Simulation")
            self.bus_combo.currentIndexChanged.connect(self._change_active_bus)
            right_layout.addWidget(self.bus_combo)
            # Store reference for status updates
            self.channel_label = None
        elif self.can_bus_manager and len(self.can_bus_manager.buses) == 1:
            # Single bus - show as label with colored status
            bus_name = list(self.can_bus_manager.buses.keys())[0]
            bus = list(self.can_bus_manager.buses.values())[0]
            self.channel_label = QLabel()
            self._update_channel_status(bus_name, bus.connected)
            right_layout.addWidget(self.channel_label)
        else:
            # No bus available
            self.channel_label = QLabel("<b>Channel:</b> <span style='color: red; font-weight: bold;'>Disconnected</span>")
            right_layout.addWidget(self.channel_label)
        
        top_layout.addLayout(right_layout)
        main_layout.addLayout(top_layout)
        
        # Add separator line
        line = QLabel()
        line.setFrameStyle(QLabel.Shape.HLine | QLabel.Shadow.Sunken)
        main_layout.addWidget(line)
        
        # Protocol information
        info_text = QLabel(
            "• Protocol: ISO 15765-4 (CAN)<br>"
            "• Type: Request/Response (polling)<br>"
            "• Request ID: 0x7DF (broadcast)<br>"
            "• Response IDs: 0x7E8-0x7EF"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #555; font-size: 11px;")
        main_layout.addWidget(info_text)
        
        # Statistics
        self.stats_label = QLabel("Requests: 0 | Responses: 0 | Success Rate: 0.0%")
        self.stats_label.setStyleSheet("color: gray; font-size: 10px;")
        main_layout.addWidget(self.stats_label)
        
        group.setLayout(main_layout)
        return group
    
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
        
        # Filtro compacto (inline)
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
        
        # Lista de PIDs disponíveis
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
        
        # Tabela de valores
        self.values_table = QTableWidget()
        self.values_table.setColumnCount(6)
        self.values_table.setHorizontalHeaderLabels([
            "PID", "Name", "Value", "Unit", "ECU", "Last Update"
        ])
        
        # Configuração otimizada para Name e Value
        header = self.values_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # PID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Name - ajustável
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Value - ajustável
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Unit
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # ECU
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Last Update
        
        # Define larguras iniciais para Name e Value
        self.values_table.setColumnWidth(1, 250)  # Name - mais largo
        self.values_table.setColumnWidth(2, 120)  # Value - largo o suficiente
        
        # Linhas mais compactas mas mantém fonte normal
        self.values_table.verticalHeader().setDefaultSectionSize(24)
        self.values_table.verticalHeader().setVisible(False)
        
        self.values_table.setAlternatingRowColors(True)
        layout.addWidget(self.values_table)
        
        # Botão Clear
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
        
        # Tabela de mensagens
        self.raw_table = QTableWidget()
        self.raw_table.setColumnCount(5)
        self.raw_table.setHorizontalHeaderLabels([
            "Timestamp", "ID", "Type", "Data", "Decoded"
        ])
        
        # Configuração otimizada
        header = self.raw_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Timestamp
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Data
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Decoded
        
        # Linhas mais compactas mas mantém fonte normal
        self.raw_table.verticalHeader().setDefaultSectionSize(24)
        self.raw_table.verticalHeader().setVisible(False)
        
        self.raw_table.setAlternatingRowColors(True)
        layout.addWidget(self.raw_table)
        
        # Limitar a 500 mensagens
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
        """Create footer with controls"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        # Controles de polling
        poll_group = QGroupBox("Polling Control")
        poll_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ " + t('obd2_start_polling'))
        self.start_btn.clicked.connect(self._start_polling)
        self.start_btn.setEnabled(False)
        poll_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏸ " + t('obd2_stop_polling'))
        self.stop_btn.clicked.connect(self._stop_polling)
        self.stop_btn.setEnabled(False)
        poll_layout.addWidget(self.stop_btn)
        
        self.single_shot_btn = QPushButton(t('obd2_single_shot'))
        self.single_shot_btn.clicked.connect(self._single_shot)
        self.single_shot_btn.setEnabled(False)
        self.single_shot_btn.setToolTip("Read selected PIDs once (no continuous polling)")
        poll_layout.addWidget(self.single_shot_btn)
        
        poll_layout.addWidget(QLabel("Interval:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 10000)
        self.interval_spin.setValue(1000)
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.setSingleStep(100)
        self.interval_spin.valueChanged.connect(self._update_poll_interval)
        poll_layout.addWidget(self.interval_spin)
        
        poll_group.setLayout(poll_layout)
        layout.addWidget(poll_group)
        
        layout.addStretch()
        
        # Botão Read DTCs
        self.read_dtc_btn = QPushButton("🔍 " + t('obd2_read_dtcs'))
        self.read_dtc_btn.clicked.connect(self._read_dtcs)
        self.read_dtc_btn.setToolTip("Read Diagnostic Trouble Codes (Service 03)")
        layout.addWidget(self.read_dtc_btn)
        
        # Botão Save Results
        save_btn = QPushButton("💾 " + t('obd2_save_results'))
        save_btn.clicked.connect(self._save_results)
        save_btn.setToolTip("Export current values to CSV file")
        layout.addWidget(save_btn)
        
        # Botão fechar
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        widget.setLayout(layout)
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
            
            # Marcar se já selecionado
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
            # Reset dropdown para "-- Select Preset --"
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
        
        # Limpa lista de PIDs disponíveis
        self.available_pids.clear()
        
        # PIDs de suporte: 0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xE0
        support_pids = [0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xE0]
        
        # Envia requisições para todos os PIDs de suporte
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
        
        # Aguarda 2 segundos para receber todas as respostas
        QTimer.singleShot(2000, self._check_available_pids_complete)
    
    def _check_available_pids_complete(self):
        """Callback after PID verification completes"""
        self.checking_pids = False
        self.check_pids_btn.setEnabled(True)
        
        if self.available_pids:
            # Atualiza lista de PIDs para mostrar apenas disponíveis
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
        
        # Dados estão nos bytes 3-6 (4 bytes = 32 bits)
        data = msg.data[3:7]
        
        # Converte para inteiro de 32 bits
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
                # PID disponível - habilita e marca
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
                original_text = item.text().replace(" ✓", "").replace(" ✗", "")
                item.setText(f"{original_text} ✓")
                item.setForeground(QColor(0, 128, 0))  # Verde
            else:
                # PID não disponível - desabilita e marca
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                original_text = item.text().replace(" ✓", "").replace(" ✗", "")
                item.setText(f"{original_text} ✗")
                item.setForeground(QColor(128, 128, 128))  # Cinza
    
    def _on_pid_selection_changed(self):
        """Callback when PID selection changes"""
        # Atualiza selected_pids baseado na seleção atual
        self.selected_pids.clear()
        for item in self.pid_list.selectedItems():
            pid = item.data(Qt.ItemDataRole.UserRole)
            self.selected_pids.add(pid)
        
        self.selection_label.setText(f"Selected: {len(self.selected_pids)} PIDs")
        
        # Habilita botões se houver PIDs selecionados e estiver conectado
        has_selection = len(self.selected_pids) > 0
        is_connected = self.active_bus is not None and self.active_bus.connected
        
        self.start_btn.setEnabled(has_selection and is_connected and not self.polling_active)
        self.single_shot_btn.setEnabled(has_selection and is_connected and not self.polling_active)
    
    def _update_pid_selection(self):
        """Update visual PID selection"""
        # Bloqueia sinais temporariamente para evitar loops
        self.pid_list.blockSignals(True)
        
        for i in range(self.pid_list.count()):
            item = self.pid_list.item(i)
            pid = item.data(Qt.ItemDataRole.UserRole)
            item.setSelected(pid in self.selected_pids)
        
        self.pid_list.blockSignals(False)
        
        # Atualiza label e botões
        self.selection_label.setText(f"Selected: {len(self.selected_pids)} PIDs")
        has_selection = len(self.selected_pids) > 0
        is_connected = self.active_bus is not None and self.active_bus.connected
        self.start_btn.setEnabled(has_selection and is_connected and not self.polling_active)
        self.single_shot_btn.setEnabled(has_selection and is_connected and not self.polling_active)
    
    def _start_polling(self):
        """Inicia polling de PIDs"""
        # Atualizar seleção baseado na lista
        self.selected_pids.clear()
        for item in self.pid_list.selectedItems():
            pid = item.data(Qt.ItemDataRole.UserRole)
            self.selected_pids.add(pid)
        
        if not self.selected_pids:
            return
        
        self.polling_active = True
        self.poll_timer.start(int(self.poll_interval * 1000))
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.single_shot_btn.setEnabled(False)
        self.pid_list.setEnabled(False)
        
        # Statistics
        self.request_count = 0
        self.response_count = 0
        
        self._log_message("✅ Polling started")
    
    def _stop_polling(self):
        """Para polling de PIDs"""
        self.polling_active = False
        self.poll_timer.stop()
        # Não para update_timer - deixa rodando para atualizar status de conexão
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.single_shot_btn.setEnabled(True)
        self.pid_list.setEnabled(True)
        
        self._log_message("⏸ Polling stopped")
    
    def _single_shot(self):
        """Read selected PIDs once (no continuous polling)"""
        # Atualizar seleção baseado na lista
        self.selected_pids.clear()
        for item in self.pid_list.selectedItems():
            pid = item.data(Qt.ItemDataRole.UserRole)
            self.selected_pids.add(pid)
        
        if not self.selected_pids:
            return
        
        if not self.active_bus or not self.active_bus.bus:
            return
        
        self._log_message("Single shot - reading selected PIDs...")
        
        # Desabilita botões temporariamente
        self.start_btn.setEnabled(False)
        self.single_shot_btn.setEnabled(False)
        self.read_dtc_btn.setEnabled(False)
        
        # Envia todas as requisições de uma vez
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
                
                # Adiciona à tabela raw
                pid_info = OBD2_PIDS.get(pid, {})
                pid_name = pid_info.get('name', f'PID 0x{pid:02X}')
                self._add_raw_request(request, f"Request: {pid_name}")
                
            except Exception as e:
                self._log_message(f"Error reading PID 0x{pid:02X}: {e}")
        
        # Aguarda 1 segundo para receber respostas (as respostas são processadas pelo thread de recepção)
        QTimer.singleShot(1000, self._single_shot_complete)
    
    def _single_shot_complete(self):
        """Callback after single shot completes"""
        self._log_message(f"Single shot complete - requested {len(self.selected_pids)} PIDs")
        
        # Re-habilita botões
        self.start_btn.setEnabled(True)
        self.single_shot_btn.setEnabled(True)
        self.read_dtc_btn.setEnabled(True)
    
    def _process_dtc_response(self, msg: CANMessage):
        """Processa resposta de DTC com suporte a multi-frame"""
        if len(msg.data) < 2:
            return
        
        # Marca que recebeu resposta
        self.dtc_response_received = True
        
        # Primeiro frame: [Length, 0x43, Num DTCs, DTC1_H, DTC1_L, ...]
        if msg.data[1] == 0x43:
            # Limpa buffer e inicia novo
            self.dtc_buffer.clear()
            
            if len(msg.data) < 3:
                return
            
            num_dtcs = msg.data[2]
            if num_dtcs == 0:
                return
            
            # Adiciona dados do primeiro frame ao buffer (a partir do byte 3)
            self.dtc_buffer.extend(msg.data[3:])
            
            # Debug: mostra buffer após primeiro frame
            # self._log_message(f"  [DEBUG] First frame buffer: {self.dtc_buffer.hex()}")
        else:
            # Frame de continuação - adiciona dados ao buffer (a partir do byte 1)
            # Mas só se não for padding (00 00 00 00)
            data_to_add = msg.data[1:]
            # Remove padding do final
            while len(data_to_add) > 0 and data_to_add[-1] == 0x00:
                data_to_add = data_to_add[:-1]
            
            if len(data_to_add) > 0:
                self.dtc_buffer.extend(data_to_add)
            
            # Debug: mostra buffer após frame de continuação
            # self._log_message(f"  [DEBUG] After continuation buffer: {self.dtc_buffer.hex()}")
        
        # Processa apenas DTCs que ainda não foram encontrados
        # Para evitar duplicatas ao receber múltiplos frames
        temp_dtcs = []
        idx = 0
        while idx + 1 < len(self.dtc_buffer):
            dtc_high = self.dtc_buffer[idx]
            dtc_low = self.dtc_buffer[idx + 1]
            
            # Ignora DTCs vazios (0x0000)
            if dtc_high == 0 and dtc_low == 0:
                idx += 2
                continue
            
            # Decodifica DTC
            dtc_code = self._decode_dtc(dtc_high, dtc_low)
            if dtc_code not in temp_dtcs:
                temp_dtcs.append(dtc_code)
            
            idx += 2
        
        # Adiciona apenas novos DTCs
        for dtc in temp_dtcs:
            if dtc not in self.dtcs_found:
                self.dtcs_found.append(dtc)
                self._log_message(f"  • {dtc}")
    
    def _read_dtcs(self):
        """Read Diagnostic Trouble Codes (Service 03)"""
        if not self.active_bus or not self.active_bus.bus:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Cannot read DTCs: Not connected to CAN bus."
            )
            return
        
        self._log_message("Reading DTCs (Service 03)...")
        
        # Desabilita botões temporariamente
        self.start_btn.setEnabled(False)
        self.single_shot_btn.setEnabled(False)
        self.read_dtc_btn.setEnabled(False)
        
        # Limpa buffer de DTCs
        self.dtcs_found = []
        self.dtc_buffer.clear()
        self.dtc_response_received = False
        self.receiving_dtcs = True
        
        try:
            # Envia request (Service 03 = Show stored DTCs)
            request = can.Message(
                arbitration_id=0x7DF,  # Broadcast
                data=[0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            
            self.active_bus.send(request)
            self._add_raw_request(request, "Request: Read DTCs (Service 03)")
            
            # Aguarda 1 segundo para receber respostas (processadas por on_can_message)
            QTimer.singleShot(1000, self._read_dtcs_complete)
        
        except Exception as e:
            self._log_message(f"Error reading DTCs: {e}")
            self.receiving_dtcs = False
            self.start_btn.setEnabled(True)
            self.single_shot_btn.setEnabled(True)
            self.read_dtc_btn.setEnabled(True)
    
    def _read_dtcs_complete(self):
        """Callback after DTC read completes"""
        self.receiving_dtcs = False
        
        # Verifica se recebeu alguma resposta
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
        # Mostra resultado em popup
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
            # Recebeu resposta mas sem DTCs
            self._log_message("No DTCs found - vehicle is healthy!")
            QMessageBox.information(
                self,
                "No DTCs",
                "No Diagnostic Trouble Codes found.\n\nVehicle is healthy! ✅"
            )
        
        # Re-habilita botões
        self.start_btn.setEnabled(True)
        self.single_shot_btn.setEnabled(True)
        self.read_dtc_btn.setEnabled(True)
    
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
        
        # Resto do código (14 bits)
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
                
                # Adiciona à tabela raw
                pid_info = OBD2_PIDS.get(pid, {})
                pid_name = pid_info.get('name', f'PID 0x{pid:02X}')
                self._add_raw_request(request, f"Poll: {pid_name}")
                
                # Respostas serão processadas automaticamente por on_can_message()
                
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
        
        # Adiciona à tabela raw
        self._add_raw_message(msg, f"Response PID 0x{pid:02X}: {value_str}")
    
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
        # Atualiza tabela de valores (apenas se houver dados ou polling ativo)
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
                
                # Não colorir - mantém legibilidade
                age = time.time() - data['timestamp']
                
                self.values_table.setItem(row, 2, value_item)
                
                # Unidade
                self.values_table.setItem(row, 3, QTableWidgetItem(pid_info.get('unit', '')))
                
                # ECU
                self.values_table.setItem(row, 4, QTableWidgetItem(f"0x{data['ecu_id']:03X}"))
                
                # Timestamp (só atualiza se polling ativo)
                if self.polling_active:
                    self.values_table.setItem(row, 5, QTableWidgetItem(f"{age:.1f}s ago"))
                else:
                    # Se não está em polling, mostra timestamp fixo
                    timestamp_str = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')
                    self.values_table.setItem(row, 5, QTableWidgetItem(timestamp_str))
        
        # Atualiza estatísticas
        if self.request_count > 0:
            success_rate = (self.response_count / self.request_count) * 100
        else:
            success_rate = 0
        
        self.stats_label.setText(
            f"Requests: {self.request_count} | "
            f"Responses: {self.response_count} | "
            f"Success Rate: {success_rate:.1f}%"
        )
        
        # Atualiza status da conexão (apenas se tiver label de canal único)
        if hasattr(self, 'channel_label') and self.channel_label and self.active_bus:
            bus_name = self.active_bus.config.name if hasattr(self.active_bus, 'config') else "CAN"
            self._update_channel_status(bus_name, self.active_bus.connected)
    
    def _add_raw_message(self, msg: CANMessage, decoded: str):
        """Add raw message to table"""
        # Limitar número de mensagens
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
        # Limitar número de mensagens
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
            status_html = "<span style='color: green; font-weight: bold;'>Connected</span>"
        else:
            status_html = "<span style='color: #0066cc; font-weight: bold;'>Simulation</span>"
        self.channel_label.setText(f"<b>Channel:</b> {bus_name} - {status_html}")
    
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
        self.start_btn.setEnabled(len(self.selected_pids) > 0 and self.active_bus is not None)
    
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
        
        # Nome padrão com timestamp
        default_name = f"obd2_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save OBD-II Results",
            default_name,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filename:
            return  # Usuário cancelou
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Cabeçalho
                writer.writerow([
                    'PID',
                    'Name',
                    'Value',
                    'Unit',
                    'ECU ID',
                    'Timestamp',
                    'Age (seconds)'
                ])
                
                # Dados
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
                
                # Adiciona estatísticas no final
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
