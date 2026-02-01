"""
Dialogs - Janelas de diálogo da aplicação (versão refatorada)
"""

import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QScrollArea, QWidget, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from .models import CANMessage, CANConfig
from .utils import calculate_baudrate_divisor
from .i18n import get_i18n, t
from .theme import get_adaptive_colors, get_bit_style, should_use_dark_mode


class SettingsDialog(QDialog):
    """Dialog de configurações de conexão"""
    def __init__(self, parent=None, config=None, usb_monitor=None):
        super().__init__(parent)
        self.config = config or {}
        self.i18n = get_i18n()
        self.usb_monitor = usb_monitor
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(t('menu_connection_settings'))
        self.setModal(True)
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        
        # Get theme preference from config
        theme_pref = self.config.get('theme', 'system')
        colors = get_adaptive_colors(theme_pref)
        
        # General Settings
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout()
        
        # Timestamp checkbox
        self.timestamp_check = QCheckBox("Enable Timestamps")
        self.timestamp_check.setChecked(self.config.get('timestamp', True))
        self.timestamp_check.setToolTip("Add timestamp to received messages")
        general_layout.addWidget(self.timestamp_check)
        
        # Simulation Mode checkbox
        self.simulation_mode_check = QCheckBox(t('label_simulation_mode'))
        self.simulation_mode_check.setChecked(self.config.get('simulation_mode', False))
        self.simulation_mode_check.setToolTip(t('tooltip_simulation_mode'))
        general_layout.addWidget(self.simulation_mode_check)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # Language Selection
        language_group = QGroupBox(t('menu_language'))
        language_layout = QHBoxLayout()
        self.language_combo = QComboBox()
        
        # Add available languages
        for code, name in self.i18n.get_available_languages().items():
            self.language_combo.addItem(f"{name}", code)
        
        # Set current language
        current_lang = self.config.get('language', self.i18n.get_language())
        index = self.language_combo.findData(current_lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        
        language_layout.addWidget(self.language_combo)
        language_group.setLayout(language_layout)
        layout.addWidget(language_group)
        
        # Theme Selection
        theme_group = QGroupBox(t('theme_group'))
        theme_layout = QVBoxLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(t('theme_system'), "system")
        self.theme_combo.addItem(t('theme_light'), "light")
        self.theme_combo.addItem(t('theme_dark'), "dark")
        
        # Set current theme
        current_theme = self.config.get('theme', 'system')
        theme_index = self.theme_combo.findData(current_theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
        
        theme_layout.addWidget(self.theme_combo)
        
        # Info label
        theme_info = QLabel(t('theme_restart_info'))
        theme_info.setStyleSheet(colors['info_text'])
        theme_info.setWordWrap(True)
        theme_layout.addWidget(theme_info)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Multi-CAN Configuration
        multican_group = QGroupBox(t('multican_group'))
        multican_layout = QVBoxLayout()
        
        # Info label
        multican_info = QLabel(t('multican_info'))
        multican_info.setStyleSheet(colors['info_text'])
        multican_info.setWordWrap(True)
        multican_layout.addWidget(multican_info)
        
        # Scroll area for CAN bus widgets
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(250)
        
        scroll_widget = QWidget()
        self.can_buses_layout = QVBoxLayout(scroll_widget)
        self.can_buses_layout.setSpacing(10)
        
        # Store CAN bus widgets
        self.can_bus_widgets = []
        
        # Load existing CAN buses from config
        can_buses = self.config.get('can_buses', [])
        if not can_buses:
            # Default: single CAN bus with current settings
            can_buses = [{
                'name': 'CAN1',
                'channel': self.config.get('channel', 'can0'),
                'baudrate': self.config.get('baudrate', 500000),
                'listen_only': self.config.get('listen_only', True)
            }]
        
        for bus in can_buses:
            self._add_can_bus_widget(bus)
        
        self.can_buses_layout.addStretch()
        scroll.setWidget(scroll_widget)
        multican_layout.addWidget(scroll)
        
        # Buttons for add/remove
        can_buttons_layout = QHBoxLayout()
        self.btn_add_can = QPushButton(t('btn_add_can'))
        self.btn_add_can.clicked.connect(self._add_new_can_bus)
        can_buttons_layout.addWidget(self.btn_add_can)
        
        can_buttons_layout.addStretch()
        multican_layout.addLayout(can_buttons_layout)
        
        multican_group.setLayout(multican_layout)
        layout.addWidget(multican_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    
    def _add_can_bus_widget(self, bus_config):
        """Add a CAN bus configuration widget"""
        # Create widget container
        bus_widget = QGroupBox()
        bus_layout = QVBoxLayout()
        
        # Row 1: Name and Remove button
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(t('multican_name') + ":"))
        name_input = QLineEdit(bus_config.get('name', f'CAN{len(self.can_bus_widgets)+1}'))
        name_input.setMaximumWidth(150)
        row1.addWidget(name_input)
        row1.addStretch()
        
        # Remove button
        btn_remove = QPushButton(t('btn_remove_can'))
        btn_remove.setMaximumWidth(100)
        btn_remove.clicked.connect(lambda: self._remove_can_bus_widget(bus_widget))
        row1.addWidget(btn_remove)
        bus_layout.addLayout(row1)
        
        # Row 2: Device and Scan button
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(t('multican_device') + ":"))
        channel_input = QComboBox()
        channel_input.setEditable(True)
        
        # Add common devices based on platform
        import sys
        if sys.platform == "win32":
            channel_input.addItems(["COM1", "COM3", "COM4", "can0", "vcan0"])
        elif sys.platform == "linux":
            channel_input.addItems(["/dev/ttyUSB0", "/dev/ttyACM0", "can0", "vcan0"])
        else:
            channel_input.addItems(["/dev/cu.usbserial", "/dev/cu.usbmodem", "can0", "vcan0"])
        
        channel_input.setCurrentText(bus_config.get('channel', 'can0'))
        row2.addWidget(channel_input, 1)
        
        # Scan button
        btn_scan = QPushButton(t('btn_scan_devices'))
        btn_scan.setMaximumWidth(120)
        btn_scan.clicked.connect(lambda: self._scan_device_for_bus(channel_input))
        row2.addWidget(btn_scan)
        bus_layout.addLayout(row2)
        
        # Row 3: Baudrate and Listen Only
        row3 = QHBoxLayout()
        row3.addWidget(QLabel(t('multican_baudrate') + ":"))
        baudrate_combo = QComboBox()
        baudrate_combo.addItems(["125 Kbit/s", "250 Kbit/s", "500 Kbit/s", "1000 Kbit/s"])
        baudrate = bus_config.get('baudrate', 500000)
        baudrate_combo.setCurrentText(f"{baudrate//1000} Kbit/s")
        baudrate_combo.setMaximumWidth(150)
        row3.addWidget(baudrate_combo)
        
        row3.addStretch()
        
        # Listen Only checkbox
        listen_only_check = QCheckBox(t('multican_listen_only'))
        listen_only_check.setChecked(bus_config.get('listen_only', True))
        row3.addWidget(listen_only_check)
        bus_layout.addLayout(row3)
        
        # Row 4: Serial-specific settings (COM Baudrate, RTS HS)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("COM Baudrate:"))
        com_baudrate_combo = QComboBox()
        com_baudrate_combo.addItems([
            "9600 bit/s", "19200 bit/s", "38400 bit/s", 
            "57600 bit/s", "115200 bit/s"
        ])
        com_baudrate = bus_config.get('com_baudrate', '115200 bit/s')
        com_baudrate_combo.setCurrentText(com_baudrate)
        com_baudrate_combo.setMaximumWidth(150)
        com_baudrate_combo.setToolTip("Serial port baudrate (for SLCAN/USB devices)")
        row4.addWidget(com_baudrate_combo)
        
        row4.addStretch()
        
        # RTS HS checkbox
        rts_hs_check = QCheckBox("RTS HS")
        rts_hs_check.setChecked(bus_config.get('rts_hs', False))
        rts_hs_check.setToolTip("Request To Send Hardware Handshake (for serial devices)")
        row4.addWidget(rts_hs_check)
        bus_layout.addLayout(row4)
        
        # Info label for serial settings
        serial_info = QLabel("ℹ️ COM Baudrate and RTS HS only apply to serial/USB devices")
        serial_info.setStyleSheet("color: gray; font-size: 10px;")
        serial_info.setWordWrap(True)
        bus_layout.addWidget(serial_info)
        
        bus_widget.setLayout(bus_layout)
        
        # Store references to inputs
        bus_widget.name_input = name_input
        bus_widget.channel_input = channel_input
        bus_widget.baudrate_combo = baudrate_combo
        bus_widget.listen_only_check = listen_only_check
        bus_widget.com_baudrate_combo = com_baudrate_combo
        bus_widget.rts_hs_check = rts_hs_check
        
        # Add to layout and list
        self.can_buses_layout.insertWidget(len(self.can_bus_widgets), bus_widget)
        self.can_bus_widgets.append(bus_widget)
    
    def _add_new_can_bus(self):
        """Add a new CAN bus configuration"""
        new_bus = {
            'name': f'CAN{len(self.can_bus_widgets) + 1}',
            'channel': 'can0',
            'baudrate': 500000,
            'listen_only': True
        }
        self._add_can_bus_widget(new_bus)
    
    def _remove_can_bus_widget(self, widget):
        """Remove a CAN bus widget"""
        # Don't allow removing the last bus
        if len(self.can_bus_widgets) <= 1:
            QMessageBox.warning(self, t('warning'), t('multican_info'))
            return
        
        self.can_bus_widgets.remove(widget)
        self.can_buses_layout.removeWidget(widget)
        widget.deleteLater()
    
    def _scan_device_for_bus(self, channel_input):
        """Scan and select device for a specific CAN bus"""
        if not self.usb_monitor:
            QMessageBox.warning(self, t('warning'), t('msg_usb_monitor_not_available'))
            return
        
        dialog = USBDeviceSelectionDialog(self, self.usb_monitor)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            device = dialog.selected_device
            if device:
                channel_input.setCurrentText(device.path)
    
    def get_config(self):
        """Retorna configuração atualizada"""
        selected_language = self.language_combo.currentData()
        selected_theme = self.theme_combo.currentData()
        
        # Extract CAN buses from widgets
        can_buses = []
        for widget in self.can_bus_widgets:
            name = widget.name_input.text()
            channel = widget.channel_input.currentText()
            baudrate_text = widget.baudrate_combo.currentText()
            baudrate = int(baudrate_text.split()[0]) * 1000
            listen_only = widget.listen_only_check.isChecked()
            com_baudrate = widget.com_baudrate_combo.currentText()
            rts_hs = widget.rts_hs_check.isChecked()
            
            # Auto-detect interface based on channel
            channel_upper = channel.upper()
            if (channel.startswith('/dev/tty.') or channel.startswith('/dev/cu.') or
                    channel.startswith('/dev/ttyUSB') or channel.startswith('/dev/ttyACM') or
                    (channel_upper.startswith('COM') and len(channel) >= 4)):
                interface = 'slcan'
            elif channel.startswith('can') or channel.startswith('vcan'):
                interface = 'socketcan'
            else:
                interface = 'socketcan'  # default
            
            can_buses.append({
                'name': name,
                'channel': channel,
                'baudrate': baudrate,
                'interface': interface,
                'listen_only': listen_only,
                'com_baudrate': com_baudrate,
                'rts_hs': rts_hs
            })
        
        # Legacy compatibility: use first bus as default
        first_bus = can_buses[0] if can_buses else {
            'channel': 'can0',
            'baudrate': 500000,
            'listen_only': True
        }
        
        return {
            # Legacy fields (for backward compatibility)
            'channel': first_bus['channel'],
            'baudrate': first_bus['baudrate'],
            'listen_only': first_bus.get('listen_only', True),
            
            # New fields
            'timestamp': self.timestamp_check.isChecked(),
            'language': selected_language,
            'theme': selected_theme,
            'simulation_mode': self.simulation_mode_check.isChecked(),
            'can_buses': can_buses
        }


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
        
        # Header com informações da mensagem
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
        
        # Criar visualização de bits para cada byte
        if self.message:
            for byte_idx, byte_val in enumerate(self.message.data):
                byte_group = self.create_byte_viewer(byte_idx, byte_val)
                scroll_layout.addWidget(byte_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Botões
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
        """Cria visualização de um byte com seus 8 bits"""
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
        
        # Labels editáveis para cada bit
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


class FilterDialog(QDialog):
    """Dialog para configurar filtros de mensagens"""
    def __init__(self, parent=None, current_filters=None):
        super().__init__(parent)
        self.current_filters = current_filters or {
            'enabled': False,
            'id_filters': [],
            'data_filters': [],
            'show_only': True
        }
        # Get theme from parent's config if available
        self.theme_pref = 'system'
        if parent and hasattr(parent, 'theme_preference'):
            self.theme_pref = parent.theme_preference
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Message Filters")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Enable/Disable filters
        self.enable_check = QCheckBox("Enable Filters")
        self.enable_check.setChecked(self.current_filters.get('enabled', False))
        self.enable_check.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.enable_check)
        
        # Mode selection
        mode_group = QGroupBox("Filter Mode")
        mode_layout = QVBoxLayout()
        
        self.show_only_radio = QCheckBox("Show Only Matching (whitelist)")
        self.show_only_radio.setChecked(self.current_filters.get('show_only', True))
        mode_layout.addWidget(self.show_only_radio)
        
        self.hide_matching_radio = QCheckBox("Hide Matching (blacklist)")
        self.hide_matching_radio.setChecked(not self.current_filters.get('show_only', True))
        mode_layout.addWidget(self.hide_matching_radio)
        
        # Conectar para garantir que apenas um esteja marcado
        self.show_only_radio.stateChanged.connect(
            lambda: self.hide_matching_radio.setChecked(not self.show_only_radio.isChecked())
        )
        self.hide_matching_radio.stateChanged.connect(
            lambda: self.show_only_radio.setChecked(not self.hide_matching_radio.isChecked())
        )
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # ID Filters
        id_group = QGroupBox("ID Filters")
        id_layout = QVBoxLayout()
        
        colors = get_adaptive_colors(self.theme_pref)
        id_help = QLabel("Enter CAN IDs (hex) separated by commas or spaces\nExample: 0x280, 0x284, 0x300-0x310")
        id_help.setStyleSheet(colors['info_text'])
        id_layout.addWidget(id_help)
        
        self.id_filter_input = QLineEdit()
        self.id_filter_input.setPlaceholderText("0x280, 0x284, 0x300-0x310")
        # Carregar filtros existentes
        if self.current_filters.get('id_filters'):
            id_text = ", ".join([f"0x{id:03X}" for id in self.current_filters['id_filters']])
            self.id_filter_input.setText(id_text)
        id_layout.addWidget(self.id_filter_input)
        
        id_group.setLayout(id_layout)
        layout.addWidget(id_group)
        
        # Channel-specific ID Filters
        channel_group = QGroupBox("Channel-Specific ID Filters")
        channel_layout = QVBoxLayout()
        
        channel_help = QLabel("Filter IDs per channel (overrides global ID filters)\nLeave empty to use global filters")
        channel_help.setStyleSheet(colors['info_text'])
        channel_layout.addWidget(channel_help)
        
        # Scroll area for channel filters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        scroll_widget = QWidget()
        self.channel_filters_layout = QVBoxLayout(scroll_widget)
        
        # Get available channels from parent
        self.channel_filter_inputs = {}
        available_channels = ['ALL']  # ALL = applies to all channels
        parent_window = self.parent()
        if parent_window and hasattr(parent_window, 'can_bus_manager'):
            available_channels.extend(parent_window.can_bus_manager.get_bus_names())
        
        # Create input for each channel
        for channel in available_channels:
            channel_row = QHBoxLayout()
            channel_label = QLabel(f"{channel}:")
            channel_label.setMinimumWidth(80)
            channel_row.addWidget(channel_label)
            
            channel_input = QLineEdit()
            channel_input.setPlaceholderText("0x280, 0x284, 0x300-0x310")
            
            # Load existing filters
            channel_filters = self.current_filters.get('channel_filters', {})
            if channel in channel_filters:
                channel_ids = channel_filters[channel].get('ids', [])
                if channel_ids:
                    id_text = ", ".join([f"0x{id:03X}" for id in channel_ids])
                    channel_input.setText(id_text)
            
            channel_row.addWidget(channel_input)
            
            # Mode checkbox
            channel_mode = QCheckBox("Show Only")
            if channel in channel_filters:
                channel_mode.setChecked(channel_filters[channel].get('show_only', True))
            else:
                channel_mode.setChecked(True)
            channel_row.addWidget(channel_mode)
            
            self.channel_filters_layout.addLayout(channel_row)
            self.channel_filter_inputs[channel] = {'input': channel_input, 'mode': channel_mode}
        
        scroll.setWidget(scroll_widget)
        channel_layout.addWidget(scroll)
        
        channel_group.setLayout(channel_layout)
        layout.addWidget(channel_group)
        
        # Data Filters
        data_group = QGroupBox("Data Filters (Advanced)")
        data_layout = QVBoxLayout()
        
        data_help = QLabel("Filter by data content (hex)\nExample: Byte 0 = FF, Byte 2 = 00")
        data_help.setStyleSheet(colors['info_text'])
        data_layout.addWidget(data_help)
        
        self.data_filter_table = QTableWidget()
        self.data_filter_table.setColumnCount(3)
        self.data_filter_table.setHorizontalHeaderLabels(['Byte Index', 'Value (Hex)', 'Mask (Hex)'])
        self.data_filter_table.setMaximumHeight(150)
        data_layout.addWidget(self.data_filter_table)
        
        data_btn_layout = QHBoxLayout()
        self.btn_add_data_filter = QPushButton("+ Add Data Filter")
        self.btn_add_data_filter.clicked.connect(self.add_data_filter_row)
        data_btn_layout.addWidget(self.btn_add_data_filter)
        
        self.btn_remove_data_filter = QPushButton("- Remove Selected")
        self.btn_remove_data_filter.clicked.connect(self.remove_data_filter_row)
        data_btn_layout.addWidget(self.btn_remove_data_filter)
        data_btn_layout.addStretch()
        data_layout.addLayout(data_btn_layout)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # Quick filters
        quick_group = QGroupBox("Quick Filters")
        quick_layout = QHBoxLayout()
        
        self.btn_clear_filters = QPushButton("🗑 Clear All")
        self.btn_clear_filters.clicked.connect(self.clear_all_filters)
        quick_layout.addWidget(self.btn_clear_filters)
        
        quick_layout.addStretch()
        quick_group.setLayout(quick_layout)
        layout.addWidget(quick_group)
        
        layout.addStretch()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_filters)
        layout.addWidget(button_box)
        
        # Carregar filtros de dados existentes
        for data_filter in self.current_filters.get('data_filters', []):
            self.add_data_filter_row(data_filter)
    
    def add_data_filter_row(self, data=None):
        """Adiciona linha para filtro de dados"""
        row = self.data_filter_table.rowCount()
        self.data_filter_table.insertRow(row)
        
        if data:
            self.data_filter_table.setItem(row, 0, QTableWidgetItem(str(data.get('byte_index', 0))))
            self.data_filter_table.setItem(row, 1, QTableWidgetItem(data.get('value', 'FF')))
            self.data_filter_table.setItem(row, 2, QTableWidgetItem(data.get('mask', 'FF')))
        else:
            self.data_filter_table.setItem(row, 0, QTableWidgetItem("0"))
            self.data_filter_table.setItem(row, 1, QTableWidgetItem("FF"))
            self.data_filter_table.setItem(row, 2, QTableWidgetItem("FF"))
    
    def remove_data_filter_row(self):
        """Remove linha selecionada"""
        current_row = self.data_filter_table.currentRow()
        if current_row >= 0:
            self.data_filter_table.removeRow(current_row)
    
    def clear_all_filters(self):
        """Limpa todos os filtros"""
        self.id_filter_input.clear()
        self.data_filter_table.setRowCount(0)
        self.enable_check.setChecked(False)
    
    def apply_filters(self):
        """Aplica filtros sem fechar dialog"""
        pass
    
    def get_filters(self):
        """Retorna configuração de filtros"""
        # Parse ID filters
        id_filters = []
        id_text = self.id_filter_input.text().strip()
        if id_text:
            parts = id_text.replace(',', ' ').split()
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Range: 0x300-0x310
                    try:
                        start, end = part.split('-')
                        start_id = int(start.strip(), 16)
                        end_id = int(end.strip(), 16)
                        id_filters.extend(range(start_id, end_id + 1))
                    except:
                        pass
                else:
                    # Single ID
                    try:
                        id_filters.append(int(part, 16))
                    except:
                        pass
        
        # Parse channel-specific filters
        channel_filters = {}
        for channel, widgets in self.channel_filter_inputs.items():
            channel_text = widgets['input'].text().strip()
            if channel_text:
                channel_ids = []
                parts = channel_text.replace(',', ' ').split()
                for part in parts:
                    part = part.strip()
                    if '-' in part:
                        # Range: 0x300-0x310
                        try:
                            start, end = part.split('-')
                            start_id = int(start.strip(), 16)
                            end_id = int(end.strip(), 16)
                            channel_ids.extend(range(start_id, end_id + 1))
                        except:
                            pass
                    else:
                        # Single ID
                        try:
                            channel_ids.append(int(part, 16))
                        except:
                            pass
                
                if channel_ids:
                    channel_filters[channel] = {
                        'ids': channel_ids,
                        'show_only': widgets['mode'].isChecked()
                    }
        
        # Parse data filters
        data_filters = []
        for row in range(self.data_filter_table.rowCount()):
            try:
                byte_index = int(self.data_filter_table.item(row, 0).text())
                value = self.data_filter_table.item(row, 1).text()
                mask = self.data_filter_table.item(row, 2).text()
                data_filters.append({
                    'byte_index': byte_index,
                    'value': value,
                    'mask': mask
                })
            except:
                pass
        
        return {
            'enabled': self.enable_check.isChecked(),
            'id_filters': id_filters,
            'data_filters': data_filters,
            'show_only': self.show_only_radio.isChecked(),
            'channel_filters': channel_filters
        }


