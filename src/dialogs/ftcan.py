"""
FTCAN Dialog - Interface for FTCAN 2.0 protocol analysis
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QTextEdit, QCheckBox, QSpinBox,
    QHeaderView, QComboBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from typing import List, Dict, Optional
from ..models import CANMessage
from ..decoders.decoder_ftcan import FTCANDecoder, MEASURE_IDS


class FTCANDialog(QDialog):
    """Dialog for FTCAN 2.0 message analysis"""
    
    def __init__(self, parent=None, buses_1mbps=None):
        super().__init__(parent)
        self.setWindowTitle("FTCAN 2.0 Protocol Analyzer")
        self.resize(1200, 800)
        
        self.decoder = FTCANDecoder()
        self.messages: List[CANMessage] = []
        self.auto_decode = True
        
        # Buses available at 1 Mbps
        self.buses_1mbps = buses_1mbps or []
        self.selected_bus = self.buses_1mbps[0][0] if self.buses_1mbps else None
        
        self._setup_ui()
        
        # Timer for automatic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Update every 500ms
    
    def _setup_ui(self):
        """Configura interface"""
        layout = QVBoxLayout()
        
        # Header with information
        header = self._create_header()
        layout.addWidget(header)
        
        # Tabs
        tabs = QTabWidget()
        
        # Tab 1: Mensagens decodificadas
        tab_messages = self._create_messages_tab()
        tabs.addTab(tab_messages, "Decoded Messages")
        
        # Tab 2: Medidas em tempo real
        tab_measures = self._create_measures_tab()
        tabs.addTab(tab_measures, "Live Measures")
        
        # Tab 3: Diagnóstico
        tab_diagnostics = self._create_diagnostics_tab()
        tabs.addTab(tab_diagnostics, "Diagnostics")
        
        layout.addWidget(tabs)
        
        # Footer with controls
        footer = self._create_footer()
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QWidget:
        """Create header with information"""
        group = QGroupBox("FTCAN 2.0 Protocol Information")
        main_layout = QVBoxLayout()
        
        # Top row: Title on left, Bus selector on right
        top_layout = QHBoxLayout()
        
        # Left side: Protocol title
        title_label = QLabel("<b style='font-size: 14px;'>FuelTech CAN Protocol</b>")
        top_layout.addWidget(title_label)
        
        top_layout.addStretch()
        
        # Right side: Channel selector with status
        right_layout = QHBoxLayout()
        
        # Debug log
        print(f"[FTCAN Dialog] Number of 1Mbps buses: {len(self.buses_1mbps)}")
        for i, (name, bus) in enumerate(self.buses_1mbps):
            print(f"  [{i}] {name}: connected={bus.connected}, baudrate={bus.config.baudrate}")
        
        if len(self.buses_1mbps) > 1:
            # Multiple buses - show dropdown
            right_layout.addWidget(QLabel("<b>Channel:</b>"))
            self.bus_combo = QComboBox()
            self.bus_combo.setMinimumWidth(180)
            for bus_name, bus in self.buses_1mbps:
                if bus.connected:
                    self.bus_combo.addItem(f"{bus_name} - Connected")
                else:
                    self.bus_combo.addItem(f"{bus_name} - Simulation")
            self.bus_combo.currentIndexChanged.connect(self._on_bus_changed)
            right_layout.addWidget(self.bus_combo)
        elif len(self.buses_1mbps) == 1:
            # Single bus - show as label with colored status
            bus_name, bus = self.buses_1mbps[0]
            if bus.connected:
                status_html = "<span style='color: green; font-weight: bold;'>Connected</span>"
            else:
                status_html = "<span style='color: #0066cc; font-weight: bold;'>Simulation</span>"
            bus_label = QLabel(f"<b>Channel:</b> {bus_name} - {status_html}")
            right_layout.addWidget(bus_label)
        else:
            # No bus available
            status_html = "<span style='color: red; font-weight: bold;'>Disconnected</span>"
            bus_label = QLabel(f"<b>Channel:</b> {status_html}")
            right_layout.addWidget(bus_label)
        
        top_layout.addLayout(right_layout)
        main_layout.addLayout(top_layout)
        
        # Add separator line
        line = QLabel()
        line.setFrameStyle(QLabel.Shape.HLine | QLabel.Shadow.Sunken)
        main_layout.addWidget(line)
        
        # Protocol information
        info_text = QLabel(
            "• Physical Layer: CAN 2.0B Extended (29-bit ID)<br>"
            "• Baudrate: <b>1 Mbps</b> (1000000 bit/s)<br>"
            "• Data Format: Big-endian, signed 16-bit values<br>"
            "• Supported Devices: WB-O2 Nano, ECUs, Sensors"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #555; font-size: 11px;")
        main_layout.addWidget(info_text)
        
        group.setLayout(main_layout)
        return group
    
    def _on_bus_changed(self, index: int):
        """Callback when selected bus changes"""
        if index >= 0 and index < len(self.buses_1mbps):
            self.selected_bus = self.buses_1mbps[index][0]
    
    def _create_messages_tab(self) -> QWidget:
        """Cria tab de mensagens decodificadas"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Tabela de mensagens
        self.messages_table = QTableWidget()
        self.messages_table.setColumnCount(8)
        self.messages_table.setHorizontalHeaderLabels([
            "Timestamp", "CAN ID", "Product", "Data Field", 
            "Message ID", "Measures", "Status", "Raw Data"
        ])
        
        header = self.messages_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        
        self.messages_table.itemSelectionChanged.connect(self._on_message_selected)
        layout.addWidget(self.messages_table)
        
        # Detalhes da mensagem selecionada
        details_group = QGroupBox("Message Details")
        details_layout = QVBoxLayout()
        
        self.message_details = QTextEdit()
        self.message_details.setReadOnly(True)
        self.message_details.setMaximumHeight(150)
        font = QFont("Courier New", 9)
        self.message_details.setFont(font)
        details_layout.addWidget(self.message_details)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_measures_tab(self) -> QWidget:
        """Cria tab de medidas em tempo real"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Filtro de dispositivo
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Device:"))
        
        self.device_filter = QComboBox()
        self.device_filter.addItem("All Devices")
        self.device_filter.currentTextChanged.connect(self._update_measures_display)
        filter_layout.addWidget(self.device_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Tabela de medidas
        self.measures_table = QTableWidget()
        self.measures_table.setColumnCount(6)
        self.measures_table.setHorizontalHeaderLabels([
            "Device", "Measure", "Value", "Unit", "Raw Value", "Last Update"
        ])
        
        header = self.measures_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.measures_table)
        
        widget.setLayout(layout)
        return widget
    
    def _create_diagnostics_tab(self) -> QWidget:
        """Create diagnostics tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("No data yet")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Dispositivos detectados
        devices_group = QGroupBox("Detected Devices")
        devices_layout = QVBoxLayout()
        
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(5)
        self.devices_table.setHorizontalHeaderLabels([
            "Product ID", "Product Name", "Unique ID", "Message Count", "Last Seen"
        ])
        
        header = self.devices_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        devices_layout.addWidget(self.devices_table)
        devices_group.setLayout(devices_layout)
        layout.addWidget(devices_group)
        
        # Problemas detectados
        issues_group = QGroupBox("Detected Issues")
        issues_layout = QVBoxLayout()
        
        self.issues_text = QTextEdit()
        self.issues_text.setReadOnly(True)
        self.issues_text.setMaximumHeight(150)
        issues_layout.addWidget(self.issues_text)
        
        issues_group.setLayout(issues_layout)
        layout.addWidget(issues_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_footer(self) -> QWidget:
        """Create footer with controls"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        # Auto-decode
        self.auto_decode_check = QCheckBox("Auto-decode")
        self.auto_decode_check.setChecked(True)
        self.auto_decode_check.stateChanged.connect(self._on_auto_decode_changed)
        layout.addWidget(self.auto_decode_check)
        
        layout.addStretch()
        
        # Botões
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_data)
        layout.addWidget(clear_btn)
        
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_data)
        layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        widget.setLayout(layout)
        return widget
    
    def add_message(self, msg: CANMessage):
        """Add message for analysis"""
        # Verifica se é mensagem FTCAN
        if not FTCANDecoder.is_ftcan_message(msg.can_id):
            return
        
        # Filtra por bus selecionado (se houver múltiplos)
        if self.selected_bus and hasattr(msg, 'source') and msg.source != self.selected_bus:
            return
        
        self.messages.append(msg)
        
        # Limita buffer
        if len(self.messages) > 1000:
            self.messages = self.messages[-1000:]
    
    def _update_display(self):
        """Atualiza display com novas mensagens"""
        if not self.auto_decode:
            return
        
        # Atualiza tabela de mensagens
        self._update_messages_table()
        
        # Atualiza medidas
        self._update_measures_display()
        
        # Atualiza diagnóstico
        self._update_diagnostics()
    
    def _update_messages_table(self):
        """Atualiza tabela de mensagens"""
        # Pega últimas 100 mensagens
        recent_messages = self.messages[-100:]
        
        self.messages_table.setRowCount(len(recent_messages))
        
        for row, msg in enumerate(recent_messages):
            decoded = self.decoder.decode_message(msg.can_id, msg.data)
            
            # Timestamp
            self.messages_table.setItem(row, 0, QTableWidgetItem(f"{msg.timestamp:.3f}"))
            
            # CAN ID
            self.messages_table.setItem(row, 1, QTableWidgetItem(f"0x{msg.can_id:08X}"))
            
            # Product
            if decoded['identification']:
                product = decoded['identification']['product_name']
                self.messages_table.setItem(row, 2, QTableWidgetItem(product))
                
                # Data Field
                data_field = decoded['identification']['data_field_name']
                self.messages_table.setItem(row, 3, QTableWidgetItem(data_field))
                
                # Message ID
                msg_id = decoded['identification']['message_id']
                self.messages_table.setItem(row, 4, QTableWidgetItem(msg_id))
            
            # Measures
            measure_count = len(decoded.get('measures', []))
            self.messages_table.setItem(row, 5, QTableWidgetItem(str(measure_count)))
            
            # Status
            status = "Complete" if decoded.get('is_complete') else "Incomplete"
            if decoded.get('error'):
                status = f"Error: {decoded['error']}"
            
            status_item = QTableWidgetItem(status)
            if decoded.get('error'):
                status_item.setForeground(QColor(255, 0, 0))
            elif decoded.get('is_complete'):
                status_item.setForeground(QColor(0, 150, 0))
            
            self.messages_table.setItem(row, 6, status_item)
            
            # Raw Data
            self.messages_table.setItem(row, 7, QTableWidgetItem(msg.to_hex_string()))
    
    def _update_measures_display(self):
        """Atualiza display de medidas"""
        # Coleta todas as medidas das mensagens recentes
        measures_dict = {}  # {(device, measure_name): (value, unit, raw, timestamp)}
        
        for msg in self.messages[-100:]:
            decoded = self.decoder.decode_message(msg.can_id, msg.data)
            
            if not decoded['identification'] or not decoded.get('measures'):
                continue
            
            device = decoded['identification']['product_name']
            
            for measure in decoded['measures']:
                key = (device, measure['name'])
                measures_dict[key] = (
                    measure['real_value'],
                    measure['unit'],
                    measure['raw_value'],
                    msg.timestamp
                )
        
        # Aplica filtro antes de contar linhas
        current_filter = self.device_filter.currentText()
        filtered_items = []
        
        for (device, measure_name), (value, unit, raw, timestamp) in sorted(measures_dict.items()):
            if current_filter != "All Devices" and device != current_filter:
                continue
            filtered_items.append(((device, measure_name), (value, unit, raw, timestamp)))
        
        # Atualiza tabela com itens filtrados
        self.measures_table.setRowCount(len(filtered_items))
        
        for row, ((device, measure_name), (value, unit, raw, timestamp)) in enumerate(filtered_items):
            self.measures_table.setItem(row, 0, QTableWidgetItem(device))
            self.measures_table.setItem(row, 1, QTableWidgetItem(measure_name))
            self.measures_table.setItem(row, 2, QTableWidgetItem(f"{value:.3f}"))
            self.measures_table.setItem(row, 3, QTableWidgetItem(unit))
            self.measures_table.setItem(row, 4, QTableWidgetItem(str(raw)))
            self.measures_table.setItem(row, 5, QTableWidgetItem(f"{timestamp:.3f}s"))
        
        # Atualiza filtro de dispositivos (sem recursão)
        self._update_device_filter_safe()
    
    def _update_device_filter_safe(self):
        """Update device list in filter (no recursion)"""
        # Bloqueia sinais temporariamente para evitar recursão
        self.device_filter.blockSignals(True)
        
        current = self.device_filter.currentText()
        
        devices = set()
        for msg in self.messages:
            decoded = self.decoder.decode_message(msg.can_id, msg.data)
            if decoded['identification']:
                devices.add(decoded['identification']['product_name'])
        
        self.device_filter.clear()
        self.device_filter.addItem("All Devices")
        for device in sorted(devices):
            self.device_filter.addItem(device)
        
        # Restaura seleção
        index = self.device_filter.findText(current)
        if index >= 0:
            self.device_filter.setCurrentIndex(index)
        
        # Reativa sinais
        self.device_filter.blockSignals(False)
    
    def _update_diagnostics(self):
        """Update diagnostic information"""
        if not self.messages:
            return
        
        # Estatísticas gerais
        total_messages = len(self.messages)
        ftcan_messages = sum(1 for msg in self.messages if FTCANDecoder.is_ftcan_message(msg.can_id))
        
        # Dispositivos únicos
        devices = {}
        for msg in self.messages:
            decoded = self.decoder.decode_message(msg.can_id, msg.data)
            if decoded['identification']:
                product_id = decoded['identification']['product_id']
                product_name = decoded['identification']['product_name']
                
                if product_id not in devices:
                    devices[product_id] = {
                        'name': product_name,
                        'unique_id': decoded['identification']['unique_id'],
                        'count': 0,
                        'last_seen': 0
                    }
                
                devices[product_id]['count'] += 1
                devices[product_id]['last_seen'] = msg.timestamp
        
        # Atualiza estatísticas
        stats_text = f"""
<b>Total Messages:</b> {total_messages}<br>
<b>FTCAN Messages:</b> {ftcan_messages}<br>
<b>Unique Devices:</b> {len(devices)}<br>
<b>Time Span:</b> {self.messages[-1].timestamp - self.messages[0].timestamp:.2f}s
        """
        self.stats_label.setText(stats_text)
        
        # Update devices table
        self.devices_table.setRowCount(len(devices))
        
        row = 0
        for product_id, info in sorted(devices.items()):
            self.devices_table.setItem(row, 0, QTableWidgetItem(product_id))
            self.devices_table.setItem(row, 1, QTableWidgetItem(info['name']))
            self.devices_table.setItem(row, 2, QTableWidgetItem(str(info['unique_id'])))
            self.devices_table.setItem(row, 3, QTableWidgetItem(str(info['count'])))
            self.devices_table.setItem(row, 4, QTableWidgetItem(f"{info['last_seen']:.3f}s"))
            row += 1
        
        # Detecta problemas
        self._detect_issues()
    
    def _detect_issues(self):
        """Detect communication issues"""
        issues = []
        
        if not self.messages:
            self.issues_text.setText("No messages to analyze")
            return
        
        # Verifica se há mensagens FTCAN
        ftcan_count = sum(1 for msg in self.messages if FTCANDecoder.is_ftcan_message(msg.can_id))
        
        if ftcan_count == 0:
            issues.append("⚠️ No FTCAN messages detected!")
            issues.append("   - Check if baudrate is set to 1 Mbps (1000000 bit/s)")
            issues.append("   - Verify CAN bus termination (120Ω resistors)")
            issues.append("   - Check if device is powered and connected")
        
        # Verifica se há WB-O2 Nano
        has_wbo2 = False
        for msg in self.messages:
            decoded = self.decoder.decode_message(msg.can_id, msg.data)
            if decoded['identification']:
                if 'WBO2_NANO' in decoded['identification']['product_name']:
                    has_wbo2 = True
                    break
        
        if not has_wbo2 and ftcan_count > 0:
            issues.append("ℹ️ No WB-O2 Nano detected")
            issues.append("   - Device may not be associated with ECU")
            issues.append("   - Check CAN wiring (White/Red = CAN+, Yellow/Blue = CAN-)")
        
        # Verifica segmentação incompleta
        incomplete_segments = sum(
            1 for msg in self.messages[-100:]
            if not self.decoder.decode_message(msg.can_id, msg.data).get('is_complete', True)
        )
        
        if incomplete_segments > 0:
            issues.append(f"⚠️ {incomplete_segments} incomplete segmented packets")
            issues.append("   - Possible message loss or buffer overflow")
        
        if not issues:
            issues.append("✅ No issues detected")
        
        self.issues_text.setText("\n".join(issues))
    
    def _on_message_selected(self):
        """Callback when message is selected"""
        selected_rows = self.messages_table.selectedItems()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if row >= len(self.messages):
            return
        
        msg = self.messages[-(len(self.messages) - row)]
        decoded = self.decoder.decode_message(msg.can_id, msg.data)
        
        # Formata detalhes
        details = []
        details.append(f"=== Message Details ===")
        details.append(f"Timestamp: {msg.timestamp:.6f}s")
        details.append(f"CAN ID: 0x{msg.can_id:08X} (29-bit)")
        details.append(f"DLC: {msg.dlc}")
        details.append(f"Data: {msg.to_hex_string()}")
        details.append("")
        
        if decoded['identification']:
            ident = decoded['identification']
            details.append(f"=== FTCAN Identification ===")
            details.append(f"Product: {ident['product_name']}")
            details.append(f"Product ID: {ident['product_id']} (Type: {ident['product_type_id']}, Unique: {ident['unique_id']})")
            details.append(f"Data Field: {ident['data_field_name']} ({ident['data_field_id']})")
            details.append(f"Message ID: {ident['message_id']}")
            details.append(f"Is Response: {ident['is_response']}")
            details.append("")
        
        if decoded.get('measures'):
            details.append(f"=== Measures ({len(decoded['measures'])}) ===")
            for measure in decoded['measures']:
                details.append(f"• {measure['formatted']}")
                details.append(f"  MeasureID: {measure['measure_id']}, DataID: {measure['data_id']}")
            details.append("")
        
        if decoded.get('error'):
            details.append(f"=== Error ===")
            details.append(decoded['error'])
        
        self.message_details.setText("\n".join(details))
    
    def _on_auto_decode_changed(self, state):
        """Callback quando auto-decode muda"""
        self.auto_decode = (state == Qt.CheckState.Checked.value)
    
    def _clear_data(self):
        """Limpa dados"""
        self.messages.clear()
        self.decoder.clear_segmented_buffers()
        self.messages_table.setRowCount(0)
        self.measures_table.setRowCount(0)
        self.devices_table.setRowCount(0)
        self.message_details.clear()
        self.stats_label.setText("No data yet")
        self.issues_text.clear()
    
    def _export_data(self):
        """Exporta dados decodificados"""
        # TODO: Implement export
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Export", "Export feature coming soon!")
