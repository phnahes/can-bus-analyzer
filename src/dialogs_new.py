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
        
        # CAN Connection Settings
        can_group = QGroupBox("CAN Connection")
        can_layout = QVBoxLayout()
        
        # CAN Device
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("CAN Device:"))
        self.device_combo = QComboBox()
        # Default device suggestions (platform-specific)
        import sys
        if sys.platform == "win32":
            default_devices = ["COM1", "COM3", "COM4", "can0", "vcan0"]
        elif sys.platform == "linux":
            default_devices = ["/dev/ttyUSB0", "/dev/ttyACM0", "can0", "vcan0"]
        else:
            default_devices = ["/dev/cu.usbserial", "/dev/cu.usbmodem", "can0", "vcan0"]
        self.device_combo.addItems(default_devices)
        self.device_combo.setEditable(True)
        default_channel = self.config.get('channel') or ("COM1" if sys.platform == "win32" else "can0")
        self.device_combo.setCurrentText(default_channel)
        device_layout.addWidget(self.device_combo, 1)
        
        # Botão Scan Devices
        self.scan_btn = QPushButton(t('btn_scan_devices'))
        self.scan_btn.clicked.connect(self.scan_devices)
        device_layout.addWidget(self.scan_btn)
        
        can_layout.addLayout(device_layout)
        
        # COM Baudrate
        com_baud_layout = QHBoxLayout()
        com_baud_layout.addWidget(QLabel("COM Baudrate:"))
        self.com_baudrate_combo = QComboBox()
        self.com_baudrate_combo.addItems([
            "9600 bit/s", "19200 bit/s", "38400 bit/s", 
            "57600 bit/s", "115200 bit/s"
        ])
        self.com_baudrate_combo.setCurrentText("115200 bit/s")
        com_baud_layout.addWidget(self.com_baudrate_combo)
        can_layout.addLayout(com_baud_layout)
        
        # CAN Baudrate
        can_baud_layout = QHBoxLayout()
        can_baud_layout.addWidget(QLabel("CAN Baudrate:"))
        self.can_baudrate_combo = QComboBox()
        self.can_baudrate_combo.addItems([
            "125 Kbit/s", "250 Kbit/s", "500 Kbit/s", "1000 Kbit/s"
        ])
        baudrate = self.config.get('baudrate', 500000)
        self.can_baudrate_combo.setCurrentText(f"{baudrate//1000} Kbit/s")
        can_baud_layout.addWidget(self.can_baudrate_combo)
        can_layout.addLayout(can_baud_layout)
        
        # Checkboxes
        self.rts_hs_check = QCheckBox("RTS HS")
        can_layout.addWidget(self.rts_hs_check)
        
        self.listen_only_check = QCheckBox("Listen Only")
        self.listen_only_check.setChecked(self.config.get('listen_only', True))
        can_layout.addWidget(self.listen_only_check)
        
        self.timestamp_check = QCheckBox("Time Stamp")
        self.timestamp_check.setChecked(True)
        can_layout.addWidget(self.timestamp_check)
        
        # Simulation Mode checkbox
        self.simulation_mode_check = QCheckBox(t('label_simulation_mode'))
        self.simulation_mode_check.setChecked(self.config.get('simulation_mode', False))
        self.simulation_mode_check.setToolTip(t('tooltip_simulation_mode'))
        can_layout.addWidget(self.simulation_mode_check)
        
        # Baudrate Register
        baud_reg_layout = QHBoxLayout()
        baud_reg_layout.addWidget(QLabel("Baudrate Reg:"))
        self.baudrate_reg_input = QLineEdit("FFFFFF")
        self.baudrate_reg_input.setMaximumWidth(100)
        baud_reg_layout.addWidget(self.baudrate_reg_input)
        baud_reg_layout.addStretch()
        can_layout.addLayout(baud_reg_layout)
        
        # Info text
        info_label = QLabel("<BRGCON1>;<BRGCON2>;<BRGCON3> (canhack)\n<BTR0>;<BTR1> (Lawicel, Peak)")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        can_layout.addWidget(info_label)
        
        # Close CAN group
        can_group.setLayout(can_layout)
        layout.addWidget(can_group)
        
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
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def scan_devices(self):
        """Abre diálogo de seleção de dispositivos USB"""
        if not self.usb_monitor:
            QMessageBox.warning(self, t('warning'), t('msg_usb_monitor_not_available'))
            return
        
        dialog = USBDeviceSelectionDialog(self, self.usb_monitor)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            device = dialog.selected_device
            if device:
                # Atualizar combo box com o dispositivo selecionado
                self.device_combo.setCurrentText(device.path)
                
                # Informar ao usuário
                QMessageBox.information(
                    self,
                    t('dialog_usb_device_title'),
                    f"{t('msg_device_connected').format(device=device.name)}\n\n"
                    f"Path: {device.path}\n"
                    f"Description: {device.description}"
                )
    
    def get_config(self):
        """Retorna configuração atualizada"""
        baudrate_str = self.can_baudrate_combo.currentText().split()[0]
        selected_language = self.language_combo.currentData()
        
        return {
            'channel': self.device_combo.currentText(),
            'baudrate': int(baudrate_str) * 1000,
            'com_baudrate': self.com_baudrate_combo.currentText(),
            'listen_only': self.listen_only_check.isChecked(),
            'timestamp': self.timestamp_check.isChecked(),
            'rts_hs': self.rts_hs_check.isChecked(),
            'baudrate_reg': self.baudrate_reg_input.text(),
            'language': selected_language,
            'simulation_mode': self.simulation_mode_check.isChecked()
        }


class BitFieldViewerDialog(QDialog):
    """Dialog para visualizar bits individuais de uma mensagem CAN"""
    def __init__(self, parent=None, message: CANMessage = None):
        super().__init__(parent)
        self.message = message
        self.bit_labels = {}
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
            bit_widget.setStyleSheet(
                f"background-color: {'#4CAF50' if bit_value else '#f44336'}; "
                f"color: white; font-weight: bold; font-size: 16px; "
                f"padding: 10px; border-radius: 5px;"
            )
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
        
        id_help = QLabel("Enter CAN IDs (hex) separated by commas or spaces\nExample: 0x280, 0x284, 0x300-0x310")
        id_help.setStyleSheet("color: gray; font-size: 10px;")
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
        
        # Data Filters
        data_group = QGroupBox("Data Filters (Advanced)")
        data_layout = QVBoxLayout()
        
        data_help = QLabel("Filter by data content (hex)\nExample: Byte 0 = FF, Byte 2 = 00")
        data_help.setStyleSheet("color: gray; font-size: 10px;")
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
            'show_only': self.show_only_radio.isChecked()
        }


class TriggerDialog(QDialog):
    """Dialog para configurar triggers de transmissão automática"""
    def __init__(self, parent=None, triggers=None):
        super().__init__(parent)
        self.triggers = triggers or []
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
        info_label.setStyleSheet("color: gray; font-size: 11px; padding: 10px;")
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
        example_text.setStyleSheet("color: gray; font-size: 10px;")
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