class TriggerDialog(QDialog):
    """Dialog para configurar triggers de transmissão automática"""
    def __init__(self, parent=None, triggers=None):
        super().__init__(parent)
        self.triggers = triggers or []
        # Get theme from parent's config if available
        theme_pref = 'system'
        if parent and hasattr(parent, 'theme_preference'):
            theme_pref = parent.theme_preference
        self.colors = get_adaptive_colors(theme_pref)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Trigger-based Transmission")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Info
        info_label = QLabel(
            "Configure automatic transmission based on received messages.\n"
            "When a trigger condition is met, the associated message is sent automatically."
        )
        info_label.setStyleSheet(f"{self.colors['info_text'].replace('10px', '11px')}; padding: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Enable triggers
        self.enable_check = QCheckBox("Enable Trigger-based Transmission")
        self.enable_check.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.enable_check)
        
        # Triggers table
        triggers_group = QGroupBox("Configured Triggers")
        triggers_layout = QVBoxLayout()
        
        self.triggers_table = QTableWidget()
        self.triggers_table.setColumnCount(6)
        self.triggers_table.setHorizontalHeaderLabels([
            'Enabled', 'Trigger ID', 'Trigger Data', 'TX ID', 'TX Data', 'Comment'
        ])
        
        # Ajustar colunas
        header = self.triggers_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 70)   # Enabled
        header.resizeSection(1, 80)   # Trigger ID
        header.resizeSection(2, 150)  # Trigger Data
        header.resizeSection(3, 80)   # TX ID
        header.resizeSection(4, 150)  # TX Data
        header.setStretchLastSection(True)  # Comment
        
        triggers_layout.addWidget(self.triggers_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("➕ Add Trigger")
        self.btn_add.clicked.connect(self.add_trigger)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_edit = QPushButton("✏️ Edit Selected")
        self.btn_edit.clicked.connect(self.edit_trigger)
        btn_layout.addWidget(self.btn_edit)
        
        self.btn_remove = QPushButton("➖ Remove Selected")
        self.btn_remove.clicked.connect(self.remove_trigger)
        btn_layout.addWidget(self.btn_remove)
        
        btn_layout.addStretch()
        triggers_layout.addLayout(btn_layout)
        
        triggers_group.setLayout(triggers_layout)
        layout.addWidget(triggers_group)
        
        # Examples
        examples_group = QGroupBox("Examples")
        examples_layout = QVBoxLayout()
        
        example_text = QLabel(
            "<b>Example 1:</b> When ID 0x280 is received, send ID 0x300<br>"
            "<b>Example 2:</b> When ID 0x284 with byte[0]=0xFF, send ID 0x301<br>"
            "<b>Example 3:</b> Simulate ECU response to diagnostic requests"
        )
        example_text.setStyleSheet(self.colors['info_text'])
        examples_layout.addWidget(example_text)
        
        examples_group.setLayout(examples_layout)
        layout.addWidget(examples_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Carregar triggers existentes
        self.load_triggers_to_table()
    
    def load_triggers_to_table(self):
        """Carrega triggers na tabela"""
        self.triggers_table.setRowCount(0)
        
        for trigger in self.triggers:
            row = self.triggers_table.rowCount()
            self.triggers_table.insertRow(row)
            
            # Enabled checkbox
            enabled_check = QCheckBox()
            enabled_check.setChecked(trigger.get('enabled', True))
            enabled_widget = QWidget()
            enabled_layout = QHBoxLayout(enabled_widget)
            enabled_layout.addWidget(enabled_check)
            enabled_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            enabled_layout.setContentsMargins(0, 0, 0, 0)
            self.triggers_table.setCellWidget(row, 0, enabled_widget)
            
            # Trigger ID
            self.triggers_table.setItem(row, 1, QTableWidgetItem(trigger.get('trigger_id', '0x000')))
            
            # Trigger Data (opcional)
            trigger_data = trigger.get('trigger_data', '')
            self.triggers_table.setItem(row, 2, QTableWidgetItem(trigger_data if trigger_data else 'Any'))
            
            # TX ID
            self.triggers_table.setItem(row, 3, QTableWidgetItem(trigger.get('tx_id', '0x000')))
            
            # TX Data
            self.triggers_table.setItem(row, 4, QTableWidgetItem(trigger.get('tx_data', '00 00 00 00 00 00 00 00')))
            
            # Comment
            self.triggers_table.setItem(row, 5, QTableWidgetItem(trigger.get('comment', '')))
    
    def add_trigger(self):
        """Adiciona novo trigger"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Dialog simples para adicionar trigger
        trigger_id, ok1 = QInputDialog.getText(self, "Add Trigger", "Trigger ID (hex):", text="0x280")
        if not ok1:
            return
        
        tx_id, ok2 = QInputDialog.getText(self, "Add Trigger", "TX ID (hex):", text="0x300")
        if not ok2:
            return
        
        tx_data, ok3 = QInputDialog.getText(self, "Add Trigger", "TX Data (hex):", text="00 00 00 00 00 00 00 00")
        if not ok3:
            return
        
        comment, ok4 = QInputDialog.getText(self, "Add Trigger", "Comment (optional):")
        
        # Adicionar à lista
        new_trigger = {
            'enabled': True,
            'trigger_id': trigger_id,
            'trigger_data': '',  # Any data
            'tx_id': tx_id,
            'tx_data': tx_data,
            'comment': comment if ok4 else ''
        }
        
        self.triggers.append(new_trigger)
        self.load_triggers_to_table()
    
    def edit_trigger(self):
        """Edita trigger selecionado"""
        current_row = self.triggers_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Edit Trigger", "Select a trigger to edit!")
            return
        
        # Implementar edição (similar ao add)
        QMessageBox.information(self, "Edit", "Edit functionality - to be implemented")
    
    def remove_trigger(self):
        """Remove trigger selecionado"""
        current_row = self.triggers_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Remove Trigger", "Select a trigger to remove!")
            return
        
        reply = QMessageBox.question(
            self,
            "Remove Trigger",
            "Are you sure you want to remove this trigger?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.triggers.pop(current_row)
            self.load_triggers_to_table()
    
    def get_triggers(self):
        """Retorna lista de triggers configurados"""
        triggers = []
        
        for row in range(self.triggers_table.rowCount()):
            # Get enabled state
            enabled_widget = self.triggers_table.cellWidget(row, 0)
            enabled_check = enabled_widget.findChild(QCheckBox)
            enabled = enabled_check.isChecked() if enabled_check else True
            
            trigger = {
                'enabled': enabled,
                'trigger_id': self.triggers_table.item(row, 1).text(),
                'trigger_data': self.triggers_table.item(row, 2).text(),
                'tx_id': self.triggers_table.item(row, 3).text(),
                'tx_data': self.triggers_table.item(row, 4).text(),
                'comment': self.triggers_table.item(row, 5).text() if self.triggers_table.item(row, 5) else ''
            }
            triggers.append(trigger)
        
        return {
            'enabled': self.enable_check.isChecked(),
            'triggers': triggers
        }


class USBDeviceSelectionDialog(QDialog):
    """Diálogo para seleção de dispositivos USB/Serial"""
    
    def __init__(self, parent=None, usb_monitor=None):
        super().__init__(parent)
        self.usb_monitor = usb_monitor
        self.selected_device = None
        self.init_ui()
        self.refresh_devices()
    
    def init_ui(self):
        self.setWindowTitle(t('dialog_usb_device_title'))
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Informação
        info_label = QLabel(t('dialog_usb_device_info'))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Tabela de dispositivos
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(3)
        self.devices_table.setHorizontalHeaderLabels([
            t('label_device_name'),
            t('label_device_path'),
            t('label_device_description')
        ])
        self.devices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.devices_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.devices_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.devices_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.devices_table.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.devices_table)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Botões
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton(t('btn_refresh'))
        self.refresh_btn.clicked.connect(self.refresh_devices)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.select_btn = QPushButton(t('btn_select'))
        self.select_btn.clicked.connect(self.accept)
        self.select_btn.setEnabled(False)
        button_layout.addWidget(self.select_btn)
        
        self.cancel_btn = QPushButton(t('btn_cancel'))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Conectar sinal de seleção
        self.devices_table.itemSelectionChanged.connect(self.on_selection_changed)
    
    def refresh_devices(self):
        """Atualiza a lista de dispositivos"""
        self.devices_table.setRowCount(0)
        
        if not self.usb_monitor:
            self.status_label.setText(t('msg_usb_monitor_not_available'))
            return
        
        # Obter dispositivos disponíveis
        devices = self.usb_monitor.get_available_devices()
        
        if not devices:
            self.status_label.setText(t('msg_no_usb_devices_found'))
            return
        
        # Preencher tabela
        self.devices_table.setRowCount(len(devices))
        for row, device in enumerate(devices):
            # Nome
            name_item = QTableWidgetItem(device.name)
            self.devices_table.setItem(row, 0, name_item)
            
            # Caminho
            path_item = QTableWidgetItem(device.path)
            self.devices_table.setItem(row, 1, path_item)
            
            # Descrição
            desc_item = QTableWidgetItem(device.description)
            self.devices_table.setItem(row, 2, desc_item)
        
        self.status_label.setText(t('msg_usb_devices_found').format(count=len(devices)))
    
    def on_selection_changed(self):
        """Callback quando a seleção muda"""
        has_selection = len(self.devices_table.selectedItems()) > 0
        self.select_btn.setEnabled(has_selection)
    
    def get_selected_device(self):
        """Retorna o dispositivo selecionado"""
        selected_rows = self.devices_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        path = self.devices_table.item(row, 1).text()
        name = self.devices_table.item(row, 0).text()
        
        # Criar objeto de dispositivo
        from .usb_device_monitor import USBDeviceInfo
        return USBDeviceInfo(path, name)
    
    def accept(self):
        """Aceita a seleção"""
        self.selected_device = self.get_selected_device()
        if self.selected_device:
            super().accept()
        else:
            QMessageBox.warning(self, t('warning'), t('msg_select_device'))
