"""
Settings Dialog - Connection settings
"""

import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QPushButton,
    QGroupBox, QScrollArea, QWidget, QMessageBox, QFileDialog, QTabWidget,
    QRadioButton, QSpinBox,
)
from PyQt6.QtCore import Qt

from ..config import DEFAULT_CHANNEL
from ..i18n import get_i18n, t
from ..theme import get_adaptive_colors
from ..baudrate_detect_dialog import BaudrateDetectDialog
from ..storage_paths import get_default_saves_root_dir

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
        self.setMinimumWidth(480)
        
        layout = QVBoxLayout(self)
        
        # Get theme preference from config
        theme_pref = self.config.get('theme', 'system')
        colors = get_adaptive_colors(theme_pref)
        
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # --- Tab: General (language, theme, saves directory) ---
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
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
        general_layout.addWidget(language_group)
        
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
        general_layout.addWidget(theme_group)

        tx_startup_group = QGroupBox(t('settings_section_tx_startup'))
        tx_startup_layout = QVBoxLayout()
        tx_info = QLabel(t('settings_tx_startup_info'))
        tx_info.setStyleSheet(colors['info_text'])
        tx_info.setWordWrap(True)
        tx_startup_layout.addWidget(tx_info)

        self.tx_startup_show_radio = QRadioButton(t('settings_tx_startup_show'))
        self.tx_startup_hide_radio = QRadioButton(t('settings_tx_startup_hide'))
        if self.config.get('show_tx_panel_on_startup', True):
            self.tx_startup_show_radio.setChecked(True)
        else:
            self.tx_startup_hide_radio.setChecked(True)
        tx_row = QHBoxLayout()
        tx_row.addWidget(self.tx_startup_show_radio)
        tx_row.addWidget(self.tx_startup_hide_radio)
        tx_row.addStretch()
        tx_startup_layout.addLayout(tx_row)
        tx_startup_group.setLayout(tx_startup_layout)
        general_layout.addWidget(tx_startup_group)
        
        # Save Directory
        saves_group = QGroupBox("Save Directory")
        saves_layout = QVBoxLayout()

        saves_info = QLabel(
            "Base directory for saved files (TX, Monitor, Traces, FTCAN, OBD2, Gateway, etc.)."
        )
        saves_info.setStyleSheet(colors['info_text'])
        saves_info.setWordWrap(True)
        saves_layout.addWidget(saves_info)

        saves_row = QHBoxLayout()
        self.saves_base_dir_input = QLineEdit(self.config.get('saves_base_dir', ''))
        default_saves_dir = str(get_default_saves_root_dir())
        self.saves_base_dir_input.setPlaceholderText(default_saves_dir)
        self.saves_base_dir_input.setToolTip(
            f"Leave empty to use default: {default_saves_dir}"
        )
        saves_row.addWidget(self.saves_base_dir_input, 1)

        browse_saves_btn = QPushButton("Browse...")
        browse_saves_btn.clicked.connect(self._browse_saves_base_dir)
        saves_row.addWidget(browse_saves_btn)

        default_saves_btn = QPushButton("Use Default")
        default_saves_btn.clicked.connect(self._use_default_saves_dir)
        saves_row.addWidget(default_saves_btn)

        saves_layout.addLayout(saves_row)
        saves_group.setLayout(saves_layout)
        general_layout.addWidget(saves_group)

        updates_group = QGroupBox(t('settings_section_updates'))
        updates_layout = QVBoxLayout()
        updates_info = QLabel(t('settings_updates_info'))
        updates_info.setStyleSheet(colors['info_text'])
        updates_info.setWordWrap(True)
        updates_layout.addWidget(updates_info)

        self.check_updates_on_startup_check = QCheckBox(t('label_check_updates_on_startup'))
        self.check_updates_on_startup_check.setChecked(
            self.config.get('check_updates_on_startup', True)
        )
        self.check_updates_on_startup_check.setToolTip(t('tooltip_check_updates_on_startup'))
        updates_layout.addWidget(self.check_updates_on_startup_check)

        updates_group.setLayout(updates_layout)
        general_layout.addWidget(updates_group)
        
        general_layout.addStretch()
        tabs.addTab(general_tab, t('settings_tab_general'))
        
        # --- Tab: CAN bus (simulation mode, multi-CAN) ---
        can_tab = QWidget()
        can_layout = QVBoxLayout(can_tab)
        
        self.simulation_mode_check = QCheckBox(t('label_simulation_mode'))
        self.simulation_mode_check.setChecked(self.config.get('simulation_mode', False))
        self.simulation_mode_check.setToolTip(t('tooltip_simulation_mode'))
        can_layout.addWidget(self.simulation_mode_check)
        
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
                'name': DEFAULT_CHANNEL,
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
        can_layout.addWidget(multican_group)

        # --- Performance limits (UI can be slower than the bus) ---
        perf_group = QGroupBox(t('settings_section_performance'))
        perf_layout = QVBoxLayout()

        perf_info = QLabel(t('settings_perf_info'))
        perf_info.setStyleSheet(colors['info_text'])
        perf_info.setWordWrap(True)
        perf_layout.addWidget(perf_info)

        tracer_row = QHBoxLayout()
        tracer_row.addWidget(QLabel(t('label_max_tracer_rows') + ":"))
        self.max_tracer_rows_input = QSpinBox()
        self.max_tracer_rows_input.setRange(0, 1_000_000)
        self.max_tracer_rows_input.setSingleStep(5000)
        self.max_tracer_rows_input.setValue(
            self.config.get('max_tracer_rows', 20000)
        )
        self.max_tracer_rows_input.setToolTip(t('tooltip_max_tracer_rows'))
        self.max_tracer_rows_input.setMaximumWidth(140)
        tracer_row.addWidget(self.max_tracer_rows_input)
        tracer_row.addStretch()
        perf_layout.addLayout(tracer_row)

        queue_row = QHBoxLayout()
        queue_row.addWidget(QLabel(t('label_rx_queue_size') + ":"))
        self.rx_queue_size_input = QSpinBox()
        self.rx_queue_size_input.setRange(1000, 1_000_000)
        self.rx_queue_size_input.setSingleStep(5000)
        self.rx_queue_size_input.setValue(
            self.config.get('rx_queue_size', 50000)
        )
        self.rx_queue_size_input.setToolTip(t('tooltip_rx_queue_size'))
        self.rx_queue_size_input.setMaximumWidth(140)
        queue_row.addWidget(self.rx_queue_size_input)
        queue_row.addStretch()
        perf_layout.addLayout(queue_row)

        perf_group.setLayout(perf_layout)
        can_layout.addWidget(perf_group)

        can_layout.addStretch()
        tabs.addTab(can_tab, t('settings_tab_can_bus'))
        
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

        # Row 5: SocketCAN link setup
        bring_up_check = QCheckBox(t('multican_bring_up'))
        bring_up_check.setChecked(bus_config.get('bring_up', False))
        bring_up_check.setToolTip(t('tooltip_bring_up'))
        bus_layout.addWidget(bring_up_check)

        socketcan_info = QLabel(t('multican_bring_up_info'))
        socketcan_info.setStyleSheet("color: gray; font-size: 10px;")
        socketcan_info.setWordWrap(True)
        bus_layout.addWidget(socketcan_info)

        bus_widget.setLayout(bus_layout)
        
        # Store references to inputs
        bus_widget.name_input = name_input
        bus_widget.channel_input = channel_input
        bus_widget.baudrate_combo = baudrate_combo
        bus_widget.listen_only_check = listen_only_check
        bus_widget.com_baudrate_combo = com_baudrate_combo
        bus_widget.rts_hs_check = rts_hs_check
        bus_widget.bring_up_check = bring_up_check
        
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
        # Linux: list real SocketCAN interfaces first (cheap, no root needed).
        try:
            from ..can_interface_setup import list_can_interfaces, sys_is_linux

            links = list_can_interfaces() if sys_is_linux() else []
        except Exception as e:
            print(f"Could not list CAN interfaces: {e}")
            links = []

        if links:
            existing = {channel_input.itemText(i) for i in range(channel_input.count())}
            for link in links:
                if link.name not in existing:
                    channel_input.addItem(link.name)
            channel_input.setToolTip(
                "\n".join(f"{link.name}: {link.summary}" for link in links)
            )
            if channel_input.currentText() not in {link.name for link in links}:
                channel_input.setCurrentText(links[0].name)

        if not self.usb_monitor:
            if links:
                return
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
                # Update combo with the detected baudrate
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

    @staticmethod
    def _parse_com_baudrate(value: str) -> int:
        """'115200 bit/s' -> 115200 (0 when unparsable)."""
        try:
            return int(str(value).split()[0])
        except (ValueError, IndexError):
            return 0

    def _browse_saves_base_dir(self):
        """Browse for saves base directory."""
        start_dir = self.saves_base_dir_input.text().strip() or str(get_default_saves_root_dir())
        selected = QFileDialog.getExistingDirectory(self, "Select Saves Base Directory", start_dir)
        if selected:
            self.saves_base_dir_input.setText(selected)

    def _use_default_saves_dir(self):
        """Reset saves directory to application default."""
        self.saves_base_dir_input.setText("")
    
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
                'bring_up': widget.bring_up_check.isChecked(),
                'com_baudrate': com_baudrate,
                'tty_baudrate': self._parse_com_baudrate(com_baudrate),
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
            'saves_base_dir': self.saves_base_dir_input.text().strip(),
            'check_updates_on_startup': self.check_updates_on_startup_check.isChecked(),
            'show_tx_panel_on_startup': self.tx_startup_show_radio.isChecked(),
            'simulation_mode': self.simulation_mode_check.isChecked(),
            'max_tracer_rows': self.max_tracer_rows_input.value(),
            'rx_queue_size': self.rx_queue_size_input.value(),
            'can_buses': can_buses
        }
