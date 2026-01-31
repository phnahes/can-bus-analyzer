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
from .dialogs_new import SettingsDialog, BitFieldViewerDialog, FilterDialog, TriggerDialog
from .file_operations import FileOperations
from .logger import get_logger
from .i18n import get_i18n, t
from .theme import detect_dark_mode, get_adaptive_colors, should_use_dark_mode

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
        self.recording = False  # Apenas para Tracer: controla se mensagens são salvas para reprodução
        self.paused = False
        self.tracer_mode = False  # Tracer Mode
        self.recorded_messages: List[CANMessage] = []  # Mensagens gravadas para reprodução (Tracer)
        self.can_bus: Optional[can.BusABC] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.message_queue = queue.Queue()
        self.received_messages: List[CANMessage] = []
        self.transmit_messages: List[Dict] = []
        self.message_counters = defaultdict(int)  # Counter per ID
        self.message_last_timestamp = {}  # Último timestamp por ID para calcular period
        
        # Playback control
        self.playback_active = False
        self.playback_paused = False
        self.playback_thread: Optional[threading.Thread] = None
        self.playback_stop_event = threading.Event()
        self.current_playback_row = -1
        
        # Message filters
        self.message_filters = {
            'enabled': False,
            'id_filters': [],
            'data_filters': [],
            'show_only': True
        }
        
        # Triggers for automatic transmission
        self.triggers = []
        self.triggers_enabled = False
        
        # Periodic transmission control
        self.periodic_send_active = False
        self.periodic_send_threads = {}  # {row_index: thread}
        self.periodic_send_stop_events = {}  # {row_index: threading.Event}
        
        # Transmit editing state
        self.editing_tx_row = -1  # -1 = adding new, >= 0 = editing existing row
        
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
        """Inicializa a interface do usuário"""
        self.setWindowTitle("CAN Analyzer - macOS")
        self.setGeometry(100, 100, 1200, 800)
        
        # Get adaptive colors based on theme preference
        self.colors = get_adaptive_colors(self.theme_preference)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Criar menu bar
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
        
        # Pause button (desabilitado temporariamente - manter lógica)
        self.btn_pause = QPushButton()
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setVisible(False)  # Ocultar por enquanto
        toolbar_layout.addWidget(self.btn_pause)
        
        # Botão Tracer/Monitor Mode (alterna entre os dois)
        self.btn_tracer = QPushButton()
        self.btn_tracer.setCheckable(True)
        self.btn_tracer.clicked.connect(self.toggle_tracer_mode)
        toolbar_layout.addWidget(self.btn_tracer)
        
        # Espaço expansível para empurrar botão TX para direita
        toolbar_layout.addStretch()
        
        # Botão Toggle Transmit Panel (no canto direito)
        self.btn_toggle_transmit = QPushButton("📤 Hide TX")
        self.btn_toggle_transmit.setToolTip("Mostrar/Ocultar painel de Transmissão")
        self.btn_toggle_transmit.clicked.connect(self.toggle_transmit_panel)
        toolbar_layout.addWidget(self.btn_toggle_transmit)
        self.transmit_panel_visible = True  # Estado do painel
        
        main_layout.addLayout(toolbar_layout)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Painel de Recepção
        self.receive_group = QGroupBox("Receive (Monitor)")
        receive_layout = QVBoxLayout()
        
        self.receive_table = QTableWidget()
        self.setup_receive_table()
        
        # Ocultar cabeçalho vertical (números de linha padrão)
        self.receive_table.verticalHeader().setVisible(False)
        
        # Fonte monoespaçada maior para melhor legibilidade
        font = QFont("Courier New", 14)
        self.receive_table.setFont(font)
        
        # Habilitar seleção múltipla
        self.receive_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.receive_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Menu de contexto (botão direito)
        self.receive_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.receive_table.customContextMenuRequested.connect(self.show_receive_context_menu)
        
        receive_layout.addWidget(self.receive_table)
        
        # Controles de reprodução do Tracer (inicialmente ocultos)
        self.tracer_controls_widget = QWidget()
        tracer_controls_layout = QHBoxLayout(self.tracer_controls_widget)
        tracer_controls_layout.setContentsMargins(0, 5, 0, 5)
        
        # Botão Record (exclusivo do Tracer)
        self.btn_record = QPushButton("⏺ Record")
        self.btn_record.setCheckable(True)
        self.btn_record.setToolTip("Gravar mensagens para reprodução posterior")
        self.btn_record.clicked.connect(self.toggle_recording)
        tracer_controls_layout.addWidget(self.btn_record)
        
        # Botão Clear (limpar mensagens gravadas)
        self.btn_clear_tracer = QPushButton("🗑 Clear")
        self.btn_clear_tracer.setToolTip("Limpar mensagens gravadas")
        self.btn_clear_tracer.clicked.connect(self.clear_tracer_messages)
        tracer_controls_layout.addWidget(self.btn_clear_tracer)
        
        tracer_controls_layout.addWidget(QLabel("|"))
        
        self.btn_play_all = QPushButton("▶ Play All")
        self.btn_play_all.setToolTip("Reproduzir (enviar) todas as mensagens gravadas")
        self.btn_play_all.clicked.connect(self.play_all_messages)
        self.btn_play_all.setEnabled(False)  # Desabilitado até gravar mensagens
        tracer_controls_layout.addWidget(self.btn_play_all)
        
        self.btn_play_selected = QPushButton("▶ Play Selected")
        self.btn_play_selected.setToolTip("Reproduzir (enviar) apenas as mensagens selecionadas")
        self.btn_play_selected.clicked.connect(self.play_selected_message)
        self.btn_play_selected.setEnabled(False)  # Desabilitado até gravar mensagens
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
        
        self.tracer_controls_widget.setVisible(False)  # Oculto por padrão
        receive_layout.addWidget(self.tracer_controls_widget)
        
        self.receive_group.setLayout(receive_layout)
        splitter.addWidget(self.receive_group)
        
        # Painel de Transmissão
        self.transmit_group = QGroupBox("Transmit")
        transmit_layout = QVBoxLayout()
        
        # Tabela de mensagens para transmitir
        self.transmit_table = QTableWidget()
        self.transmit_table.setColumnCount(17)
        self.transmit_table.setHorizontalHeaderLabels([
            'PID', 'DLC', 'RTR', 'Period', 'TX Mode', 'Trigger ID', 'Trigger Data',
            'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'Count', 'Comment'
        ])
        
        # Double-click para carregar mensagem nos campos de edição
        self.transmit_table.itemDoubleClicked.connect(self.load_tx_message_to_edit)
        
        # Context menu para transmit table
        self.transmit_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.transmit_table.customContextMenuRequested.connect(self.show_transmit_context_menu)
        
        # Tornar tabela readonly
        self.transmit_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Fonte maior para transmit
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
        # Bytes de dados (D0-D7)
        for i in range(7, 15):
            header_tx.resizeSection(i, 40)
        header_tx.resizeSection(15, 60)  # Count
        header_tx.resizeSection(16, 150) # Comment
        
        transmit_layout.addWidget(self.transmit_table)
        
        # Controles de transmissão
        tx_controls = QWidget()
        tx_controls_layout = QVBoxLayout(tx_controls)
        
        # Linha 1: PID | DLC | Data | Period
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("PID:"))
        self.tx_id_input = QLineEdit("000")
        self.tx_id_input.setMaximumWidth(80)
        self.tx_id_input.setPlaceholderText("000")
        row1.addWidget(self.tx_id_input)
        
        # Separador visual
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
        
        # Separador visual
        sep2 = QLabel("│")
        sep2.setStyleSheet(self.colors['separator'])
        row1.addWidget(sep2)
        
        row1.addWidget(QLabel("Data:"))
        
        # Criar 8 campos para cada byte (sem labels D0, D1, etc)
        self.tx_data_bytes = []
        for i in range(8):
            byte_input = QLineEdit("00")
            byte_input.setMaximumWidth(35)
            byte_input.setMaxLength(2)
            byte_input.setInputMask("HH")  # Apenas hexadecimal
            byte_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tx_data_bytes.append(byte_input)
            row1.addWidget(byte_input)
        
        # Separador visual
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
        
        # Linha 2: Options: 29 Bit, RTR | Comment
        row2 = QHBoxLayout()
        
        row2.addWidget(QLabel("Options:"))
        
        self.tx_29bit_check = QCheckBox("29 Bit")
        row2.addWidget(self.tx_29bit_check)
        
        self.tx_rtr_check = QCheckBox("RTR")
        row2.addWidget(self.tx_rtr_check)
        
        # Separador visual
        sep4 = QLabel("│")
        sep4.setStyleSheet(self.colors['separator'])
        row2.addWidget(sep4)
        
        row2.addWidget(QLabel("Comment:"))
        self.tx_comment_input = QLineEdit()
        self.tx_comment_input.setPlaceholderText("Optional description")
        row2.addWidget(self.tx_comment_input)
        
        row2.addStretch()
        tx_controls_layout.addLayout(row2)
        
        # Linha 3: TX Mode, Trigger ID, Trigger Data
        row3 = QHBoxLayout()
        
        row3.addWidget(QLabel("TX Mode:"))
        self.tx_mode_combo = QComboBox()
        self.tx_mode_combo.addItems(["off", "on", "trigger"])
        self.tx_mode_combo.setMaximumWidth(100)
        row3.addWidget(self.tx_mode_combo)
        
        # Separador visual
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
        
        # Linha 4: Botões - Add/Save, Delete, Clear | Send, Send All/Stop All [espaço] Save, Load
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
        
        # Separador visual
        separator = QLabel("|")
        separator.setStyleSheet(f"{self.colors['separator']}; font-size: 16px; padding: 0 10px;")
        row4.addWidget(separator)
        
        self.btn_single = QPushButton("Send")
        self.btn_single.clicked.connect(self.send_single)
        row4.addWidget(self.btn_single)
        
        self.btn_send_all = QPushButton("Send All")
        self.btn_send_all.clicked.connect(self.send_all)
        row4.addWidget(self.btn_send_all)
        
        # Espaço expansível para empurrar Save/Load para direita
        row4.addStretch()
        
        # Botões de arquivo no canto direito
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
        
        # Definir proporções do splitter
        splitter.setSizes([500, 300])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        status_bar_layout = QHBoxLayout()
        
        # Lado esquerdo: informações de conexão e status
        self.connection_status = QLabel("Not Connected")
        status_bar_layout.addWidget(self.connection_status)
        
        status_bar_layout.addWidget(QLabel("|"))
        
        self.device_label = QLabel()
        status_bar_layout.addWidget(self.device_label)
        
        status_bar_layout.addWidget(QLabel("|"))
        
        # Label mostra o modo de operação do CAN (Listen Only / Normal)
        self.mode_label = QLabel()
        status_bar_layout.addWidget(self.mode_label)
        
        status_bar_layout.addWidget(QLabel("|"))
        
        self.filter_status_label = QLabel("Filter: Off")
        status_bar_layout.addWidget(self.filter_status_label)
        
        status_bar_layout.addWidget(QLabel("|"))
        
        self.msg_count_label = QLabel("Messages: 0")
        status_bar_layout.addWidget(self.msg_count_label)
        
        status_bar_layout.addStretch()
        
        # Lado direito: área para notificações
        self.notification_label = QLabel("")
        self.notification_label.setStyleSheet(self.colors['notification'])
        self.notification_label.setWordWrap(True)  # Quebra linha apenas se necessário
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.notification_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        status_bar_layout.addWidget(self.notification_label)
        
        main_layout.addLayout(status_bar_layout)
        
        # Atualizar textos com traduções (APÓS criar todos os elementos)
        self.update_ui_translations()
    
    def setup_receive_table(self):
        """Configura a tabela de recepção baseado no modo"""
        if self.tracer_mode:
            # Modo Tracer: ID, Time, PID, DLC, Data, ASCII, Comment
            self.receive_table.setColumnCount(7)
            self.receive_table.setHorizontalHeaderLabels(['ID', 'Time', 'PID', 'DLC', 'Data', 'ASCII', 'Comment'])
            
            # Modo Tracer: permitir edição (apenas Comment)
            self.receive_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
            
            # Permitir redimensionamento manual de todas as colunas
            header = self.receive_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            
            # Definir larguras iniciais apropriadas
            header.resizeSection(0, 60)   # ID (sequencial)
            header.resizeSection(1, 100)  # Time
            header.resizeSection(2, 80)   # PID (CAN ID)
            header.resizeSection(3, 60)   # DLC
            header.resizeSection(4, 250)  # Data
            header.resizeSection(5, 100)  # ASCII
            header.resizeSection(6, 150)  # Comment
            
            # Permitir que a última coluna se expanda se houver espaço
            header.setStretchLastSection(True)
        else:
            # Modo Monitor: ID, Count, PID, DLC, Data, Period, ASCII, Comment
            self.receive_table.setColumnCount(8)
            self.receive_table.setHorizontalHeaderLabels(['ID', 'Count', 'PID', 'DLC', 'Data', 'Period', 'ASCII', 'Comment'])
            
            # Modo Monitor: NÃO permitir edição (dados são atualizados automaticamente)
            self.receive_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            
            # Permitir redimensionamento manual de todas as colunas
            header = self.receive_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            
            # Definir larguras iniciais apropriadas
            header.resizeSection(0, 40)   # ID (sequencial)
            header.resizeSection(1, 60)   # Count
            header.resizeSection(2, 80)   # PID (CAN ID)
            header.resizeSection(3, 50)   # DLC
            header.resizeSection(4, 250)  # Data
            header.resizeSection(5, 70)   # Period
            header.resizeSection(6, 100)  # ASCII
            header.resizeSection(7, 150)  # Comment
            
            # Permitir que a última coluna se expanda se houver espaço
            header.setStretchLastSection(True)
    
    def toggle_tracer_mode(self):
        """Alterna entre modo Tracer (cronológico) e Monitor (agrupado)
        
        Monitor Mode: Agrupa por ID, mostra última mensagem, contador
        Tracer Mode: Lista todas as mensagens em ordem cronológica
        """
        # Inverter a lógica: quando clicado, ativa Tracer, mas visualmente "desclica" o botão
        self.tracer_mode = not self.tracer_mode
        self.btn_tracer.setChecked(False)  # Sempre manter visualmente "desclicado"
        
        # Atualizar texto do botão (mostra o modo OPOSTO para onde vai alternar)
        if self.tracer_mode:
            # Está em Tracer, botão mostra "Monitor" para voltar
            self.btn_tracer.setText(f"📊 {t('btn_monitor')}")
        else:
            # Está em Monitor, botão mostra "Tracer" para ativar
            self.btn_tracer.setText(f"📊 {t('btn_tracer')}")
        
        # NÃO limpar contadores nem mensagens - apenas reconfigurar tabela
        # self.message_counters.clear()  # REMOVIDO - mantém dados
        
        # OTIMIZAÇÃO: Desabilitar atualizações da UI durante repopulação
        self.receive_table.setUpdatesEnabled(False)
        
        # Limpar tabela antes de reconfigurar
        self.receive_table.setRowCount(0)
        
        # Reconfigurar tabela (colunas e headers)
        self.setup_receive_table()
        
        # Repopular tabela com dados existentes (SUPER OTIMIZADO)
        if self.tracer_mode:
            # Modo Tracer: Repopular APENAS com mensagens gravadas (se houver)
            if len(self.recorded_messages) > 0:
                self.receive_table.setRowCount(len(self.recorded_messages))
                
                for row_idx, msg in enumerate(self.recorded_messages):
                    dt = datetime.fromtimestamp(msg.timestamp)
                    time_str = dt.strftime("%S.%f")[:-3]
                    pid_str = f"0x{msg.can_id:03X}"
                    data_str = " ".join([f"{b:02X}" for b in msg.data])
                    ascii_str = msg.to_ascii()
                    
                    # Criar items com alinhamento
                    id_item = QTableWidgetItem(str(row_idx + 1))
                    id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # IMPORTANTE: Armazenar o índice real em recorded_messages
                    id_item.setData(Qt.ItemDataRole.UserRole, row_idx)
                    
                    dlc_item = QTableWidgetItem(str(msg.dlc))
                    dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Inserir items
                    self.receive_table.setItem(row_idx, 0, id_item)
                    self.receive_table.setItem(row_idx, 1, QTableWidgetItem(time_str))
                    self.receive_table.setItem(row_idx, 2, QTableWidgetItem(pid_str))
                    self.receive_table.setItem(row_idx, 3, dlc_item)
                    self.receive_table.setItem(row_idx, 4, QTableWidgetItem(data_str))
                    self.receive_table.setItem(row_idx, 5, QTableWidgetItem(ascii_str))
                    self.receive_table.setItem(row_idx, 6, QTableWidgetItem(msg.comment))
        else:
            # Modo Monitor: reconstruir visualização agrupada
            # Limpar contadores para reconstruir do zero
            self.message_counters.clear()
            self.message_last_timestamp.clear()
            
            # SUPER OTIMIZAÇÃO: Agrupar mensagens por ID primeiro (em memória)
            # Depois inserir na tabela de uma vez
            total_messages = len(self.received_messages)
            
            if total_messages > 0:
                # 1. Agrupar mensagens por ID (MUITO MAIS RÁPIDO que inserir uma por uma)
                id_data = {}  # {can_id: {'last_msg': msg, 'count': N, 'period': X}}
                
                for msg in self.received_messages:
                    # Verificar filtro
                    if not self.message_passes_filter(msg):
                        continue
                    
                    # Incrementar contador
                    self.message_counters[msg.can_id] += 1
                    count = self.message_counters[msg.can_id]
                    
                    # Calcular period
                    period_str = ""
                    if msg.can_id in self.message_last_timestamp:
                        period_ms = int((msg.timestamp - self.message_last_timestamp[msg.can_id]) * 1000)
                        period_str = f"{period_ms}"
                    
                    # Atualizar timestamp
                    self.message_last_timestamp[msg.can_id] = msg.timestamp
                    
                    # Armazenar dados (última mensagem de cada ID)
                    id_data[msg.can_id] = {
                        'msg': msg,
                        'count': count,
                        'period': period_str
                    }
                
                # 2. Criar todas as linhas de uma vez
                unique_ids = len(id_data)
                self.receive_table.setRowCount(unique_ids)
                
                # 3. Popular tabela com dados agrupados (ORDENADO POR PID)
                row_idx = 0
                for can_id, data in sorted(id_data.items(), key=lambda x: x[0]):
                    msg = data['msg']
                    count = data['count']
                    period_str = data['period']
                    
                    pid_str = f"0x{can_id:03X}"
                    data_str = " ".join([f"{b:02X}" for b in msg.data])
                    ascii_str = msg.to_ascii()
                    
                    # Criar items com alinhamento
                    id_item = QTableWidgetItem(str(row_idx + 1))
                    id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    count_item = QTableWidgetItem(str(count))
                    count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    dlc_item = QTableWidgetItem(str(msg.dlc))
                    dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    period_item = QTableWidgetItem(period_str)
                    period_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Inserir items - Monitor: ID, Count, PID, DLC, Data, Period, ASCII, Comment
                    self.receive_table.setItem(row_idx, 0, id_item)                              # ID sequencial
                    self.receive_table.setItem(row_idx, 1, count_item)                           # Count
                    self.receive_table.setItem(row_idx, 2, QTableWidgetItem(pid_str))            # PID
                    self.receive_table.setItem(row_idx, 3, dlc_item)                             # DLC
                    self.receive_table.setItem(row_idx, 4, QTableWidgetItem(data_str))           # Data
                    self.receive_table.setItem(row_idx, 5, period_item)                          # Period
                    self.receive_table.setItem(row_idx, 6, QTableWidgetItem(ascii_str))          # ASCII
                    self.receive_table.setItem(row_idx, 7, QTableWidgetItem(msg.comment))        # Comment
                    
                    row_idx += 1
                    
                    # Processar eventos a cada 100 IDs
                    if row_idx % 100 == 0:
                        QApplication.processEvents()
        
        # OTIMIZAÇÃO: Re-habilitar atualizações da UI
        self.receive_table.setUpdatesEnabled(True)
        
        # Reconfigurar menu de contexto após recriar tabela
        self.receive_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.receive_table.customContextMenuRequested.connect(self.show_receive_context_menu)
        
        # Reconfigurar seleção múltipla
        self.receive_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.receive_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Mostrar/ocultar controles de reprodução (apenas em Tracer)
        self.tracer_controls_widget.setVisible(self.tracer_mode)
        
        # Atualizar label do grupo
        # Encontrar o QGroupBox pai
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
        # Window title
        self.setWindowTitle(t('app_title'))
        
        # Toolbar buttons
        self.btn_connect.setText(f"🔌 {t('btn_connect')}")
        self.btn_disconnect.setText(f"⏹ {t('btn_disconnect')}")
        self.btn_reset.setText(f"🔄 {t('btn_reset')}")
        self.btn_pause.setText(f"⏸ {t('btn_pause')}")
        self.btn_clear_tracer.setText(f"🗑 {t('btn_clear')}")
        self.btn_tracer.setText(f"📊 {t('btn_tracer') if not self.tracer_mode else t('btn_monitor')}")
        
        # Status label removido - notificações via statusBar()
        
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
        # Botões de transmissão - textos são atualizados dinamicamente
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
        menubar.clear()  # Limpar menus existentes antes de recriar
        
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
    
    def toggle_connection(self):
        """Conecta ou desconecta do barramento CAN"""
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        """Conecta ao barramento CAN"""
        self.logger.info("Tentando conectar ao barramento CAN")
        
        try:
            simulation_mode = self.config.get('simulation_mode', False)
            
            # Tentar conexão real se não estiver em modo simulação
            if not simulation_mode and CAN_AVAILABLE:
                channel = self.config.get('channel', 'can0')
                baudrate = self.config.get('baudrate', 500000)
                
                self.logger.info(f"Tentando conexão real: Channel={channel}, Baudrate={baudrate}")
                
                try:
                    # Detect interface type from channel (cross-platform)
                    channel_upper = channel.upper()
                    if (channel.startswith('/dev/tty.') or channel.startswith('/dev/cu.') or
                            channel.startswith('/dev/ttyUSB') or channel.startswith('/dev/ttyACM') or
                            (channel_upper.startswith('COM') and len(channel) >= 4 and channel[3:].strip().isdigit())):
                        # Serial device (SLCAN) - macOS, Linux, Windows
                        bustype = 'slcan'
                        self.logger.info(f"Using SLCAN interface for {channel}")
                    elif channel.startswith('can') or channel.startswith('vcan'):
                        # SocketCAN (Linux)
                        bustype = 'socketcan'
                        self.logger.info(f"Using SocketCAN interface for {channel}")
                    else:
                        bustype = None
                        self.logger.info("Auto-detecting interface type")
                    
                    # Tentar criar bus CAN
                    if bustype:
                        self.can_bus = can.interface.Bus(
                            channel=channel,
                            bustype=bustype,
                            bitrate=baudrate
                        )
                    else:
                        self.can_bus = can.interface.Bus(
                            channel=channel,
                            bitrate=baudrate
                        )
                    
                    self.logger.info("Conexão real estabelecida com sucesso!")
                    
                    # Configurar interface
                    self.connected = True
                    self.connection_status.setText(f"Connected: {baudrate//1000} kbit/s")
                    self.device_label.setText(f"Device: {channel}")
                    self.show_notification(t('notif_connected', channel=channel, baudrate=baudrate//1000), 5000)
                    
                except Exception as e:
                    self.logger.error(f"Erro ao conectar ao dispositivo real: {str(e)}")
                    self.logger.warning("Tentando modo simulação como fallback")
                    
                    # Perguntar ao usuário se quer usar simulação
                    reply = QMessageBox.question(
                        self,
                        "Connection Error",
                        f"Não foi possível conectar ao dispositivo:\n{str(e)}\n\n"
                        f"Deseja conectar em modo simulação?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.No:
                        return
                    
                    # Ativar modo simulação temporariamente
                    simulation_mode = True
            
            # Modo simulação
            if simulation_mode or not CAN_AVAILABLE:
                self.logger.warning("Conectando em modo simulação")
                self.logger.info(f"Configuração: Channel={self.config.get('channel')}, Baudrate={self.config.get('baudrate', 500000)//1000}Kbps")
                
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
                baudrate = self.config.get('baudrate', 500000)
                self.connection_status.setText(f"Simulation: {baudrate//1000} kbit/s")
                device_info = self.config.get('channel', 'can0')
                self.device_label.setText(f"Device: {device_info} (Sim)")
                self.show_notification(t('notif_simulation_mode', baudrate=baudrate//1000), 5000)
            
            # Configurações comuns
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.btn_pause.setEnabled(True)
            
            # Atualizar label de modo
            if self.config.get('listen_only', True):
                self.mode_label.setText(t('status_listen_only'))
            else:
                self.mode_label.setText(t('status_normal'))
            
            # Iniciar thread de recepção
            self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.receive_thread.start()
            self.logger.info("Thread de recepção iniciada")
            
            # Gerar dados de exemplo apenas em modo simulação
            if simulation_mode or not CAN_AVAILABLE:
                self.generate_sample_data()
            
            self.logger.info("Conexão estabelecida com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Connection Error", f"Erro ao conectar: {str(e)}")
    
    def disconnect(self):
        """Desconecta do barramento CAN"""
        self.logger.info("Desconectando do barramento CAN")
        
        self.connected = False
        
        # Parar envio periódico se estiver ativo
        if self.periodic_send_active:
            self.stop_all()
        
        # Parar gravação se estiver ativa
        if self.recording:
            self.btn_record.setChecked(False)
            self.toggle_recording()
        
        if self.can_bus:
            try:
                self.can_bus.shutdown()
            except Exception as e:
                # Ignorar erros ao desconectar (dispositivo pode já estar desconectado)
                self.logger.warning(f"Erro ao fechar interface CAN (ignorado): {e}")
            finally:
                self.can_bus = None
                self.logger.info("Interface CAN encerrada")
        
        self.connection_status.setText("Not Connected")
        self.device_label.setText("Device: N/A")
        self.show_notification(t('notif_disconnected'), 3000)
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_pause.setEnabled(False)
        
        # Resetar label de modo ao desconectar
        if self.config.get('listen_only', True):
            self.mode_label.setText("Listen Only Mode")
        else:
            self.mode_label.setText("Normal Mode")
    
    def reset(self):
        """Reseta a aplicação sem derrubar a conexão"""
        # Limpar tabela
        self.receive_table.setRowCount(0)
        
        # Limpar dados
        self.received_messages.clear()
        self.message_counters.clear()
        self.message_last_timestamp.clear()
        
        # Limpar mensagens gravadas (Tracer)
        self.recorded_messages.clear()
        
        # Resetar botões de reprodução
        if hasattr(self, 'btn_play_all'):
            self.btn_play_all.setEnabled(False)
            self.btn_play_selected.setEnabled(False)
        
        # Parar gravação se estiver ativa
        if self.recording:
            self.btn_record.setChecked(False)
            self.btn_record.setText("⏺ Record")
            self.btn_record.setStyleSheet("")
            self.recording = False
        
        self.update_message_count()
        self.show_notification(t('notif_reset'))
    
    def toggle_recording(self):
        """Inicia/para a gravação de mensagens para reprodução (apenas Tracer)"""
        self.recording = self.btn_record.isChecked()
        
        if self.recording:
            # Iniciar gravação
            self.recorded_messages.clear()  # Limpar gravações anteriores
            self.receive_table.setRowCount(0)  # Limpar tabela
            self.btn_record.setText("⏺ Recording")
            self.btn_record.setStyleSheet(self.colors['record_active'])
            self.btn_play_all.setEnabled(False)
            self.btn_play_selected.setEnabled(False)
            self.show_notification(t('notif_recording_started'), 3000)
        else:
            # Parar gravação
            self.btn_record.setText("⏺ Record")
            self.btn_record.setStyleSheet("")
            
            # NÃO limpar tabela - manter mensagens gravadas visíveis para replay
            
            # Habilitar botões de reprodução se houver mensagens gravadas
            if len(self.recorded_messages) > 0:
                self.btn_play_all.setEnabled(True)
                self.btn_play_selected.setEnabled(True)
                self.show_notification(t('notif_recording_stopped', count=len(self.recorded_messages)), 3000)
            else:
                self.show_notification(t('notif_recording_stopped_empty'), 3000)
    
    def toggle_transmit_panel(self):
        """Mostra/oculta o painel de Transmissão"""
        self.transmit_panel_visible = not self.transmit_panel_visible
        
        if self.transmit_panel_visible:
            # Mostrar painel
            self.transmit_group.setVisible(True)
            self.btn_toggle_transmit.setText("📤 Hide TX")
            self.show_notification(t('notif_tx_panel_visible'), 2000)
        else:
            # Ocultar painel
            self.transmit_group.setVisible(False)
            self.btn_toggle_transmit.setText("📤 Show TX")
            self.show_notification(t('notif_tx_panel_hidden'), 2000)
    
    def show_notification(self, message: str, duration: int = 3000):
        """Mostra notificação temporária no canto inferior direito"""
        self.notification_label.setText(message)
        
        # Criar timer para limpar notificação
        QTimer.singleShot(duration, lambda: self.notification_label.setText(""))
    
    def clear_tracer_messages(self):
        """Limpa mensagens gravadas no Tracer"""
        self.recorded_messages.clear()
        self.receive_table.setRowCount(0)
        self.btn_play_all.setEnabled(False)
        self.btn_play_selected.setEnabled(False)
        self.show_notification(t('notif_recorded_cleared'))
    
    def toggle_pause(self):
        """Pausa/retoma a exibição"""
        self.paused = not self.paused
        if self.paused:
            self.btn_pause.setText("▶ Resume")
            self.btn_pause.setStyleSheet(self.colors['pause_active'])
        else:
            self.btn_pause.setText("⏸ Pause")
            self.btn_pause.setStyleSheet("")
    
    def clear_receive(self):
        """Limpa a tabela de recepção"""
        self.receive_table.setRowCount(0)
        self.update_message_count()
    
    def receive_loop(self):
        """Loop de recepção de mensagens CAN"""
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
        """Inicia timer para atualização da UI"""
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
                
                # Verificar triggers (antes de adicionar à UI)
                if self.triggers_enabled and self.connected:
                    self.check_and_fire_triggers(msg)
                
                # Exibir mensagens na UI
                if self.tracer_mode:
                    # Tracer: só exibir se estiver gravando (Record ativo)
                    if self.recording:
                        self.recorded_messages.append(msg)  # Adicionar à lista ANTES de exibir
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
        # Verificar filtro
        if not self.message_passes_filter(msg):
            return
        
        dt = datetime.fromtimestamp(msg.timestamp)
        time_str = dt.strftime("%S.%f")[:-3]  # Segundos.milissegundos
        pid_str = f"0x{msg.can_id:03X}"  # PID = CAN ID
        data_str = " ".join([f"{b:02X}" for b in msg.data])
        ascii_str = msg.to_ascii()
        
        row = self.receive_table.rowCount()
        self.receive_table.insertRow(row)
        
        # Criar items com alinhamento
        id_item = QTableWidgetItem(str(row + 1))
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # IMPORTANTE: Armazenar o índice real em recorded_messages como UserRole
        # Isso permite mapear corretamente a linha da tabela para a mensagem
        msg_index = len(self.recorded_messages) - 1  # Índice da última mensagem adicionada
        id_item.setData(Qt.ItemDataRole.UserRole, msg_index)
        
        dlc_item = QTableWidgetItem(str(msg.dlc))
        dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # ID, Time, PID, DLC, Data, ASCII, Comment
        self.receive_table.setItem(row, 0, id_item)                          # ID sequencial
        self.receive_table.setItem(row, 1, QTableWidgetItem(time_str))      # Time
        self.receive_table.setItem(row, 2, QTableWidgetItem(pid_str))       # PID
        self.receive_table.setItem(row, 3, dlc_item)                        # DLC
        self.receive_table.setItem(row, 4, QTableWidgetItem(data_str))      # Data
        self.receive_table.setItem(row, 5, QTableWidgetItem(ascii_str))     # ASCII
        self.receive_table.setItem(row, 6, QTableWidgetItem(msg.comment))   # Comment
        
        # NO TRACER MODE: Sem highlight (deixar fluir sem azul)
        # Removido o código de highlight para que as mensagens fluam naturalmente
        
        # Auto-scroll
        self.receive_table.scrollToBottom()
    
    def add_message_monitor_mode(self, msg: CANMessage, highlight: bool = True):
        """Adiciona mensagem no modo Monitor (agrupa por ID)
        
        Args:
            msg: Mensagem CAN a ser adicionada
            highlight: Se True, destaca linha atualizada (para recepção em tempo real)
                      Se False, não destaca (para carregamento de logs)
        """
        # Verificar filtro
        if not self.message_passes_filter(msg):
            return
        
        pid_str = f"0x{msg.can_id:03X}"
        data_str = " ".join([f"{b:02X}" for b in msg.data])
        ascii_str = msg.to_ascii()
        
        # Incrementar contador
        self.message_counters[msg.can_id] += 1
        count = self.message_counters[msg.can_id]
        
        # Calcular period (tempo desde última mensagem deste ID)
        period_str = ""
        if msg.can_id in self.message_last_timestamp:
            period_ms = int((msg.timestamp - self.message_last_timestamp[msg.can_id]) * 1000)
            period_str = f"{period_ms}"
        
        # Atualizar timestamp da última mensagem deste ID
        self.message_last_timestamp[msg.can_id] = msg.timestamp
        
        # Procurar se já existe linha com esse PID
        existing_row = -1
        for row in range(self.receive_table.rowCount()):
            if self.receive_table.item(row, 2).text() == pid_str:  # Coluna 2 agora é PID
                existing_row = row
                break
        
        if existing_row >= 0:
            # Atualizar linha existente
            # Monitor: ID, Count, PID, DLC, Data, Period, ASCII, Comment
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # Centralizar Count
            self.receive_table.setItem(existing_row, 1, count_item)                     # Count
            self.receive_table.setItem(existing_row, 4, QTableWidgetItem(data_str))     # Data
            self.receive_table.setItem(existing_row, 5, QTableWidgetItem(period_str))   # Period
            self.receive_table.setItem(existing_row, 6, QTableWidgetItem(ascii_str))    # ASCII
            
            # NO MONITOR MODE: Destacar APENAS a célula Count em azul claro quando count > 1
            if highlight and count > 1:
                count_item.setBackground(self.colors['highlight'])
            else:
                # Manter cor normal se count == 1
                count_item.setBackground(self.colors['normal_bg'])
                
            # Limpar background das outras células (caso tenham sido destacadas antes)
            for col in range(self.receive_table.columnCount()):
                if col == 1:  # Pular a coluna Count
                    continue
                item = self.receive_table.item(existing_row, col)
                if item:
                    item.setBackground(self.colors['normal_bg'])
        else:
            # Adicionar nova linha NA POSIÇÃO CORRETA (ordenado por PID)
            # Monitor: ID, Count, PID, DLC, Data, Period, ASCII, Comment
            
            # Encontrar posição correta para inserir (mantendo ordem por PID)
            insert_row = self.receive_table.rowCount()  # Por padrão, inserir no final
            
            for row in range(self.receive_table.rowCount()):
                existing_pid_item = self.receive_table.item(row, 2)
                if existing_pid_item:
                    existing_pid_str = existing_pid_item.text()
                    # Comparar PIDs (remover "0x" e converter para int)
                    try:
                        existing_pid = int(existing_pid_str.replace("0x", ""), 16)
                        if msg.can_id < existing_pid:
                            insert_row = row
                            break
                    except ValueError:
                        continue
            
            self.receive_table.insertRow(insert_row)
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
            
            # Inserir items - Monitor: ID, Count, PID, DLC, Data, Period, ASCII, Comment
            self.receive_table.setItem(row, 0, id_item)                            # ID sequencial
            self.receive_table.setItem(row, 1, count_item)                         # Count
            self.receive_table.setItem(row, 2, QTableWidgetItem(pid_str))          # PID
            self.receive_table.setItem(row, 3, dlc_item)                           # DLC
            self.receive_table.setItem(row, 4, QTableWidgetItem(data_str))         # Data
            self.receive_table.setItem(row, 5, period_item)                        # Period
            self.receive_table.setItem(row, 6, QTableWidgetItem(ascii_str))        # ASCII
            self.receive_table.setItem(row, 7, QTableWidgetItem(msg.comment))      # Comment
            
            # NÃO destacar na primeira mensagem (count == 1), manter cor normal
            # Highlight só deve aparecer quando count > 1 (mensagem repetida)
            count_item.setBackground(self.colors['normal_bg'])
            
            # Recalcular IDs sequenciais de todas as linhas (pois a ordem mudou)
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
        """Obtém bytes de dados dos campos individuais"""
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
        # Limpar espaços e converter
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
        """Obtém dados de uma mensagem da tabela de transmissão"""
        # Colunas: ID(0), DLC(1), RTR(2), Period(3), TX Mode(4), Trigger ID(5), Trigger Data(6), D0-D7(7-14), Count(15), Comment(16)
        
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
            'data': data
        }
    
    def send_single(self):
        """Envia uma única mensagem"""
        try:
            can_id = int(self.tx_id_input.text(), 16)
            dlc = self.tx_dlc_input.value()
            data = self.get_data_from_bytes()
            
            if self.can_bus:
                message = can.Message(
                    arbitration_id=can_id,
                    data=data[:dlc],
                    is_extended_id=self.tx_29bit_check.isChecked(),
                    is_remote_frame=self.tx_rtr_check.isChecked()
                )
                self.can_bus.send(message)
                self.logger.info(f"Transmit: Enviado 0x{can_id:03X} - {data.hex()}")
                
                # Se estamos editando uma linha, incrementar o contador dela
                if self.editing_tx_row >= 0 and self.editing_tx_row < self.transmit_table.rowCount():
                    count_item = self.transmit_table.item(self.editing_tx_row, 15)
                    if count_item:
                        current_count = int(count_item.text()) if count_item.text().isdigit() else 0
                        count_item.setText(str(current_count + 1))
                    else:
                        # Criar item se não existir
                        new_item = QTableWidgetItem("1")
                        new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.transmit_table.setItem(self.editing_tx_row, 15, new_item)
                        self.transmit_table.setItem(self.editing_tx_row, 15, new_item)
                
                # Sem popup - apenas notificação discreta
                self.show_notification(t('notif_message_sent', id=can_id), 1000)
            else:
                self.show_notification(t('notif_simulation_sent', id=can_id), 2000)
        except Exception as e:
            self.logger.error(f"Erro ao enviar: {e}")
            self.show_notification(t('notif_error', error=str(e)), 3000)
    
    def clear_tx_fields(self):
        """Limpa todos os campos de edição de transmissão"""
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
        # Atualizar botão para "Add"
        self.btn_add.setText("Add")
    
    def add_tx_message(self):
        """Adiciona ou atualiza mensagem na lista de transmissão"""
        try:
            # Verificar se estamos editando uma linha existente ou adicionando nova
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
            
            # Resetar estado de edição
            self.editing_tx_row = -1
            self.clear_tx_fields()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Erro ao adicionar: {str(e)}")
    
    def load_tx_message_to_edit(self, item=None):
        """Carrega mensagem da tabela para os campos de edição (double-click ou copy)"""
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
                
                # Definir que estamos editando esta linha
                self.editing_tx_row = current_row
                
                # Mudar botão para "Save"
                self.btn_add.setText("Save")
                
            except Exception as e:
                self.logger.error(f"Erro ao carregar mensagem: {e}")
    
    def delete_tx_message(self):
        """Remove mensagem da lista"""
        current_row = self.transmit_table.currentRow()
        if current_row >= 0:
            self.transmit_table.removeRow(current_row)
    
    def send_all(self):
        """Inicia envio periódico de todas as mensagens da tabela de transmissão"""
        if not self.connected or not self.can_bus:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        if self.periodic_send_active:
            self.show_notification(t('notif_periodic_already_active'), 2000)
            return
        
        # Verificar se há mensagens na tabela
        if self.transmit_table.rowCount() == 0:
            self.show_notification(t('notif_no_messages_in_table'), 2000)
            return
        
        self.periodic_send_active = True
        
        # Iniciar thread para cada mensagem com período > 0
        messages_started = 0
        for row in range(self.transmit_table.rowCount()):
            try:
                # Obter dados da linha usando função auxiliar
                msg_data = self.get_tx_message_data_from_table(row)
                
                # Verificar se tem período configurado
                if msg_data['period'] == "off" or msg_data['period'] == "0":
                    continue
                
                # Parse do período (em ms)
                try:
                    period_ms = int(msg_data['period'])
                    if period_ms <= 0:
                        continue
                except ValueError:
                    continue
                
                # Criar evento de parada para esta thread
                stop_event = threading.Event()
                self.periodic_send_stop_events[row] = stop_event
                
                # Criar e iniciar thread de envio periódico
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
            # Transformar botão Send All em Stop All
            self.btn_send_all.setText("Stop All")
            self.btn_send_all.setStyleSheet(self.colors['send_active'])
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.stop_all)
        else:
            self.periodic_send_active = False
            self.show_notification(t('notif_no_valid_period'), 2000)
    
    def stop_all(self):
        """Para todas as transmissões periódicas"""
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
        
        # Limpar estruturas
        self.periodic_send_threads.clear()
        self.periodic_send_stop_events.clear()
        self.periodic_send_active = False
        
        # Reverter botão Stop All para Send All
        self.btn_send_all.setText("Send All")
        self.btn_send_all.setStyleSheet("")
        self.btn_send_all.clicked.disconnect()
        self.btn_send_all.clicked.connect(self.send_all)
        
        self.show_notification(t('notif_periodic_stopped'), 2000)
        self.logger.info("Periodic Send: Todas as transmissões periódicas foram paradas")
    
    def _periodic_send_worker(self, row: int, can_id: int, dlc: int, data: bytes, period_ms: int, stop_event: threading.Event, is_rtr: bool = False):
        """Worker thread para envio periódico de uma mensagem"""
        period_sec = period_ms / 1000.0
        
        try:
            while not stop_event.is_set():
                try:
                    # Enviar mensagem
                    if self.can_bus:
                        # Garantir que data tenha o tamanho correto (dlc bytes)
                        data_to_send = data[:dlc] if len(data) >= dlc else data + b'\x00' * (dlc - len(data))
                        
                        can_msg = can.Message(
                            arbitration_id=can_id,
                            data=data_to_send,
                            is_extended_id=(can_id > 0x7FF),
                            is_remote_frame=is_rtr
                        )
                        self.can_bus.send(can_msg)
                        
                        # Incrementar contador na tabela (thread-safe via QTimer)
                        # Usar functools.partial para garantir captura correta do valor
                        QTimer.singleShot(0, partial(self._increment_tx_count, row))
                        
                except Exception as e:
                    self.logger.error(f"Erro ao enviar mensagem periódica 0x{can_id:03X}: {e}")
                
                # Aguardar período ou até stop_event ser setado
                stop_event.wait(period_sec)
                
        except Exception as e:
            self.logger.error(f"Erro no worker de envio periódico (row {row}): {e}")
    
    def _increment_tx_count(self, row: int):
        """Incrementa o contador de transmissão na tabela (deve ser chamado na thread principal)"""
        try:
            if row < self.transmit_table.rowCount():
                # Coluna 15 é Count na nova estrutura
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    # Incrementar contador existente
                    try:
                        current_count = int(count_item.text())
                        count_item.setText(str(current_count + 1))
                    except ValueError:
                        count_item.setText("1")
                else:
                    # Criar item se não existir
                    new_item = QTableWidgetItem("1")
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 15, new_item)
        except Exception as e:
            self.logger.error(f"Erro ao incrementar contador: {e}")
    
    def _update_tx_count(self, row: int, count: int):
        """Atualiza o contador de transmissão na tabela (deve ser chamado na thread principal)"""
        try:
            if row < self.transmit_table.rowCount():
                # Coluna 15 é Count na nova estrutura
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    count_item.setText(str(count))
                else:
                    # Criar item se não existir
                    new_item = QTableWidgetItem(str(count))
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 15, new_item)
        except Exception as e:
            self.logger.error(f"Erro ao atualizar contador: {e}")
    
    def show_settings(self):
        """Mostra janela de configurações"""
        try:
            self.logger.info("Abrindo dialog de configurações")
            dialog = SettingsDialog(self, self.config, self.usb_monitor)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_config = dialog.get_config()
                self.logger.info(f"Configurações atualizadas: {new_config}")
                
                # Verificar se mudou o idioma
                old_language = self.config.get('language', 'en')
                new_language = new_config.get('language', 'en')
                
                # Verificar se mudou o tema
                old_theme = self.config.get('theme', 'system')
                new_theme = new_config.get('theme', 'system')
                
                # Verificar se mudou listen_only
                old_listen_only = self.config.get('listen_only', True)
                new_listen_only = new_config.get('listen_only', True)
                
                # Atualizar configuração local E salvar em arquivo
                self.config.update(new_config)
                self.config_manager.update(new_config)
                self.logger.info("Configuração salva em config.json")
                
                # Aplicar mudança de idioma
                language_changed = False
                if old_language != new_language:
                    from .i18n import get_i18n
                    i18n = get_i18n()
                    i18n.set_language(new_language)
                    self.logger.info(f"Idioma alterado para: {new_language}")
                    
                    # Atualizar interface com novo idioma
                    self.update_ui_translations()
                    language_changed = True
                
                # Aplicar mudança de tema
                theme_changed = False
                if old_theme != new_theme:
                    self.logger.info(f"Tema alterado para: {new_theme}")
                    # Aplicar tema imediatamente
                    self.apply_theme(new_theme)
                    theme_changed = True
                
                # Atualizar label de modo se conectado ou sempre atualizar
                if self.config.get('listen_only', True):
                    self.mode_label.setText(t('status_listen_only'))
                else:
                    self.mode_label.setText(t('status_normal'))
                
                if old_listen_only != new_listen_only:
                    self.logger.info(f"Modo alterado para: {'Listen Only' if new_listen_only else 'Normal'}")
                
                # Mostrar notificação no canto inferior direito
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
        """Muda o idioma da aplicação"""
        try:
            old_language = self.config.get('language', 'en')
            
            if old_language == language_code:
                return  # Já está no idioma selecionado
            
            # Atualizar configuração
            self.config['language'] = language_code
            self.config_manager.update(self.config)
            
            # Aplicar mudança de idioma
            from .i18n import get_i18n
            i18n = get_i18n()
            i18n.set_language(language_code)
            self.logger.info(f"Idioma alterado para: {language_code}")
            
            # Atualizar interface com novo idioma
            self.update_ui_translations()
            
            # Mostrar notificação
            lang_name = {"en": "English", "pt": "Português", "es": "Español", "de": "Deutsch", "fr": "Français"}.get(language_code, language_code)
            self.show_notification(t('notif_language_changed', language=lang_name), 3000)
            
        except Exception as e:
            self.logger.error(f"Erro ao mudar idioma: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Language Error", f"Erro ao mudar idioma: {str(e)}")
    
    def show_filters(self):
        """Mostra configuração de filtros"""
        QMessageBox.information(self, "Filters", "Filtros em desenvolvimento")
    
    def show_statistics(self):
        """Mostra estatísticas"""
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
                stats_text += f"  0x{can_id:03X}: {count} mensagens\n"
        
        QMessageBox.information(self, "Statistics", stats_text)
    
    def show_about(self):
        """Mostra informações sobre o aplicativo"""
        import sys
        import platform
        from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        
        python_version = sys.version.split()[0]
        qt_version = QT_VERSION_STR
        pyqt_version = PYQT_VERSION_STR
        os_info = platform.platform()
        
        about_text = f"""
        <h2>CAN Analyzer - macOS</h2>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Build:</b> 2026.01</p>
        
        <h3>Description:</h3>
        <p>Professional CAN bus analyzer for macOS with advanced monitoring,<br>
        recording, and transmission capabilities.</p>
        
        <h3>Key Features:</h3>
        <ul>
            <li><b>Monitor Mode</b> - Real-time CAN message monitoring</li>
            <li><b>Tracer Mode</b> - Record and playback CAN sessions</li>
            <li><b>Transmit</b> - Send CAN messages with periodic transmission</li>
            <li><b>Bit Field Viewer</b> - Detailed binary analysis</li>
            <li><b>Software Filters</b> - ID-based message filtering</li>
            <li><b>Trigger System</b> - Event-based message transmission</li>
            <li><b>Multiple Formats</b> - Save/Load in JSON, CSV, TRC</li>
            <li><b>Listen Only Mode</b> - Non-intrusive monitoring</li>
        </ul>
        
        <h3>System Information:</h3>
        <p><b>Python:</b> {python_version}<br>
        <b>Qt:</b> {qt_version}<br>
        <b>PyQt:</b> {pyqt_version}<br>
        <b>Platform:</b> {os_info}</p>
        
        <h3>Technology Stack:</h3>
        <p>Built with Python, PyQt6, and python-can library</p>
        
        <p><b>Copyright © 2026</b><br>
        All rights reserved.</p>
        """
        QMessageBox.about(self, "About CAN Analyzer", about_text)
    
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
                
                # No modo Tracer, salvar apenas mensagens gravadas (recorded_messages)
                # No modo Monitor, salvar todas as mensagens recebidas
                messages_to_save = self.recorded_messages if self.tracer_mode else self.received_messages
                
                # Determinar formato pelo extensão
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
                
                # Mostrar notificação
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
        """Salva log em formato JSON"""
        data = {
            'version': '1.0',
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
            writer.writerow(['Timestamp', 'ID', 'DLC', 'Data', 'Comment'])
            for msg in messages:
                writer.writerow([
                    msg.timestamp,
                    f"0x{msg.can_id:03X}",
                    msg.dlc,
                    msg.to_hex_string(),
                    msg.comment
                ])
    
    def _save_log_trace(self, filename: str, messages: List[CANMessage]):
        """Salva log em formato Trace (compatível com CANHacker)"""
        with open(filename, 'w') as f:
            f.write(f"; CAN Trace File\n")
            f.write(f"; Generated by CAN Analyzer - macOS\n")
            f.write(f"; Mode: {'Tracer' if self.tracer_mode else 'Monitor'}\n")
            f.write(f"; Baudrate: {self.config['baudrate']} bps\n")
            f.write(f"; Messages: {len(messages)}\n")
            f.write(f";\n")
            
            for msg in messages:
                # Formato: timestamp id dlc data
                f.write(f"{msg.timestamp:.6f} {msg.can_id:03X} {msg.dlc} {msg.data.hex()}\n")
    
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
                
                # Se não estiver em modo Tracer, mudar automaticamente
                if not self.tracer_mode:
                    self.logger.info("Load Log: Mudando para modo Tracer")
                    self.toggle_tracer_mode()
                    self.logger.info(f"Load Log: Após toggle - tracer_mode={self.tracer_mode}")
                
                self.clear_receive()
                self.message_counters.clear()
                
                # Determinar formato pelo extensão
                if filename.endswith('.csv'):
                    messages = self._load_log_csv(filename)
                elif filename.endswith('.trc'):
                    messages = self._load_log_trace(filename)
                else:
                    messages = self._load_log_json(filename)
                
                self.logger.info(f"Load Log: {len(messages)} mensagens carregadas")
                
                # SEMPRE adicionar ao Tracer, independente de estar conectado ou não
                # Load Trace deve sempre carregar no modo Tracer
                self.logger.info(f"Load Log: Adicionando ao Tracer - tracer_mode={self.tracer_mode}")
                
                for msg in messages:
                    # Adicionar às mensagens gravadas ANTES de exibir
                    self.recorded_messages.append(msg)
                    self.add_message_tracer_mode(msg)
                
                self.logger.info(f"Load Log: recorded_messages={len(self.recorded_messages)}")
                
                # Habilitar botões de reprodução se houver mensagens
                if len(self.recorded_messages) > 0:
                    self.btn_play_all.setEnabled(True)
                    self.btn_play_selected.setEnabled(True)
                    self.logger.info("Load Log: Botões Play habilitados")
                
                self.update_message_count()
                
                # Mostrar notificação
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_log_loaded', filename=filename_short, count=len(messages)),
                    5000
                )
            except Exception as e:
                self.logger.error(f"Erro ao carregar log: {e}", exc_info=True)
                QMessageBox.critical(self, "Load Error", f"Erro ao carregar: {str(e)}")
    
    def _load_log_json(self, filename: str) -> List[CANMessage]:
        """Carrega log de formato JSON"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Suportar formato antigo (lista) e novo (dict com metadata)
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
                count=item.get('count', 0)
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
                
                # Parse data (remover espaços)
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
                
                # Ignorar comentários
                if line.startswith(';') or not line:
                    continue
                
                # Parse: timestamp id dlc data
                parts = line.split()
                if len(parts) >= 4:
                    timestamp = float(parts[0])
                    can_id = int(parts[1], 16)
                    dlc = int(parts[2])
                    data = bytes.fromhex(parts[3])
                    
                    msg = CANMessage(
                        timestamp=timestamp,
                        can_id=can_id,
                        dlc=dlc,
                        data=data
                    )
                    messages.append(msg)
        
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
                
                # Salvar mensagens recebidas (Monitor)
                messages_to_save = self.received_messages
                
                # Determinar formato pelo extensão
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
                
                # Mostrar notificação
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
                
                # Determinar formato pelo extensão
                if filename.endswith('.csv'):
                    messages = self._load_log_csv(filename)
                elif filename.endswith('.trc'):
                    messages = self._load_log_trace(filename)
                else:
                    messages = self._load_log_json(filename)
                
                self.logger.info(f"Monitor log carregado: {len(messages)} mensagens")
                
                # Adicionar ao Monitor (received_messages)
                for msg in messages:
                    self.received_messages.append(msg)
                    self.add_message_monitor_mode(msg)
                
                self.update_message_count()
                
                # Mostrar notificação
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
        """Salva lista de mensagens de transmissão"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Transmit List",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                transmit_data = []
                
                # Percorrer todas as linhas da tabela de transmissão
                for row in range(self.transmit_table.rowCount()):
                    # Obter dados usando função auxiliar
                    msg_data = self.get_tx_message_data_from_table(row)
                    
                    # Obter outros campos
                    tx_mode_item = self.transmit_table.item(row, 4)
                    trigger_id_item = self.transmit_table.item(row, 5)
                    trigger_data_item = self.transmit_table.item(row, 6)
                    count_item = self.transmit_table.item(row, 15)
                    comment_item = self.transmit_table.item(row, 16)
                    
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
                        'comment': comment_item.text() if comment_item else ''
                    }
                    transmit_data.append(item_data)
                
                # Salvar com metadata
                data = {
                    'version': '1.0',
                    'transmit_messages': transmit_data
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Mostrar notificação
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_tx_saved', filename=filename_short, count=len(transmit_data)),
                    5000
                )
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Erro ao salvar: {str(e)}")
    
    def show_receive_context_menu(self, position):
        """Mostra menu de contexto na tabela de recepção"""
        # Verificar se há linhas selecionadas
        selected_rows = self.receive_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Criar menu
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        
        # Configurar menu para fechar ao clicar fora
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Ações do menu
        add_to_tx_action = QAction("➕ Add to Transmit", self)
        add_to_tx_action.triggered.connect(self.add_selected_to_transmit)
        menu.addAction(add_to_tx_action)
        
        copy_id_action = QAction("📋 Copy ID", self)
        copy_id_action.triggered.connect(self.copy_selected_id)
        menu.addAction(copy_id_action)
        
        copy_data_action = QAction("📋 Copy Data", self)
        copy_data_action.triggered.connect(self.copy_selected_data)
        menu.addAction(copy_data_action)
        
        menu.addSeparator()
        
        # Bit Field Viewer (apenas para uma mensagem selecionada)
        if len(selected_rows) == 1:
            bit_viewer_action = QAction("🔬 Bit Field Viewer", self)
            bit_viewer_action.triggered.connect(self.show_bit_field_viewer)
            menu.addAction(bit_viewer_action)
            menu.addSeparator()
        
        clear_selection_action = QAction("❌ Clear Selection", self)
        clear_selection_action.triggered.connect(self.receive_table.clearSelection)
        menu.addAction(clear_selection_action)
        
        # Mostrar menu na posição do cursor (exec é bloqueante e fecha automaticamente)
        menu.exec(self.receive_table.viewport().mapToGlobal(position))
    
    def show_transmit_context_menu(self, position):
        """Mostra menu de contexto na tabela de transmissão"""
        # Verificar se há linhas selecionadas
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Criar menu
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        
        # Configurar menu para fechar ao clicar fora
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Ações do menu
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
        
        # Mostrar menu na posição do cursor (exec é bloqueante e fecha automaticamente)
        menu.exec(self.transmit_table.viewport().mapToGlobal(position))
    
    def send_selected_tx_once(self):
        """Envia mensagens selecionadas da tabela de transmissão uma única vez"""
        if not self.connected or not self.can_bus:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        sent_count = 0
        for index in selected_rows:
            row = index.row()
            try:
                # Obter dados da linha usando função auxiliar
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
                self.can_bus.send(can_msg)
                sent_count += 1
                self.logger.info(f"Send Once: Enviado 0x{msg_data['can_id']:03X} DLC={msg_data['dlc']} Data={data_to_send.hex()}")
                
                # Incrementar contador na tabela
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    current_count = int(count_item.text()) if count_item.text().isdigit() else 0
                    count_item.setText(str(current_count + 1))
                else:
                    # Criar item se não existir
                    new_item = QTableWidgetItem("1")
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 15, new_item)
                
            except Exception as e:
                self.logger.error(f"Erro ao enviar mensagem da linha {row}: {e}")
        
        if sent_count > 0:
            self.show_notification(t('notif_messages_sent', count=sent_count), 2000)
    
    def start_selected_periodic(self):
        """Inicia envio periódico das mensagens selecionadas"""
        if not self.connected or not self.can_bus:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        self.periodic_send_active = True
        started_count = 0
        
        for index in selected_rows:
            row = index.row()
            
            # Verificar se já está rodando
            if row in self.periodic_send_threads:
                continue
            
            try:
                # Obter dados da linha usando função auxiliar
                msg_data = self.get_tx_message_data_from_table(row)
                
                # Verificar período
                if msg_data['period'] == "off" or msg_data['period'] == "0":
                    continue
                
                try:
                    period_ms = int(msg_data['period'])
                    if period_ms <= 0:
                        continue
                except ValueError:
                    continue
                
                # Criar evento de parada
                stop_event = threading.Event()
                self.periodic_send_stop_events[row] = stop_event
                
                # Criar e iniciar thread
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
            # Transformar botão Send All em Stop All
            self.btn_send_all.setText("Stop All")
            self.btn_send_all.setStyleSheet(self.colors['send_active'])
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.stop_all)
    
    def stop_selected_periodic(self):
        """Para envio periódico das mensagens selecionadas"""
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        stopped_count = 0
        for index in selected_rows:
            row = index.row()
            
            # Verificar se está rodando
            if row in self.periodic_send_stop_events:
                # Sinalizar para parar
                self.periodic_send_stop_events[row].set()
                
                # Aguardar thread finalizar
                if row in self.periodic_send_threads:
                    thread = self.periodic_send_threads[row]
                    if thread.is_alive():
                        thread.join(timeout=1.0)
                    del self.periodic_send_threads[row]
                
                del self.periodic_send_stop_events[row]
                stopped_count += 1
                
                # Resetar contador (coluna 15)
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    count_item.setText("0")
        
        # Se não há mais threads rodando, desativar flag e reverter botão
        if len(self.periodic_send_threads) == 0:
            self.periodic_send_active = False
            # Reverter botão Stop All para Send All
            self.btn_send_all.setText("Send All")
            self.btn_send_all.setStyleSheet("")
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.send_all)
        
        if stopped_count > 0:
            self.show_notification(t('notif_periodic_stopped_count', count=stopped_count), 2000)
    
    def delete_selected_tx_messages(self):
        """Deleta mensagens selecionadas da tabela de transmissão"""
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Ordenar em ordem decrescente para não afetar índices ao deletar
        rows_to_delete = sorted([index.row() for index in selected_rows], reverse=True)
        
        for row in rows_to_delete:
            # Se tiver envio periódico ativo, parar primeiro
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
    
    def add_selected_to_transmit(self):
        """Adiciona mensagens selecionadas à lista de transmissão"""
        selected_rows = self.receive_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        added_count = 0
        
        for index in selected_rows:
            row = index.row()
            
            try:
                # Extrair dados da linha selecionada
                if self.tracer_mode:
                    # Modo Tracer: ID, Time, PID, DLC, Data, ASCII, Comment
                    id_str = self.receive_table.item(row, 2).text()  # PID (coluna 2)
                    dlc_str = self.receive_table.item(row, 3).text()  # DLC (coluna 3)
                    data_str = self.receive_table.item(row, 4).text()  # Data (coluna 4)
                    comment_str = self.receive_table.item(row, 6).text() if self.receive_table.item(row, 6) else ""  # Comment
                else:
                    # Modo Monitor: ID, Count, PID, DLC, Data, Period, ASCII, Comment
                    id_str = self.receive_table.item(row, 2).text()  # PID (coluna 2)
                    dlc_str = self.receive_table.item(row, 3).text()  # DLC (coluna 3)
                    data_str = self.receive_table.item(row, 4).text()  # Data (coluna 4)
                    comment_str = self.receive_table.item(row, 7).text() if self.receive_table.item(row, 7) else ""  # Comment
                
                # Remover "0x" do ID se presente
                id_clean = id_str.replace("0x", "").replace("0X", "")
                dlc = int(dlc_str)
                
                # Adicionar à tabela de transmissão
                tx_row = self.transmit_table.rowCount()
                self.transmit_table.insertRow(tx_row)
                
                # Colunas: ID(0), DLC(1), RTR(2), Period(3), TX Mode(4), Trigger ID(5), Trigger Data(6), D0-D7(7-14), Count(15), Comment(16)
                
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
                
                added_count += 1
                
            except Exception as e:
                print(f"Erro ao adicionar linha {row}: {e}")
                continue
        
        if added_count > 0:
            # Mostrar mensagem na status bar ao invés de popup
            self.statusBar().showMessage(
                f"✅ {added_count} mensagem(ns) adicionada(s) à lista de transmissão!",
                3000  # 3 segundos
            )
    
    def copy_selected_id(self):
        """Copia ID da mensagem selecionada"""
        selected_rows = self.receive_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        if self.tracer_mode:
            id_str = self.receive_table.item(row, 2).text()  # PID (coluna 2) no Tracer
        else:
            id_str = self.receive_table.item(row, 2).text()  # PID (coluna 2) no Monitor
        
        # Copiar para clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(id_str)
        
        self.show_notification(t('notif_id_copied', id=id_str), 2000)
    
    def copy_selected_data(self):
        """Copia dados da mensagem selecionada"""
        selected_rows = self.receive_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        if self.tracer_mode:
            data_str = self.receive_table.item(row, 4).text()  # Data (coluna 4) no Tracer
        else:
            data_str = self.receive_table.item(row, 4).text()  # Data (coluna 4) no Monitor
        
        # Copiar para clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(data_str)
        
        self.show_notification(t('notif_data_copied', data=data_str), 2000)
    
    def load_transmit_list(self):
        """Carrega lista de mensagens de transmissão"""
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
                
                # Suportar formato antigo (lista) e novo (dict com metadata)
                if isinstance(data, list):
                    transmit_data = data
                else:
                    transmit_data = data.get('transmit_messages', [])
                
                # Limpar tabela atual (perguntar apenas se não estiver vazia)
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
                    # Lista vazia, não precisa perguntar
                    self.transmit_table.setRowCount(0)
                
                # Adicionar mensagens à tabela
                for item in transmit_data:
                    row = self.transmit_table.rowCount()
                    self.transmit_table.insertRow(row)
                    
                    # Colunas: ID(0), DLC(1), RTR(2), Period(3), TX Mode(4), Trigger ID(5), Trigger Data(6), D0-D7(7-14), Count(15), Comment(16)
                    
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
                
                # Mostrar notificação
                import os
                filename_short = os.path.basename(filename)
                self.show_notification(
                    t('notif_tx_loaded', filename=filename_short, count=len(transmit_data)),
                    5000
                )
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Erro ao carregar: {str(e)}")
    
    def toggle_playback_pause(self):
        """Pausa ou continua a reprodução"""
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
        """Destaca a linha atual durante reprodução"""
        try:
            # Limpar highlight anterior
            if self.current_playback_row >= 0 and self.current_playback_row < self.receive_table.rowCount():
                for col in range(self.receive_table.columnCount()):
                    item = self.receive_table.item(self.current_playback_row, col)
                    if item:
                        item.setBackground(self.colors['normal_bg'])
            
            # Aplicar novo highlight
            self.current_playback_row = row
            if row >= 0 and row < self.receive_table.rowCount():
                for col in range(self.receive_table.columnCount()):
                    item = self.receive_table.item(row, col)
                    if item:
                        item.setBackground(self.colors['highlight'])
                
                # Scroll para a linha atual
                first_item = self.receive_table.item(row, 0)
                if first_item:
                    self.receive_table.scrollToItem(first_item)
        except Exception as e:
            print(f"Erro ao destacar linha {row}: {e}")
    
    def clear_playback_highlight(self):
        """Limpa o highlight de reprodução"""
        if self.current_playback_row >= 0 and self.current_playback_row < self.receive_table.rowCount():
            for col in range(self.receive_table.columnCount()):
                item = self.receive_table.item(self.current_playback_row, col)
                if item:
                    item.setBackground(self.colors['normal_bg'])
        self.current_playback_row = -1
    
    def play_all_messages(self):
        """Reproduz (envia) todas as mensagens gravadas ou pausa/continua"""
        # Se já está reproduzindo, pausar/continuar
        if self.playback_active:
            self.toggle_playback_pause()
            return
        
        if not self.recorded_messages:
            QMessageBox.warning(self, "Playback", "Nenhuma mensagem gravada!\n\nClique em 'Record' para gravar mensagens primeiro.")
            return
        
        if not self.connected or not self.can_bus:
            QMessageBox.warning(self, "Playback", "Conecte-se ao barramento CAN primeiro!")
            return
        
        self.logger.log_playback("iniciado (Play All)", len(self.recorded_messages))
        
        # Parar reprodução anterior se existir
        self.stop_playback()
        
        # Iniciar reprodução em thread separada
        self.playback_active = True
        self.playback_stop_event.clear()
        self.playback_thread = threading.Thread(target=self._playback_worker, args=(self.recorded_messages,))
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        # Atualizar UI
        self.btn_play_all.setText("⏸ Pause")
        self.btn_play_selected.setEnabled(False)
        self.btn_stop_play.setEnabled(True)
        self.playback_label.setText("Playing...")
        self.show_notification(t('notif_playback_playing', count=len(self.recorded_messages)), 3000)
    
    def play_selected_message(self):
        """Reproduz (envia) apenas as mensagens selecionadas"""
        selected_rows = self.receive_table.selectionModel().selectedRows()
        
        if not selected_rows:
            return  # Sem popup, apenas retorna
        
        if not self.connected or not self.can_bus:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        # Obter mensagens selecionadas
        # No Tracer: usar índice armazenado no UserRole
        # Se não tiver UserRole, usar o PID da linha diretamente
        selected_messages = []
        
        for index in selected_rows:
            row = index.row()
            msg_added = False
            
            # Tentar obter pelo UserRole primeiro (Tracer com Record)
            id_item = self.receive_table.item(row, 0)
            if id_item:
                msg_index = id_item.data(Qt.ItemDataRole.UserRole)
                self.logger.info(f"Play Selected: Linha {row}, UserRole={msg_index}, recorded_messages={len(self.recorded_messages)}")
                
                if msg_index is not None and msg_index < len(self.recorded_messages):
                    msg = self.recorded_messages[msg_index]
                    selected_messages.append(msg)
                    msg_added = True
                    self.logger.info(f"Play Selected: Usando UserRole - 0x{msg.can_id:03X}")
            
            # Fallback: criar mensagem a partir dos dados da linha (se não conseguiu pelo UserRole)
            if not msg_added:
                pid_item = self.receive_table.item(row, 2)  # Coluna PID
                dlc_item = self.receive_table.item(row, 3)  # Coluna DLC
                data_item = self.receive_table.item(row, 4)  # Coluna Data
                
                if pid_item and dlc_item and data_item:
                    try:
                        # Parse PID (remover 0x)
                        pid_str = pid_item.text().replace('0x', '')
                        can_id = int(pid_str, 16)
                        
                        # Parse DLC
                        dlc = int(dlc_item.text())
                        
                        # Parse Data (remover espaços e converter)
                        data_str = data_item.text().replace(' ', '')
                        data = bytes.fromhex(data_str) if data_str else b''
                        
                        self.logger.info(f"Play Selected Fallback: PID={pid_str}, DLC={dlc}, Data='{data_str}' -> bytes={data.hex()}")
                        
                        # Criar mensagem temporária
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
        
        # Enviar mensagens imediatamente, sem validações extras
        try:
            for msg in selected_messages:
                can_msg = can.Message(
                    arbitration_id=msg.can_id,
                    data=msg.data,
                    is_extended_id=(msg.can_id > 0x7FF)
                )
                self.can_bus.send(can_msg)
                self.logger.info(f"Play Selected: Enviado 0x{msg.can_id:03X} - {msg.data.hex()}")
            
            # Sem popup, apenas notificação discreta
            # self.show_notification(f"✅ {len(selected_messages)} msg enviada(s)", 1000)
        except Exception as e:
            self.logger.error(f"Erro ao enviar mensagens: {e}")
            self.show_notification(t('notif_error', error=str(e)), 3000)
    
    def stop_playback(self):
        """Para a reprodução de mensagens"""
        if self.playback_active:
            self.playback_stop_event.set()
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=2.0)
            self.playback_active = False
            self.playback_paused = False
        
        # Limpar highlight
        self.clear_playback_highlight()
        
        # Atualizar UI - só habilitar se houver mensagens gravadas
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
            
            # Primeira mensagem como referência de tempo
            first_timestamp = messages[0].timestamp
            start_time = time.time()
            
            for i, msg in enumerate(messages):
                # Verificar se deve parar
                if self.playback_stop_event.is_set():
                    self.logger.info(f"Playback Worker: Parado pelo usuário na mensagem {i+1}/{len(messages)}")
                    break
                
                # Verificar se está pausado
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
                        # Aguardar até o momento correto, verificando stop_event
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
                    self.can_bus.send(can_msg)
                    self.logger.info(f"Playback: [{i+1}/{len(messages)}] Enviado 0x{msg.can_id:03X} - {msg.data.hex()}")
                    
                    # Atualizar progresso na UI thread
                    progress = f"Playing {i+1}/{len(messages)}"
                    QTimer.singleShot(0, lambda p=progress: self.playback_label.setText(p))
                    
                except Exception as e:
                    self.logger.error(f"Erro ao enviar mensagem {i+1}: {e}")
            
            self.logger.info(f"Playback Worker: Finalizado - {i+1}/{len(messages)} mensagens processadas")
            
            # Limpar highlight e finalizar reprodução
            QTimer.singleShot(0, self.clear_playback_highlight)
            QTimer.singleShot(0, self.stop_playback)
            
        except Exception as e:
            self.logger.error(f"Erro no playback worker: {e}")
            QTimer.singleShot(0, self.clear_playback_highlight)
            QTimer.singleShot(0, self.stop_playback)
    
    def show_bit_field_viewer(self):
        """Mostra o Bit Field Viewer para a mensagem selecionada"""
        selected_rows = self.receive_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Obter mensagem correspondente
        if row < len(self.received_messages):
            message = self.received_messages[row]
            
            # Criar e mostrar dialog
            dialog = BitFieldViewerDialog(self, message)
            dialog.show()
        else:
            QMessageBox.warning(self, "Bit Field Viewer", "Mensagem não encontrada!")
    
    def show_filter_dialog(self):
        """Mostra dialog de configuração de filtros"""
        dialog = FilterDialog(self, self.message_filters)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Atualizar filtros
            self.message_filters = dialog.get_filters()
            
            # Aplicar filtros imediatamente
            self.apply_message_filters()
            
            # Mostrar notificação sobre filtros
            if self.message_filters['enabled']:
                filter_count = len(self.message_filters['id_filters'])
                self.show_notification(
                    t('notif_filters_enabled', count=filter_count),
                    3000
                )
            else:
                self.show_notification(t('notif_filters_disabled'), 2000)
    
    def show_trigger_dialog(self):
        """Mostra dialog de configuração de triggers"""
        from PyQt6.QtWidgets import QDialog
        
        self.logger.info("Abrindo dialog de triggers")
        
        dialog = TriggerDialog(self, self.triggers)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Atualizar triggers
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
        """Aplica filtros às mensagens exibidas"""
        if not self.message_filters['enabled']:
            # Se filtros desabilitados, mostrar todas as linhas
            for row in range(self.receive_table.rowCount()):
                self.receive_table.setRowHidden(row, False)
            return
        
        id_filters = self.message_filters['id_filters']
        show_only = self.message_filters['show_only']
        
        # Aplicar filtro de ID
        for row in range(self.receive_table.rowCount()):
            try:
                # Obter PID da linha
                if self.tracer_mode:
                    id_item = self.receive_table.item(row, 2)  # Coluna PID no Tracer (coluna 2)
                else:
                    id_item = self.receive_table.item(row, 2)  # Coluna PID no Monitor (coluna 2)
                
                if not id_item:
                    continue
                
                id_str = id_item.text().replace("0x", "").replace("0X", "")
                msg_id = int(id_str, 16)
                
                # Aplicar lógica de filtro
                if show_only:
                    # Whitelist: mostrar apenas IDs na lista
                    should_hide = msg_id not in id_filters if id_filters else False
                else:
                    # Blacklist: ocultar IDs na lista
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
                
                # Verificar se ID corresponde
                if msg.can_id != trigger_id:
                    continue
                
                # Verificar dados (se especificado)
                trigger_data = trigger.get('trigger_data', '')
                if trigger_data and trigger_data != 'Any':
                    # Parse trigger data
                    trigger_bytes = bytes.fromhex(trigger_data.replace(' ', ''))
                    # Comparar apenas os bytes especificados
                    if len(trigger_bytes) > 0:
                        if msg.data[:len(trigger_bytes)] != trigger_bytes:
                            continue
                
                # Trigger matched! Enviar mensagem TX
                tx_id_str = trigger.get('tx_id', '0x000').replace('0x', '').replace('0X', '')
                tx_id = int(tx_id_str, 16)
                
                tx_data_str = trigger.get('tx_data', '00 00 00 00 00 00 00 00').replace(' ', '')
                tx_data = bytes.fromhex(tx_data_str)
                
                # Log do trigger
                comment = trigger.get('comment', '')
                self.logger.log_trigger(trigger_id, tx_id, comment)
                
                # Enviar mensagem
                if CAN_AVAILABLE and self.can_bus:
                    can_msg = can.Message(
                        arbitration_id=tx_id,
                        data=tx_data,
                        is_extended_id=(tx_id > 0x7FF)
                    )
                    self.can_bus.send(can_msg)
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
        
        # Filtro de ID
        if id_filters:
            id_match = msg.can_id in id_filters
            if show_only:
                # Whitelist: deve estar na lista
                if not id_match:
                    return False
            else:
                # Blacklist: não deve estar na lista
                if id_match:
                    return False
        
        # Filtro de dados
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
        """Callback chamado quando um dispositivo USB é conectado (thread segura)"""
        self.logger.info(f"Dispositivo USB conectado: {device}")
        
        # Mostrar notificação (thread segura)
        QTimer.singleShot(0, lambda: self.show_notification(
            f"🔌 {t('msg_device_connected').format(device=device.name)}",
            5000
        ))
    
    def on_usb_device_disconnected(self, device):
        """Callback chamado quando um dispositivo USB é desconectado (thread segura)"""
        self.logger.info(f"Dispositivo USB desconectado: {device}")
        
        # Verificar se o dispositivo desconectado é o que está em uso
        current_device = self.config.get('channel', '')
        if device.path == current_device:
            self.logger.warning(f"Dispositivo em uso foi desconectado: {device.path}")
            
            # Se estiver conectado, desconectar automaticamente
            if self.connected:
                self.logger.info("Desconectando automaticamente devido à remoção do dispositivo")
                
                # Executar na thread principal usando QTimer
                QTimer.singleShot(0, self._handle_device_disconnection)
        
        # Mostrar notificação (thread segura)
        QTimer.singleShot(0, lambda: self.show_notification(
            f"🔌 {t('msg_device_disconnected').format(device=device.name)}",
            5000
        ))
    
    def _handle_device_disconnection(self):
        """Manipula desconexão de dispositivo na thread principal"""
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
    
    def closeEvent(self, event):
        """Evento chamado ao fechar a janela"""
        # Parar o monitor USB
        if hasattr(self, 'usb_monitor'):
            self.usb_monitor.stop_monitoring()
        
        # Desconectar se estiver conectado
        if self.connected:
            self.disconnect()
        
        # Aceitar o evento de fechamento
        event.accept()


