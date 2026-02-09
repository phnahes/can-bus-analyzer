"""
Settings Dialog - Connection settings
"""

import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QPushButton,
    QGroupBox, QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt

from ..i18n import get_i18n, t
from ..theme import get_adaptive_colors
from ..baudrate_detect_dialog import BaudrateDetectDialog

from .usb_device_dialog import USBDeviceSelectionDialog


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
            'language': selected_language,
            'theme': selected_theme,
            'simulation_mode': self.simulation_mode_check.isChecked(),
            'can_buses': can_buses
        }
