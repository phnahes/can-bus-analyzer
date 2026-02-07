"""
Dialogs - Application dialog windows (refactored version)
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

from ..models import CANMessage, CANConfig, GatewayConfig, GatewayBlockRule, GatewayDynamicBlock, GatewayModifyRule, GatewayRoute
from ..utils import calculate_baudrate_divisor
from ..i18n import get_i18n, t
from ..theme import get_adaptive_colors, get_bit_style, should_use_dark_mode
from ..baudrate_detect_dialog import BaudrateDetectDialog


class SettingsDialog(QDialog):
    """Connection settings dialog"""
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
        
        # Auto-Detect button
        btn_auto_detect = QPushButton("🔍 Auto")
        btn_auto_detect.setToolTip("Auto-detect baudrate")
        btn_auto_detect.setMaximumWidth(70)
        btn_auto_detect.clicked.connect(lambda: self._auto_detect_baudrate(channel_input, baudrate_combo))
        row3.addWidget(btn_auto_detect)
        
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
    
    def _auto_detect_baudrate(self, channel_input, baudrate_combo):
        """Auto-detect baudrate for a specific CAN bus"""
        channel = channel_input.currentText()
        
        # Detecta interface baseado no canal
        interface = 'socketcan'
        if channel.startswith('/dev/tty') or channel.startswith('COM'):
            interface = 'slcan'
        
        # Open detection dialog
        dialog = BaudrateDetectDialog(self, channel=channel, interface=interface)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            detected_baudrate = dialog.get_detected_baudrate()
            
            if detected_baudrate:
                # Atualiza o combo com o baudrate detectado
                baudrate_text = f"{detected_baudrate // 1000} Kbit/s"
                
                # Check if baudrate is in the list
                index = baudrate_combo.findText(baudrate_text)
                if index >= 0:
                    baudrate_combo.setCurrentIndex(index)
                else:
                    # If not in list, add it
                    baudrate_combo.addItem(baudrate_text)
                    baudrate_combo.setCurrentText(baudrate_text)
                
                QMessageBox.information(
                    self,
                    "Baudrate Detected",
                    f"Baudrate detected: {detected_baudrate:,} bps\n\n"
                    f"The baudrate has been updated in the configuration."
                )
    
    def get_config(self):
        """Return updated configuration"""
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
        """Return filter configuration"""
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
    """Dialog to configure automatic transmission triggers"""
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
        
        # Add to list
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
        
        # Implement edit (similar to add)
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
    """Dialog for USB/Serial device selection"""
    
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
        
        # Information
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
        
        # Buttons
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
        
        # Connect selection signal
        self.devices_table.itemSelectionChanged.connect(self.on_selection_changed)
    
    def refresh_devices(self):
        """Atualiza a lista de dispositivos"""
        self.devices_table.setRowCount(0)
        
        if not self.usb_monitor:
            self.status_label.setText(t('msg_usb_monitor_not_available'))
            return
        
        # Get available devices
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
            
            # Description
            desc_item = QTableWidgetItem(device.description)
            self.devices_table.setItem(row, 2, desc_item)
        
        self.status_label.setText(t('msg_usb_devices_found').format(count=len(devices)))
    
    def on_selection_changed(self):
        """Callback when selection changes"""
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
        """Accept the selection"""
        self.selected_device = self.get_selected_device()
        if self.selected_device:
            super().accept()
        else:
            QMessageBox.warning(self, t('warning'), t('msg_select_device'))


class ModifyRuleDialog(QDialog):
    """Dialog to configure message modification rule with bit mask"""
    def __init__(self, parent=None, channel=None, can_id=None, existing_rule=None):
        super().__init__(parent)
        self.channel = channel or "CAN1"
        self.can_id = can_id or 0x000
        self.existing_rule = existing_rule
        self.i18n = get_i18n()
        
        # Initialize data
        if existing_rule:
            self.new_id = existing_rule.new_id
            self.data_mask = existing_rule.data_mask.copy()
            self.new_data = bytearray(existing_rule.new_data)
        else:
            self.new_id = None
            self.data_mask = [False] * 8
            self.new_data = bytearray([0x00] * 8)
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(t('gateway_modify_rule_title'))
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        
        # Get theme
        colors = get_adaptive_colors('system')
        
        # ===== Message Info =====
        info_group = QGroupBox(t('gateway_message_info'))
        info_layout = QGridLayout()
        
        info_layout.addWidget(QLabel(t('gateway_channel') + ":"), 0, 0)
        info_layout.addWidget(QLabel(f"<b>{self.channel}</b>"), 0, 1)
        
        info_layout.addWidget(QLabel(t('gateway_id') + ":"), 1, 0)
        info_layout.addWidget(QLabel(f"<b>0x{self.can_id:03X}</b>"), 1, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # ===== ID Modification =====
        id_group = QGroupBox(t('gateway_id_modification'))
        id_layout = QHBoxLayout()
        
        self.modify_id_check = QCheckBox(t('gateway_change_id'))
        self.modify_id_check.setChecked(self.new_id is not None)
        self.modify_id_check.toggled.connect(self.on_modify_id_toggled)
        id_layout.addWidget(self.modify_id_check)
        
        id_layout.addWidget(QLabel(t('gateway_new_id') + ":"))
        self.new_id_input = QLineEdit()
        self.new_id_input.setPlaceholderText("0x000")
        self.new_id_input.setMaximumWidth(100)
        self.new_id_input.setEnabled(self.new_id is not None)
        if self.new_id is not None:
            self.new_id_input.setText(f"0x{self.new_id:03X}")
        id_layout.addWidget(self.new_id_input)
        
        id_layout.addStretch()
        id_group.setLayout(id_layout)
        layout.addWidget(id_group)
        
        # ===== Data Modification with Bit Masks =====
        data_group = QGroupBox(t('gateway_data_modification'))
        data_layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel(t('gateway_data_modification_info'))
        info_label.setWordWrap(True)
        info_label.setStyleSheet(colors['info_text'])
        data_layout.addWidget(info_label)
        
        # Create byte editors (8 bytes)
        self.byte_editors = []
        
        for byte_idx in range(8):
            byte_widget = QWidget()
            byte_layout = QVBoxLayout(byte_widget)
            byte_layout.setContentsMargins(5, 5, 5, 5)
            
            # Byte header
            byte_header = QLabel(f"<b>Byte {byte_idx} (D{byte_idx})</b>")
            byte_layout.addWidget(byte_header)
            
            # Enable checkbox
            enable_check = QCheckBox(t('gateway_modify_this_byte'))
            enable_check.setChecked(self.data_mask[byte_idx])
            enable_check.toggled.connect(lambda checked, idx=byte_idx: self.on_byte_enabled(idx, checked))
            byte_layout.addWidget(enable_check)
            
            # Hex value input
            hex_layout = QHBoxLayout()
            hex_layout.addWidget(QLabel("Hex:"))
            hex_input = QLineEdit(f"{self.new_data[byte_idx]:02X}")
            hex_input.setMaximumWidth(50)
            hex_input.setMaxLength(2)
            hex_input.setInputMask("HH")
            hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hex_input.setEnabled(self.data_mask[byte_idx])
            hex_input.textChanged.connect(lambda text, idx=byte_idx: self.on_hex_changed(idx, text))
            hex_layout.addWidget(hex_input)
            hex_layout.addStretch()
            byte_layout.addLayout(hex_layout)
            
            # Bit checkboxes (8 bits per byte)
            bits_label = QLabel(t('gateway_bits') + ":")
            byte_layout.addWidget(bits_label)
            
            bits_layout = QHBoxLayout()
            bit_checks = []
            for bit_idx in range(7, -1, -1):  # MSB to LSB (7→0)
                bit_check = QCheckBox(f"{bit_idx}")
                bit_value = (self.new_data[byte_idx] >> bit_idx) & 1
                bit_check.setChecked(bool(bit_value))
                bit_check.setEnabled(self.data_mask[byte_idx])
                bit_check.toggled.connect(lambda checked, b_idx=byte_idx, bit=bit_idx: self.on_bit_toggled(b_idx, bit, checked))
                bit_checks.append(bit_check)
                bits_layout.addWidget(bit_check)
            bits_layout.addStretch()
            byte_layout.addLayout(bits_layout)
            
            # Decimal value display
            dec_label = QLabel(f"Dec: {self.new_data[byte_idx]}")
            dec_label.setStyleSheet("color: gray; font-size: 10px;")
            byte_layout.addWidget(dec_label)
            
            # Store references
            self.byte_editors.append({
                'widget': byte_widget,
                'enable_check': enable_check,
                'hex_input': hex_input,
                'bit_checks': bit_checks,
                'dec_label': dec_label
            })
        
        # Arrange bytes in grid (2 rows x 4 columns)
        bytes_grid = QWidget()
        bytes_grid_layout = QGridLayout(bytes_grid)
        
        for i, editor in enumerate(self.byte_editors):
            row = i // 4
            col = i % 4
            bytes_grid_layout.addWidget(editor['widget'], row, col)
        
        # Add to scrollable area
        scroll = QScrollArea()
        scroll.setWidget(bytes_grid)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(300)
        data_layout.addWidget(scroll)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # ===== Preview =====
        preview_group = QGroupBox(t('gateway_preview'))
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.update_preview()
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # ===== Buttons =====
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_modify_id_toggled(self, checked):
        """Handle ID modification toggle"""
        self.new_id_input.setEnabled(checked)
        if not checked:
            self.new_id = None
        self.update_preview()
    
    def on_byte_enabled(self, byte_idx, checked):
        """Handle byte enable/disable"""
        self.data_mask[byte_idx] = checked
        
        # Enable/disable controls
        editor = self.byte_editors[byte_idx]
        editor['hex_input'].setEnabled(checked)
        for bit_check in editor['bit_checks']:
            bit_check.setEnabled(checked)
        
        self.update_preview()
    
    def on_hex_changed(self, byte_idx, text):
        """Handle hex value change"""
        if len(text) == 2:
            try:
                value = int(text, 16)
                self.new_data[byte_idx] = value
                
                # Update bit checkboxes
                editor = self.byte_editors[byte_idx]
                for bit_idx in range(8):
                    bit_value = (value >> bit_idx) & 1
                    # Temporarily disconnect to avoid recursion
                    editor['bit_checks'][7 - bit_idx].blockSignals(True)
                    editor['bit_checks'][7 - bit_idx].setChecked(bool(bit_value))
                    editor['bit_checks'][7 - bit_idx].blockSignals(False)
                
                # Update decimal label
                editor['dec_label'].setText(f"Dec: {value}")
                
                self.update_preview()
            except ValueError:
                pass
    
    def on_bit_toggled(self, byte_idx, bit_idx, checked):
        """Handle individual bit toggle"""
        if checked:
            self.new_data[byte_idx] |= (1 << bit_idx)
        else:
            self.new_data[byte_idx] &= ~(1 << bit_idx)
        
        # Update hex input
        editor = self.byte_editors[byte_idx]
        editor['hex_input'].blockSignals(True)
        editor['hex_input'].setText(f"{self.new_data[byte_idx]:02X}")
        editor['hex_input'].blockSignals(False)
        
        # Update decimal label
        editor['dec_label'].setText(f"Dec: {self.new_data[byte_idx]}")
        
        self.update_preview()
    
    def update_preview(self):
        """Update preview of modifications"""
        preview_text = f"<b>{t('gateway_original')}:</b> ID=0x{self.can_id:03X}, Data=[Original]<br>"
        
        # ID modification
        if self.modify_id_check.isChecked() and self.new_id_input.text():
            try:
                id_text = self.new_id_input.text().strip()
                if id_text.startswith('0x'):
                    new_id = int(id_text, 16)
                else:
                    new_id = int(id_text)
                self.new_id = new_id
                preview_text += f"<b>{t('gateway_modified')}:</b> ID=<span style='color: orange;'>0x{new_id:03X}</span>"
            except ValueError:
                preview_text += f"<b>{t('gateway_modified')}:</b> ID=0x{self.can_id:03X}"
        else:
            self.new_id = None
            preview_text += f"<b>{t('gateway_modified')}:</b> ID=0x{self.can_id:03X}"
        
        # Data modification
        modified_bytes = []
        for i in range(8):
            if self.data_mask[i]:
                modified_bytes.append(f"<span style='color: orange;'>{self.new_data[i]:02X}</span>")
            else:
                modified_bytes.append("--")
        
        preview_text += f", Data=[{' '.join(modified_bytes)}]"
        
        # Summary
        mask_count = sum(self.data_mask)
        if mask_count > 0:
            preview_text += f"<br><br><i>{t('gateway_bytes_modified')}: {mask_count}</i>"
        
        self.preview_label.setText(preview_text)
    
    def get_rule(self) -> GatewayModifyRule:
        """Get the configured modify rule"""
        return GatewayModifyRule(
            can_id=self.can_id,
            channel=self.channel,
            enabled=True,
            new_id=self.new_id,
            data_mask=self.data_mask.copy(),
            new_data=bytes(self.new_data)
        )


class GatewayDialog(QDialog):
    """CAN Gateway configuration dialog"""
    def __init__(self, parent=None, config=None, bus_names=None):
        super().__init__(parent)
        self.config = config or GatewayConfig()
        self.bus_names = bus_names or ["CAN1", "CAN2"]
        self.i18n = get_i18n()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(t('gateway_title'))
        self.setModal(True)
        self.setMinimumWidth(900)
        self.setMinimumHeight(750)
        
        layout = QVBoxLayout(self)
        
        # Get theme preference
        colors = get_adaptive_colors('system')
        
        # ===== Transmission Control =====
        transmission_group = QGroupBox(t('gateway_transmission'))
        transmission_layout = QVBoxLayout()
        
        # Enable Gateway
        self.enable_gateway_check = QCheckBox(t('gateway_enable'))
        self.enable_gateway_check.setChecked(self.config.enabled)
        transmission_layout.addWidget(self.enable_gateway_check)
        
        # Route selection - simple horizontal layout
        route_layout = QHBoxLayout()
        
        route_layout.addWidget(QLabel(t('gateway_from') + ":"))
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(100)
        for bus_name in self.bus_names:
            self.source_combo.addItem(bus_name)
        route_layout.addWidget(self.source_combo)
        
        route_layout.addWidget(QLabel("→"))
        
        route_layout.addWidget(QLabel(t('gateway_to') + ":"))
        self.dest_combo = QComboBox()
        self.dest_combo.setMinimumWidth(100)
        for bus_name in self.bus_names:
            self.dest_combo.addItem(bus_name)
        if len(self.bus_names) > 1:
            self.dest_combo.setCurrentIndex(1)  # Default to second bus
        route_layout.addWidget(self.dest_combo)
        
        self.add_route_btn = QPushButton("➕ " + t('btn_add_route'))
        self.add_route_btn.clicked.connect(self.add_route)
        route_layout.addWidget(self.add_route_btn)
        
        self.remove_route_btn = QPushButton("➖ " + t('btn_remove'))
        self.remove_route_btn.clicked.connect(self.remove_route)
        route_layout.addWidget(self.remove_route_btn)
        
        route_layout.addStretch()
        transmission_layout.addLayout(route_layout)
        
        # Routes table
        self.routes_table = QTableWidget()
        self.routes_table.setColumnCount(3)
        self.routes_table.setHorizontalHeaderLabels([
            t('gateway_from'),
            t('gateway_to'),
            t('gateway_enabled')
        ])
        # Adjust column widths
        header = self.routes_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)
        self.routes_table.setColumnWidth(2, 80)  # Fixed width for Enabled column
        self.routes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.routes_table.setMaximumHeight(150)
        transmission_layout.addWidget(self.routes_table)
        
        transmission_group.setLayout(transmission_layout)
        layout.addWidget(transmission_group)
        
        # Info label explaining channel logic
        info_label = QLabel(t('gateway_channel_info'))
        info_label.setWordWrap(True)
        info_label.setStyleSheet(colors['info_text'])
        layout.addWidget(info_label)
        
        # ===== Static Blocking Rules =====
        blocking_group = QGroupBox(t('gateway_blocking'))
        blocking_layout = QVBoxLayout()
        
        # Add rule controls
        add_block_layout = QHBoxLayout()
        
        add_block_layout.addWidget(QLabel(t('gateway_block_id') + ":"))
        self.block_id_input = QLineEdit()
        self.block_id_input.setPlaceholderText("0x000")
        self.block_id_input.setMaximumWidth(100)
        add_block_layout.addWidget(self.block_id_input)
        
        self.add_block_btn = QPushButton("➕ " + t('btn_add'))
        self.add_block_btn.clicked.connect(self.add_block_rule)
        add_block_layout.addWidget(self.add_block_btn)
        
        self.remove_block_btn = QPushButton("➖ " + t('btn_remove'))
        self.remove_block_btn.clicked.connect(self.remove_block_rule)
        add_block_layout.addWidget(self.remove_block_btn)
        
        add_block_layout.addStretch()
        blocking_layout.addLayout(add_block_layout)
        
        # Block rules table
        self.block_table = QTableWidget()
        self.block_table.setColumnCount(3)
        self.block_table.setHorizontalHeaderLabels([
            t('gateway_source_channel'),
            t('gateway_id'),
            t('gateway_enabled')
        ])
        # Adjust column widths
        header = self.block_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)
        self.block_table.setColumnWidth(2, 80)  # Fixed width for Enabled column
        self.block_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        blocking_layout.addWidget(self.block_table)
        
        blocking_group.setLayout(blocking_layout)
        layout.addWidget(blocking_group)
        
        # ===== Dynamic Blocking =====
        dynamic_group = QGroupBox(t('gateway_dynamic_blocking'))
        dynamic_layout = QVBoxLayout()
        
        # Dynamic block controls
        dyn_control_layout = QHBoxLayout()
        
        dyn_control_layout.addWidget(QLabel(t('gateway_id_from') + ":"))
        self.dyn_id_from_input = QLineEdit()
        self.dyn_id_from_input.setPlaceholderText("0x000")
        self.dyn_id_from_input.setMaximumWidth(100)
        dyn_control_layout.addWidget(self.dyn_id_from_input)
        
        dyn_control_layout.addWidget(QLabel(t('gateway_id_to') + ":"))
        self.dyn_id_to_input = QLineEdit()
        self.dyn_id_to_input.setPlaceholderText("0x7FF")
        self.dyn_id_to_input.setMaximumWidth(100)
        dyn_control_layout.addWidget(self.dyn_id_to_input)
        
        dyn_control_layout.addWidget(QLabel(t('gateway_period') + ":"))
        self.dyn_period_input = QLineEdit()
        self.dyn_period_input.setPlaceholderText("1000")
        self.dyn_period_input.setMaximumWidth(80)
        dyn_control_layout.addWidget(self.dyn_period_input)
        dyn_control_layout.addWidget(QLabel("ms"))
        
        self.add_dyn_btn = QPushButton("➕ " + t('btn_add'))
        self.add_dyn_btn.clicked.connect(self.add_dynamic_block)
        dyn_control_layout.addWidget(self.add_dyn_btn)
        
        self.remove_dyn_btn = QPushButton("➖ " + t('btn_remove'))
        self.remove_dyn_btn.clicked.connect(self.remove_dynamic_block)
        dyn_control_layout.addWidget(self.remove_dyn_btn)
        
        dyn_control_layout.addStretch()
        dynamic_layout.addLayout(dyn_control_layout)
        
        # Dynamic block table
        self.dynamic_table = QTableWidget()
        self.dynamic_table.setColumnCount(5)
        self.dynamic_table.setHorizontalHeaderLabels([
            t('gateway_source_channel'),
            t('gateway_id_from'),
            t('gateway_id_to'),
            t('gateway_period'),
            t('gateway_enabled')
        ])
        # Adjust column widths
        header = self.dynamic_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)
        header.setSectionResizeMode(3, header.ResizeMode.Stretch)
        header.setSectionResizeMode(4, header.ResizeMode.Fixed)
        self.dynamic_table.setColumnWidth(4, 80)  # Fixed width for Enabled column
        self.dynamic_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        dynamic_layout.addWidget(self.dynamic_table)
        
        dynamic_group.setLayout(dynamic_layout)
        layout.addWidget(dynamic_group)
        
        # ===== Message Modification =====
        modify_group = QGroupBox(t('gateway_modification'))
        modify_layout = QVBoxLayout()
        
        # Modify controls
        modify_control_layout = QHBoxLayout()
        
        modify_control_layout.addWidget(QLabel(t('gateway_modify_id') + ":"))
        self.modify_id_input = QLineEdit()
        self.modify_id_input.setPlaceholderText("0x000")
        self.modify_id_input.setMaximumWidth(100)
        modify_control_layout.addWidget(self.modify_id_input)
        
        self.add_modify_btn = QPushButton("✏️ " + t('gateway_add_modify'))
        self.add_modify_btn.clicked.connect(self.show_modify_dialog)
        modify_control_layout.addWidget(self.add_modify_btn)
        
        self.remove_modify_btn = QPushButton("➖ " + t('btn_remove'))
        self.remove_modify_btn.clicked.connect(self.remove_modify_rule)
        modify_control_layout.addWidget(self.remove_modify_btn)
        
        modify_control_layout.addStretch()
        modify_layout.addLayout(modify_control_layout)
        
        # Modify rules table
        self.modify_table = QTableWidget()
        self.modify_table.setColumnCount(5)
        self.modify_table.setHorizontalHeaderLabels([
            t('gateway_source_channel'),
            t('gateway_id'),
            t('gateway_new_id'),
            t('gateway_data_mask'),
            t('gateway_enabled')
        ])
        # Adjust column widths
        header = self.modify_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)
        header.setSectionResizeMode(3, header.ResizeMode.Stretch)
        header.setSectionResizeMode(4, header.ResizeMode.Fixed)
        self.modify_table.setColumnWidth(4, 80)  # Fixed width for Enabled column
        self.modify_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.modify_table.itemDoubleClicked.connect(self.edit_modify_rule)
        modify_layout.addWidget(self.modify_table)
        
        modify_group.setLayout(modify_layout)
        layout.addWidget(modify_group)
        
        # ===== Statistics =====
        stats_group = QGroupBox(t('gateway_statistics'))
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel(t('gateway_stats_template').format(
            forwarded=0, blocked=0, modified=0
        ))
        stats_layout.addWidget(self.stats_label)
        
        self.reset_stats_btn = QPushButton(t('gateway_reset_stats'))
        self.reset_stats_btn.clicked.connect(self.reset_stats)
        stats_layout.addWidget(self.reset_stats_btn)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # ===== Save/Load Configuration =====
        config_layout = QHBoxLayout()
        
        self.save_config_btn = QPushButton(t('gateway_save_config'))
        self.save_config_btn.clicked.connect(self.save_gateway_config)
        config_layout.addWidget(self.save_config_btn)
        
        self.load_config_btn = QPushButton(t('gateway_load_config'))
        self.load_config_btn.clicked.connect(self.load_gateway_config)
        config_layout.addWidget(self.load_config_btn)
        
        config_layout.addStretch()
        layout.addLayout(config_layout)
        
        # ===== Buttons =====
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Load existing rules and routes
        self.load_routes()
        self.load_rules()
    
    def _create_centered_checkbox(self, checked=True):
        """Create a centered checkbox widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget, checkbox
    
    def load_routes(self):
        """Load existing routes into table"""
        self.routes_table.setRowCount(len(self.config.routes))
        for row, route in enumerate(self.config.routes):
            self.routes_table.setItem(row, 0, QTableWidgetItem(route.source))
            self.routes_table.setItem(row, 1, QTableWidgetItem(route.destination))
            
            widget, enabled_check = self._create_centered_checkbox(route.enabled)
            # Connect to apply changes immediately
            enabled_check.stateChanged.connect(lambda state, r=row: self._on_route_enabled_changed(r, state))
            self.routes_table.setCellWidget(row, 2, widget)
    
    def _on_route_enabled_changed(self, row, state):
        """Apply route enable/disable immediately"""
        if row < len(self.config.routes):
            self.config.routes[row].enabled = (state == Qt.CheckState.Checked.value)
            # Apply to parent if dialog has parent with can_bus_manager
            if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
                if self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(self.config)
    
    def add_route(self):
        """Add a new route"""
        source = self.source_combo.currentText()
        dest = self.dest_combo.currentText()
        
        # Validate
        if source == dest:
            QMessageBox.warning(
                self,
                t('warning'),
                t('gateway_same_source_dest')
            )
            return
        
        # Check if route already exists
        for route in self.config.routes:
            if route.source == source and route.destination == dest:
                QMessageBox.warning(
                    self,
                    t('warning'),
                    t('gateway_route_exists')
                )
                return
        
        # Add route
        route = GatewayRoute(source=source, destination=dest, enabled=True)
        self.config.routes.append(route)
        
        # Add to table
        row = self.routes_table.rowCount()
        self.routes_table.insertRow(row)
        self.routes_table.setItem(row, 0, QTableWidgetItem(source))
        self.routes_table.setItem(row, 1, QTableWidgetItem(dest))
        
        widget, enabled_check = self._create_centered_checkbox(True)
        # Connect to apply changes immediately
        enabled_check.stateChanged.connect(lambda state, r=row: self._on_route_enabled_changed(r, state))
        self.routes_table.setCellWidget(row, 2, widget)
    
    def remove_route(self):
        """Remove selected route"""
        selected_rows = self.routes_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, t('warning'), t('gateway_select_route'))
            return
        
        row = selected_rows[0].row()
        self.config.routes.pop(row)
        self.routes_table.removeRow(row)
    
    def load_rules(self):
        """Load existing rules into tables"""
        # Load block rules
        self.block_table.setRowCount(len(self.config.block_rules))
        for row, rule in enumerate(self.config.block_rules):
            self.block_table.setItem(row, 0, QTableWidgetItem(rule.channel))
            self.block_table.setItem(row, 1, QTableWidgetItem(f"0x{rule.can_id:03X}"))
            
            widget, enabled_check = self._create_centered_checkbox(rule.enabled)
            # Connect to apply changes immediately
            enabled_check.stateChanged.connect(lambda state, r=row: self._on_block_enabled_changed(r, state))
            self.block_table.setCellWidget(row, 2, widget)
        
        # Load dynamic blocks
        self.dynamic_table.setRowCount(len(self.config.dynamic_blocks))
        for row, dyn_block in enumerate(self.config.dynamic_blocks):
            self.dynamic_table.setItem(row, 0, QTableWidgetItem(dyn_block.channel))
            self.dynamic_table.setItem(row, 1, QTableWidgetItem(f"0x{dyn_block.id_from:03X}"))
            self.dynamic_table.setItem(row, 2, QTableWidgetItem(f"0x{dyn_block.id_to:03X}"))
            self.dynamic_table.setItem(row, 3, QTableWidgetItem(f"{dyn_block.period}"))
            
            widget, enabled_check = self._create_centered_checkbox(dyn_block.enabled)
            # Connect to apply changes immediately
            enabled_check.stateChanged.connect(lambda state, r=row: self._on_dynamic_enabled_changed(r, state))
            self.dynamic_table.setCellWidget(row, 4, widget)
        
        # Load modify rules
        self.modify_table.setRowCount(len(self.config.modify_rules))
        for row, rule in enumerate(self.config.modify_rules):
            self.modify_table.setItem(row, 0, QTableWidgetItem(rule.channel))
            self.modify_table.setItem(row, 1, QTableWidgetItem(f"0x{rule.can_id:03X}"))
            
            # New ID
            new_id_str = f"0x{rule.new_id:03X}" if rule.new_id is not None else "-"
            self.modify_table.setItem(row, 2, QTableWidgetItem(new_id_str))
            
            # Data mask summary
            mask_count = sum(rule.data_mask)
            mask_str = f"{mask_count} bytes" if mask_count > 0 else "-"
            self.modify_table.setItem(row, 3, QTableWidgetItem(mask_str))
            
            widget, enabled_check = self._create_centered_checkbox(rule.enabled)
            # Connect to apply changes immediately
            enabled_check.stateChanged.connect(lambda state, r=row: self._on_modify_enabled_changed(r, state))
            self.modify_table.setCellWidget(row, 4, widget)
    
    def _on_block_enabled_changed(self, row, state):
        """Apply block rule enable/disable immediately"""
        if row < len(self.config.block_rules):
            self.config.block_rules[row].enabled = (state == Qt.CheckState.Checked.value)
            # Apply to parent if dialog has parent with can_bus_manager
            if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
                if self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(self.config)
    
    def _on_dynamic_enabled_changed(self, row, state):
        """Apply dynamic block enable/disable immediately"""
        if row < len(self.config.dynamic_blocks):
            self.config.dynamic_blocks[row].enabled = (state == Qt.CheckState.Checked.value)
            # Apply to parent if dialog has parent with can_bus_manager
            if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
                if self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(self.config)
    
    def _on_modify_enabled_changed(self, row, state):
        """Apply modify rule enable/disable immediately"""
        if row < len(self.config.modify_rules):
            self.config.modify_rules[row].enabled = (state == Qt.CheckState.Checked.value)
            # Apply to parent if dialog has parent with can_bus_manager
            if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
                if self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(self.config)
    
    def _get_source_channels(self):
        """Get list of source channels based on active routes"""
        channels = []
        for row in range(self.routes_table.rowCount()):
            checkbox = self.routes_table.cellWidget(row, 2)
            if checkbox and checkbox.isChecked():
                source = self.routes_table.item(row, 0).text()
                if source not in channels:
                    channels.append(source)
        return channels
    
    def add_block_rule(self):
        """Add a new blocking rule (auto-detects channel from transmission direction)"""
        try:
            id_text = self.block_id_input.text().strip()
            
            if not id_text:
                QMessageBox.warning(self, t('warning'), t('gateway_enter_id'))
                return
            
            # Check if transmission is configured
            source_channels = self._get_source_channels()
            if not source_channels:
                QMessageBox.warning(
                    self,
                    t('warning'),
                    t('gateway_configure_transmission_first')
                )
                return
            
            # Parse ID (support hex with 0x prefix)
            if id_text.startswith('0x') or id_text.startswith('0X'):
                can_id = int(id_text, 16)
            else:
                can_id = int(id_text)
            
            # Add rule for each active source channel
            for channel in source_channels:
                rule = GatewayBlockRule(can_id=can_id, channel=channel, enabled=True)
                self.config.block_rules.append(rule)
                
                # Add to table
                row = self.block_table.rowCount()
                self.block_table.insertRow(row)
                self.block_table.setItem(row, 0, QTableWidgetItem(channel))
                self.block_table.setItem(row, 1, QTableWidgetItem(f"0x{can_id:03X}"))
                
                widget, enabled_check = self._create_centered_checkbox(True)
                # Connect to apply changes immediately
                enabled_check.stateChanged.connect(lambda state, r=row: self._on_block_enabled_changed(r, state))
                self.block_table.setCellWidget(row, 2, widget)
            
            # Clear input
            self.block_id_input.clear()
            
        except ValueError:
            QMessageBox.warning(self, t('error'), t('gateway_invalid_id'))
    
    def remove_block_rule(self):
        """Remove selected blocking rule"""
        selected_rows = self.block_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, t('warning'), t('gateway_select_rule'))
            return
        
        row = selected_rows[0].row()
        self.config.block_rules.pop(row)
        self.block_table.removeRow(row)
    
    def add_dynamic_block(self):
        """Add a new dynamic blocking rule (auto-detects channel)"""
        try:
            id_from_text = self.dyn_id_from_input.text().strip()
            id_to_text = self.dyn_id_to_input.text().strip()
            period_text = self.dyn_period_input.text().strip()
            
            if not all([id_from_text, id_to_text, period_text]):
                QMessageBox.warning(self, t('warning'), t('gateway_fill_all_fields'))
                return
            
            # Check if transmission is configured
            source_channels = self._get_source_channels()
            if not source_channels:
                QMessageBox.warning(
                    self,
                    t('warning'),
                    t('gateway_configure_transmission_first')
                )
                return
            
            # Parse values
            if id_from_text.startswith('0x'):
                id_from = int(id_from_text, 16)
            else:
                id_from = int(id_from_text)
            
            if id_to_text.startswith('0x'):
                id_to = int(id_to_text, 16)
            else:
                id_to = int(id_to_text)
            
            period = int(period_text)
            
            # Add dynamic block for each active source channel
            for channel in source_channels:
                dyn_block = GatewayDynamicBlock(
                    id_from=id_from,
                    id_to=id_to,
                    channel=channel,
                    period=period,
                    enabled=True
                )
                self.config.dynamic_blocks.append(dyn_block)
                
                # Add to table
                row = self.dynamic_table.rowCount()
                self.dynamic_table.insertRow(row)
                self.dynamic_table.setItem(row, 0, QTableWidgetItem(channel))
                self.dynamic_table.setItem(row, 1, QTableWidgetItem(f"0x{id_from:03X}"))
                self.dynamic_table.setItem(row, 2, QTableWidgetItem(f"0x{id_to:03X}"))
                self.dynamic_table.setItem(row, 3, QTableWidgetItem(f"{period}"))
                
                widget, enabled_check = self._create_centered_checkbox(True)
                # Connect to apply changes immediately
                enabled_check.stateChanged.connect(lambda state, r=row: self._on_dynamic_enabled_changed(r, state))
                self.dynamic_table.setCellWidget(row, 4, widget)
            
            # Clear inputs
            self.dyn_id_from_input.clear()
            self.dyn_id_to_input.clear()
            self.dyn_period_input.clear()
            
        except ValueError:
            QMessageBox.warning(self, t('error'), t('gateway_invalid_values'))
    
    def remove_dynamic_block(self):
        """Remove selected dynamic blocking rule"""
        selected_rows = self.dynamic_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, t('warning'), t('gateway_select_rule'))
            return
        
        row = selected_rows[0].row()
        self.config.dynamic_blocks.pop(row)
        self.dynamic_table.removeRow(row)
    
    def reset_stats(self):
        """Reset statistics (signal to parent)"""
        self.stats_label.setText(t('gateway_stats_template').format(
            forwarded=0, blocked=0, modified=0
        ))
    
    def update_stats(self, stats):
        """Update statistics display"""
        self.stats_label.setText(t('gateway_stats_template').format(
            forwarded=stats.get('forwarded', 0),
            blocked=stats.get('blocked', 0),
            modified=stats.get('modified', 0)
        ))
    
    def show_modify_dialog(self):
        """Show dialog to add/edit modify rule (auto-detects channel)"""
        id_text = self.modify_id_input.text().strip()
        
        if not id_text:
            QMessageBox.warning(self, t('warning'), t('gateway_enter_id'))
            return
        
        # Check if transmission is configured
        source_channels = self._get_source_channels()
        if not source_channels:
            QMessageBox.warning(
                self,
                t('warning'),
                t('gateway_configure_transmission_first')
            )
            return
        
        try:
            # Parse ID
            if id_text.startswith('0x') or id_text.startswith('0X'):
                can_id = int(id_text, 16)
            else:
                can_id = int(id_text)
            
            # Add rule for each active source channel
            for channel in source_channels:
                # Show modify rule editor dialog
                dialog = ModifyRuleDialog(self, channel, can_id)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    rule = dialog.get_rule()
                    self.config.modify_rules.append(rule)
                    
                    # Add to table
                    row = self.modify_table.rowCount()
                    self.modify_table.insertRow(row)
                    self.modify_table.setItem(row, 0, QTableWidgetItem(rule.channel))
                    self.modify_table.setItem(row, 1, QTableWidgetItem(f"0x{rule.can_id:03X}"))
                    
                    new_id_str = f"0x{rule.new_id:03X}" if rule.new_id is not None else "-"
                    self.modify_table.setItem(row, 2, QTableWidgetItem(new_id_str))
                    
                    mask_count = sum(rule.data_mask)
                    mask_str = f"{mask_count} bytes" if mask_count > 0 else "-"
                    self.modify_table.setItem(row, 3, QTableWidgetItem(mask_str))
                    
                    widget, enabled_check = self._create_centered_checkbox(True)
                    # Connect to apply changes immediately
                    enabled_check.stateChanged.connect(lambda state, r=row: self._on_modify_enabled_changed(r, state))
                    self.modify_table.setCellWidget(row, 4, widget)
            
            # Clear input
            self.modify_id_input.clear()
                
        except ValueError:
            QMessageBox.warning(self, t('error'), t('gateway_invalid_id'))
    
    def edit_modify_rule(self, item):
        """Edit existing modify rule"""
        row = item.row()
        if row >= len(self.config.modify_rules):
            return
        
        rule = self.config.modify_rules[row]
        
        # Show modify rule editor dialog with existing rule
        dialog = ModifyRuleDialog(self, rule.channel, rule.can_id, rule)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_rule = dialog.get_rule()
            self.config.modify_rules[row] = updated_rule
            
            # Update table
            self.modify_table.setItem(row, 0, QTableWidgetItem(updated_rule.channel))
            self.modify_table.setItem(row, 1, QTableWidgetItem(f"0x{updated_rule.can_id:03X}"))
            
            new_id_str = f"0x{updated_rule.new_id:03X}" if updated_rule.new_id is not None else "-"
            self.modify_table.setItem(row, 2, QTableWidgetItem(new_id_str))
            
            mask_count = sum(updated_rule.data_mask)
            mask_str = f"{mask_count} bytes" if mask_count > 0 else "-"
            self.modify_table.setItem(row, 3, QTableWidgetItem(mask_str))
    
    def remove_modify_rule(self):
        """Remove selected modify rule"""
        selected_rows = self.modify_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, t('warning'), t('gateway_select_rule'))
            return
        
        row = selected_rows[0].row()
        self.config.modify_rules.pop(row)
        self.modify_table.removeRow(row)
    
    def save_gateway_config(self):
        """Save gateway configuration to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            t('gateway_save_config'),
            "",
            "Gateway Config (*.gwcfg);;JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                # Get current config from UI
                current_config = self.get_config()
                
                # Create save data with file type
                data = {
                    'version': '1.0',
                    'file_type': 'gateway',
                    'gateway_config': current_config.to_dict()
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                import os
                filename_short = os.path.basename(filename)
                QMessageBox.information(
                    self,
                    t('success'),
                    t('gateway_config_saved').format(filename=filename_short)
                )
                
            except Exception as e:
                QMessageBox.critical(self, t('error'), f"Error saving: {str(e)}")
    
    def load_gateway_config(self):
        """Load gateway configuration from file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            t('gateway_load_config'),
            "",
            "Gateway Config (*.gwcfg);;JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                # Validate file type
                file_type = data.get('file_type', None)
                if file_type and file_type != 'gateway':
                    import os
                    filename_short = os.path.basename(filename)
                    
                    type_names = {
                        'tracer': t('file_type_tracer'),
                        'monitor': t('file_type_monitor'),
                        'transmit': t('file_type_transmit'),
                        'gateway': t('file_type_gateway')
                    }
                    
                    QMessageBox.warning(
                        self,
                        t('warning'),
                        t('msg_wrong_file_type').format(
                            filename=filename_short,
                            expected=type_names['gateway'],
                            found=type_names.get(file_type, file_type)
                        )
                    )
                    return
                
                # Load configuration
                gateway_data = data.get('gateway_config', {})
                self.config = GatewayConfig.from_dict(gateway_data)
                
                # Reload UI
                self.enable_gateway_check.setChecked(self.config.enabled)
                
                # Clear and reload tables
                self.routes_table.setRowCount(0)
                self.block_table.setRowCount(0)
                self.dynamic_table.setRowCount(0)
                self.modify_table.setRowCount(0)
                self.load_routes()
                self.load_rules()
                
                import os
                filename_short = os.path.basename(filename)
                QMessageBox.information(
                    self,
                    t('success'),
                    t('gateway_config_loaded').format(filename=filename_short)
                )
                
            except Exception as e:
                QMessageBox.critical(self, t('error'), f"Error loading: {str(e)}")
    
    def get_config(self):
        """Get the configured gateway settings"""
        # Update config from UI
        self.config.enabled = self.enable_gateway_check.isChecked()
        
        # Update routes enabled status
        for row in range(self.routes_table.rowCount()):
            widget = self.routes_table.cellWidget(row, 2)
            if widget and row < len(self.config.routes):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    self.config.routes[row].enabled = checkbox.isChecked()
        
        # Update enabled status from checkboxes
        for row in range(self.block_table.rowCount()):
            widget = self.block_table.cellWidget(row, 2)
            if widget and row < len(self.config.block_rules):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    self.config.block_rules[row].enabled = checkbox.isChecked()
        
        for row in range(self.dynamic_table.rowCount()):
            widget = self.dynamic_table.cellWidget(row, 4)
            if widget and row < len(self.config.dynamic_blocks):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    self.config.dynamic_blocks[row].enabled = checkbox.isChecked()
        
        for row in range(self.modify_table.rowCount()):
            widget = self.modify_table.cellWidget(row, 4)
            if widget and row < len(self.config.modify_rules):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    self.config.modify_rules[row].enabled = checkbox.isChecked()
        
        return self.config
