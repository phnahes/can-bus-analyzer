"""
FTCAN Dialog - Interface for FTCAN 2.0 protocol analysis
"""

import json
import threading
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QTextEdit, QCheckBox, QSpinBox,
    QHeaderView, QComboBox, QTabWidget, QWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor
from typing import List, Dict, Optional
from ..models import CANMessage
from ..decoders.decoder_ftcan import FTCANDecoder, MEASURE_IDS
from ..i18n import t


class DecoderWorker(QObject):
    """Worker thread for decoding messages with priority queue"""
    decoded_ready = pyqtSignal(int, dict)  # (message_index, decoded_data)
    
    def __init__(self, worker_id: int = 0):
        super().__init__()
        self.worker_id = worker_id
        self.decoder = FTCANDecoder()
        self.running = True
        self.priority_queue = []  # High priority (broadcast messages with measures)
        self.normal_queue = []    # Normal priority
        self.lock = threading.Lock()
        self.event = threading.Event()
    
    def add_decode_task(self, msg_index: int, msg: CANMessage, priority: bool = False):
        """Add message to decode queue with priority"""
        with self.lock:
            if priority:
                self.priority_queue.append((msg_index, msg))
            else:
                self.normal_queue.append((msg_index, msg))
        self.event.set()  # Wake up worker thread
    
    def process_queue(self):
        """Process decode queue (runs in thread) - priority first"""
        while self.running:
            tasks = []
            with self.lock:
                # Process priority queue first (up to 150 for faster real-time)
                if self.priority_queue:
                    tasks = self.priority_queue[:150]
                    self.priority_queue = self.priority_queue[150:]
                # Then normal queue (up to 500 for throughput)
                elif self.normal_queue:
                    tasks = self.normal_queue[:500]
                    self.normal_queue = self.normal_queue[500:]
            
            if tasks:
                for msg_index, msg in tasks:
                    try:
                        decoded = self.decoder.decode_message(msg.can_id, msg.data)
                        self.decoded_ready.emit(msg_index, decoded)
                    except Exception as e:
                        print(f"Worker {self.worker_id} error: {e}")
            else:
                # Wait for new tasks (with shorter timeout for responsiveness)
                self.event.wait(0.02)
                self.event.clear()
    
    def get_queue_size(self) -> tuple:
        """Get queue sizes (priority, normal)"""
        with self.lock:
            return len(self.priority_queue), len(self.normal_queue)
    
    def stop(self):
        """Stop worker"""
        self.running = False
        self.event.set()  # Wake up to exit


class FTCANDialog(QDialog):
    """Dialog for FTCAN 2.0 message analysis"""
    
    def __init__(self, parent=None, buses_1mbps=None):
        super().__init__(parent)
        self.setWindowTitle("FTCAN 2.0 Protocol Analyzer")
        self.resize(1200, 800)
        
        self.decoder = FTCANDecoder()
        self.messages: List[CANMessage] = []
        self.decoded_cache: Dict[int, Dict] = {}  # Cache: {msg_index: decoded_data}
        self.auto_decode = True
        self.last_processed_index = -1  # Track last processed message
        self.last_display_update = 0  # Track last message count when display was updated
        self.needs_full_update = False  # Flag for full update (diagnostics, devices)
        self.update_counter = 0  # Counter for periodic full updates
        self.product_type_filter_value = None  # Current filter value
        
        # Buses available at 1 Mbps
        self.buses_1mbps = buses_1mbps or []
        self.selected_bus = self.buses_1mbps[0][0] if self.buses_1mbps else None
        
        # Multiple background decoder workers for parallel processing
        self.num_workers = 4  # 4 workers for maximum throughput
        self.decoder_workers = []
        self.decoder_threads = []
        self.current_worker = 0  # Round-robin worker selection
        self.auto_scroll_enabled = True  # Auto-scroll messages table
        
        for i in range(self.num_workers):
            worker = DecoderWorker(worker_id=i)
            worker.decoded_ready.connect(self._on_decoded_ready)
            thread = threading.Thread(target=worker.process_queue, daemon=True)
            thread.start()
            
            self.decoder_workers.append(worker)
            self.decoder_threads.append(thread)
        
        self._setup_ui()
        
        # Timer for automatic updates - optimized for real-time
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(100)  # Check every 100ms for better real-time feel
    
    def _setup_ui(self):
        """Configura interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)  # Reduce margins from default
        layout.setSpacing(6)  # Reduce spacing between widgets
        
        # Header with information
        header = self._create_header()
        layout.addWidget(header)
        
        # Auto-decode control with warning message on the right
        control_layout = QHBoxLayout()
        
        self.auto_decode_check = QCheckBox("Auto-decode")
        self.auto_decode_check.setChecked(True)
        self.auto_decode_check.stateChanged.connect(self._on_auto_decode_changed)
        control_layout.addWidget(self.auto_decode_check)
        
        control_layout.addStretch()
        
        # Warning message (right side)
        warning_label = QLabel(
            "ℹ️ <i>Note: Due to high message volume, the Decoded Messages tab may be slower on some computers. "
            "Use Live Measures tab for real-time data.</i>"
        )
        warning_label.setStyleSheet("color: #666; font-size: 9px;")
        warning_label.setWordWrap(False)
        warning_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        control_layout.addWidget(warning_label)
        
        layout.addLayout(control_layout)
        
        # Tabs: Devices first, then measurements / messages / diagnostics
        tabs = QTabWidget()
        
        tab_devices = self._create_devices_tab()
        tabs.addTab(tab_devices, "Devices")
        
        tab_measures = self._create_measures_tab()
        tabs.addTab(tab_measures, "Live Measures")
        
        tab_messages = self._create_messages_tab()
        tabs.addTab(tab_messages, "Decoded Messages")
        
        tab_diagnostics = self._create_diagnostics_tab()
        tabs.addTab(tab_diagnostics, "Diagnostics")
        
        layout.addWidget(tabs)
        
        # Footer with controls
        footer = self._create_footer()
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QWidget:
        """Create header with information (compact)"""
        group = QGroupBox("FTCAN 2.0 Protocol")
        main_layout = QHBoxLayout()  # Changed to horizontal for compact layout
        
        # Left side: Protocol info (compact)
        info_text = QLabel(
            "<b>CAN 2.0B Extended (29-bit)</b> • 1 Mbps • Big-endian"
        )
        info_text.setStyleSheet("color: #555; font-size: 10px;")
        main_layout.addWidget(info_text)
        
        main_layout.addStretch()
        
        # Right side: Channel selector with status
        # Debug log
        print(f"[FTCAN Dialog] Number of 1Mbps buses: {len(self.buses_1mbps)}")
        for i, (name, bus) in enumerate(self.buses_1mbps):
            print(f"  [{i}] {name}: connected={bus.connected}, baudrate={bus.config.baudrate}")
        
        if len(self.buses_1mbps) > 1:
            # Multiple buses - show dropdown
            main_layout.addWidget(QLabel("<b>Channel:</b>"))
            self.bus_combo = QComboBox()
            self.bus_combo.setMinimumWidth(150)
            for bus_name, bus in self.buses_1mbps:
                if bus.connected:
                    self.bus_combo.addItem(f"{bus_name} - Connected")
                else:
                    self.bus_combo.addItem(f"{bus_name} - Simulation")
            self.bus_combo.currentIndexChanged.connect(self._on_bus_changed)
            main_layout.addWidget(self.bus_combo)
        elif len(self.buses_1mbps) == 1:
            # Single bus - show as label with colored status
            bus_name, bus = self.buses_1mbps[0]
            if bus.connected:
                status_html = "<span style='color: green; font-weight: bold;'>Connected</span>"
            else:
                status_html = "<span style='color: red; font-weight: bold;'>Disconnected</span>"
            bus_label = QLabel(f"<b>Channel:</b> {bus_name} - {status_html}")
            main_layout.addWidget(bus_label)
        else:
            # No bus available
            status_html = "<span style='color: red; font-weight: bold;'>Disconnected</span>"
            bus_label = QLabel(f"<b>Channel:</b> {status_html}")
            main_layout.addWidget(bus_label)
        
        group.setLayout(main_layout)
        return group
    
    def _on_bus_changed(self, index: int):
        """Callback when selected bus changes"""
        if index >= 0 and index < len(self.buses_1mbps):
            self.selected_bus = self.buses_1mbps[index][0]
    
    def _on_filter_changed(self, index: int):
        """Callback when product type filter changes"""
        self.product_type_filter_value = self.product_type_filter.currentData()
        self._update_messages_table()  # Refresh display with new filter
    
    def _on_auto_scroll_changed(self, state):
        """Callback when auto-scroll checkbox changes"""
        self.auto_scroll_enabled = (state == Qt.CheckState.Checked.value)
    
    def _create_messages_tab(self) -> QWidget:
        """Cria tab de mensagens decodificadas"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("<b>Filter by Device Type:</b>"))
        
        self.product_type_filter = QComboBox()
        self.product_type_filter.addItem("All Devices", None)
        self.product_type_filter.addItem("ECUs (FT500/FT600)", "ECU")
        self.product_type_filter.addItem("O2 Sensors (WB-O2)", "O2")
        self.product_type_filter.addItem("SwitchPanel", "SWITCHPAD")
        self.product_type_filter.addItem("EGT Sensors", "EGT")
        self.product_type_filter.addItem("Other Devices", "OTHER")
        self.product_type_filter.setMinimumWidth(250)
        self.product_type_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.product_type_filter)
        
        filter_layout.addStretch()
        
        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setChecked(True)
        self.auto_scroll_checkbox.stateChanged.connect(self._on_auto_scroll_changed)
        filter_layout.addWidget(self.auto_scroll_checkbox)
        
        layout.addLayout(filter_layout)
        
        # Message table (largest portion of the space)
        self.messages_table = QTableWidget()
        self.messages_table.setColumnCount(9)
        self.messages_table.setHorizontalHeaderLabels([
            "Timestamp", "CAN ID", "Product", "Data Field", 
            "Message ID", "Priority", "Measures", "Status", "Raw Data"
        ])
        
        header = self.messages_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        
        self.messages_table.itemSelectionChanged.connect(self._on_message_selected)
        layout.addWidget(self.messages_table, 3)  # 3 parts of space
        
        # Selected message details (fills available space)
        details_group = QGroupBox("Message Details")
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins
        details_layout.setSpacing(0)  # No spacing
        
        self.message_details = QTextEdit()
        self.message_details.setReadOnly(True)
        # Remove height constraints to fill available space
        font = QFont("Courier New", 9)  # Slightly larger font
        self.message_details.setFont(font)
        details_layout.addWidget(self.message_details)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group, 1)  # 1 part of space
        
        widget.setLayout(layout)
        return widget
    
    def _create_measures_tab(self) -> QWidget:
        """Cria tab de medidas em tempo real"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Device filter (compact)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("<b>Filter:</b>"))
        
        self.device_filter = QComboBox()
        self.device_filter.addItem("All Devices")
        self.device_filter.setMinimumWidth(200)
        self.device_filter.currentTextChanged.connect(self._update_measures_display)
        filter_layout.addWidget(self.device_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Measurements table
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
        """Create diagnostics tab (optimized layout)"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Top row: Statistics and Issues side by side (30% of vertical space)
        top_layout = QHBoxLayout()
        
        # Statistics (left side)
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(5, 5, 5, 5)
        
        self.stats_label = QLabel("No data yet")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("font-size: 10px;")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        stats_layout.addWidget(self.stats_label, 1)  # Stretch to fill
        
        stats_group.setLayout(stats_layout)
        top_layout.addWidget(stats_group, 1)
        
        # Problemas detectados (right side)
        issues_group = QGroupBox("Detected Issues")
        issues_layout = QVBoxLayout()
        issues_layout.setContentsMargins(5, 5, 5, 5)
        
        self.issues_text = QTextEdit()
        self.issues_text.setReadOnly(True)
        self.issues_text.setStyleSheet("font-size: 10px;")
        issues_layout.addWidget(self.issues_text, 1)  # Stretch to fill
        
        issues_group.setLayout(issues_layout)
        top_layout.addWidget(issues_group, 1)
        
        layout.addLayout(top_layout, 3)  # 30% of space
        
        # Broadcast streams (device list in the Devices tab)
        streams_group = QGroupBox("Broadcast Streams (ECU)")
        streams_layout = QVBoxLayout()
        streams_layout.setContentsMargins(5, 5, 5, 5)
        
        self.streams_table = QTableWidget()
        self.streams_table.setColumnCount(4)
        self.streams_table.setHorizontalHeaderLabels([
            "Priority", "Messages", "Measures", "Update Rate"
        ])
        self.streams_table.setRowCount(4)  # 4 priority levels
        
        priorities = ["Critical (0x0FF)", "High (0x1FF)", "Medium (0x2FF)", "Low (0x3FF)"]
        for i, priority in enumerate(priorities):
            item = QTableWidgetItem(priority)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.streams_table.setItem(i, 0, item)
            
            for j in range(1, 4):
                item = QTableWidgetItem("0")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.streams_table.setItem(i, j, item)
        
        header = self.streams_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.streams_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        streams_layout.addWidget(self.streams_table, 1)
        streams_group.setLayout(streams_layout)
        layout.addWidget(streams_group, 7)
        
        widget.setLayout(layout)
        return widget
    
    def _create_devices_tab(self) -> QWidget:
        """Lista dispositivos FTCAN agregados (Product ID, IDs decodificados, CAN de exemplo)."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        hint = QLabel(
            "Dispositivos inferidos das mensagens decodificadas (mesmo Product ID = mesma unidade no bus). "
            "Unique ID e tipo vêm do ID CAN 29-bit; Example CAN ID é o último quadro visto."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(hint)
        
        self.devices_detail_table = QTableWidget()
        self.devices_detail_table.setColumnCount(9)
        self.devices_detail_table.setHorizontalHeaderLabels([
            "Product ID",
            "Type ID",
            "Name",
            "Unique ID",
            "Example CAN ID",
            "Data fields",
            "Message IDs",
            "Msgs",
            "Last seen (s)",
        ])
        hdr = self.devices_detail_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.devices_detail_table.verticalHeader().setVisible(False)
        layout.addWidget(self.devices_detail_table)
        widget.setLayout(layout)
        return widget
    
    def _aggregate_ftcan_devices(self) -> List[Dict]:
        """Agrega dispositivos por product_id (string) a partir do cache decodificado."""
        devices: Dict[str, Dict] = {}
        for idx, msg in enumerate(self.messages):
            if idx not in self.decoded_cache:
                continue
            decoded = self.decoded_cache[idx]
            ident = decoded.get("identification")
            if not ident:
                continue
            pid = ident["product_id"]
            if pid not in devices:
                devices[pid] = {
                    "product_id": pid,
                    "product_type_id": ident["product_type_id"],
                    "product_name": ident["product_name"],
                    "unique_id": ident["unique_id"],
                    "example_can_id": msg.can_id,
                    "data_fields": set(),
                    "message_ids": set(),
                    "count": 0,
                    "last_seen": msg.timestamp,
                }
            d = devices[pid]
            d["count"] += 1
            d["last_seen"] = msg.timestamp
            d["example_can_id"] = msg.can_id
            d["data_fields"].add(ident.get("data_field_name", "-"))
            d["message_ids"].add(ident.get("message_id", "-"))
        def _mid_key(m: str) -> int:
            try:
                return int(m.replace("0x", ""), 16)
            except ValueError:
                return 0

        rows = []
        for d in sorted(devices.values(), key=lambda x: x["product_id"]):
            rows.append(
                {
                    "product_id": d["product_id"],
                    "product_type_id": d["product_type_id"],
                    "product_name": d["product_name"],
                    "unique_id": d["unique_id"],
                    "example_can_id": d["example_can_id"],
                    "data_fields": ", ".join(sorted(d["data_fields"])),
                    "message_ids": ", ".join(sorted(d["message_ids"], key=_mid_key)),
                    "count": d["count"],
                    "last_seen": d["last_seen"],
                }
            )
        return rows
    
    def _update_devices_tab(self):
        """Atualiza tabela Devices."""
        if not hasattr(self, "devices_detail_table"):
            return
        rows = self._aggregate_ftcan_devices()
        self.devices_detail_table.setUpdatesEnabled(False)
        self.devices_detail_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.devices_detail_table.setItem(i, 0, QTableWidgetItem(r["product_id"]))
            self.devices_detail_table.setItem(i, 1, QTableWidgetItem(str(r["product_type_id"])))
            self.devices_detail_table.setItem(i, 2, QTableWidgetItem(r["product_name"]))
            self.devices_detail_table.setItem(i, 3, QTableWidgetItem(str(r["unique_id"])))
            ex = QTableWidgetItem(f"0x{r['example_can_id']:08X}")
            ex.setToolTip("Último arbitration ID visto para este Product ID")
            self.devices_detail_table.setItem(i, 4, ex)
            self.devices_detail_table.setItem(i, 5, QTableWidgetItem(r["data_fields"]))
            self.devices_detail_table.setItem(i, 6, QTableWidgetItem(r["message_ids"]))
            self.devices_detail_table.setItem(i, 7, QTableWidgetItem(str(r["count"])))
            self.devices_detail_table.setItem(i, 8, QTableWidgetItem(f"{r['last_seen']:.3f}"))
        self.devices_detail_table.setUpdatesEnabled(True)
    
    def _create_footer(self) -> QWidget:
        """Create footer with controls"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        # Status label (left side - shows decode queue, cache, workers)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Buttons
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_data)
        layout.addWidget(clear_btn)
        
        load_btn = QPushButton("📂 Load")
        load_btn.clicked.connect(self._load_data)
        layout.addWidget(load_btn)
        
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self._export_data)
        layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        widget.setLayout(layout)
        return widget
    
    def add_message(self, msg: CANMessage):
        """Add message for analysis with intelligent priority"""
        # Check if this is an FTCAN message
        if not FTCANDecoder.is_ftcan_message(msg.can_id):
            return
        
        # Filter by selected bus (if multiple exist)
        if self.selected_bus and hasattr(msg, 'source') and msg.source != self.selected_bus:
            return
        
        msg_index = len(self.messages)
        self.messages.append(msg)
        
        # Queue message for background decoding with priority detection
        if self.auto_decode:
            # Detect if message is likely to contain measures (broadcast streams)
            message_id = msg.can_id & 0x7FF
            is_priority = message_id in [0x0FF, 0x1FF, 0x2FF, 0x3FF]  # Broadcast priorities
            
            # Round-robin distribution across workers
            worker = self.decoder_workers[self.current_worker]
            worker.add_decode_task(msg_index, msg, priority=is_priority)
            self.current_worker = (self.current_worker + 1) % self.num_workers
        
        # Limit buffer to 2000 messages (doubled for better history)
        if len(self.messages) > 2000:
            # Remove old messages and their cache
            removed_count = len(self.messages) - 2000
            self.messages = self.messages[-2000:]
            
            # Clear decode queues of old indices in all workers
            for worker in self.decoder_workers:
                with worker.lock:
                    # Filter priority queue
                    worker.priority_queue = [
                        (idx - removed_count, msg) 
                        for idx, msg in worker.priority_queue 
                        if idx >= removed_count
                    ]
                    # Filter normal queue
                    worker.normal_queue = [
                        (idx - removed_count, msg) 
                        for idx, msg in worker.normal_queue 
                        if idx >= removed_count
                    ]
            
            # Update cache indices
            new_cache = {}
            for idx, decoded in self.decoded_cache.items():
                if idx >= removed_count:
                    new_cache[idx - removed_count] = decoded
            self.decoded_cache = new_cache
            
            # Update tracking indices
            if self.last_processed_index >= 0:
                self.last_processed_index = max(0, self.last_processed_index - removed_count)
            if self.last_display_update >= 0:
                self.last_display_update = max(0, self.last_display_update - removed_count)
    
    def _on_decoded_ready(self, msg_index: int, decoded: Dict):
        """Callback when message is decoded in background"""
        # Only cache if index is still valid (not removed by buffer limit)
        if msg_index < len(self.messages):
            self.decoded_cache[msg_index] = decoded
    
    def _update_display(self):
        """Atualiza display com novas mensagens (otimizado)"""
        if not self.auto_decode:
            return
        
        # Update status label (lightweight) - sum all worker queues
        queue_size = sum(len(w.priority_queue) + len(w.normal_queue) for w in self.decoder_workers)
        cached_count = len(self.decoded_cache)
        total_msgs = len(self.messages)
        
        if queue_size > 0:
            self.status_label.setText(f"Decoding: {queue_size} in queue | {cached_count}/{total_msgs} cached | {self.num_workers} workers")
        else:
            self.status_label.setText(f"Ready | {cached_count}/{total_msgs} cached | {self.num_workers} workers")
        
        # Only update if there are new messages OR new decoded data
        current_msg_count = len(self.messages)
        has_new_messages = current_msg_count != self.last_display_update
        
        if not has_new_messages and queue_size == 0:
            return  # No changes, skip update
        
        if has_new_messages:
            self.last_display_update = current_msg_count
        
        self.update_counter += 1
        
        # Update measures FIRST (most important for real-time feel)
        self._update_measures_display()
        
        # Update messages table less frequently (every 2 cycles = 200ms)
        if self.update_counter % 2 == 0:
            self._update_messages_table()
        
        # Update diagnostics + Devices tab every 10 cycles (~1 s)
        if self.update_counter % 10 == 0:
            self._update_diagnostics()
            self._update_devices_tab()
    
    def _update_messages_table(self):
        """Atualiza tabela de mensagens (usando cache, otimizado)"""
        # Get last 100 messages
        total_messages = len(self.messages)
        start_index = max(0, total_messages - 100)
        recent_messages = self.messages[start_index:]
        
        # Apply product type filter
        filtered_message_indices = []  # Store (row, msg_index) mapping
        
        if self.product_type_filter_value:
            filtered_data = []
            
            for i, msg in enumerate(recent_messages):
                msg_index = start_index + i
                
                # Check cache for product type
                if msg_index in self.decoded_cache:
                    decoded = self.decoded_cache[msg_index]
                    if decoded['identification']:
                        product_name = decoded['identification']['product_name']
                        
                        # Apply filter
                        matches = False
                        if self.product_type_filter_value == "ECU" and "ECU" in product_name:
                            matches = True
                        elif self.product_type_filter_value == "O2" and ("WBO2" in product_name or "O2" in product_name):
                            matches = True
                        elif self.product_type_filter_value == "SWITCHPAD" and ("SwitchPanel" in product_name or "SWITCHPAD" in product_name):
                            matches = True
                        elif self.product_type_filter_value == "EGT" and "EGT" in product_name:
                            matches = True
                        elif self.product_type_filter_value == "OTHER":
                            if not any(x in product_name for x in ["ECU", "WBO2", "O2", "SwitchPanel", "SWITCHPAD", "EGT"]):
                                matches = True
                        
                        if matches:
                            filtered_data.append((msg_index, msg))
            
            # Use filtered messages
            if filtered_data:
                for row, (msg_index, msg) in enumerate(filtered_data):
                    filtered_message_indices.append((row, msg_index))
                recent_messages = [msg for _, msg in filtered_data]
            else:
                recent_messages = []
        else:
            # No filter - use all messages with sequential indices
            for row, msg in enumerate(recent_messages):
                filtered_message_indices.append((row, start_index + row))
        
        current_rows = self.messages_table.rowCount()
        target_rows = len(recent_messages)
        
        # Disable updates during batch operation
        self.messages_table.setUpdatesEnabled(False)
        
        # Only resize if needed
        if current_rows != target_rows:
            self.messages_table.setRowCount(target_rows)
        
        # Update all rows (even if not decoded yet)
        for row, msg in enumerate(recent_messages):
            # Get correct message index from mapping
            msg_index = filtered_message_indices[row][1] if row < len(filtered_message_indices) else start_index + row
            
            # Always show timestamp and CAN ID
            self.messages_table.setItem(row, 0, QTableWidgetItem(f"{msg.timestamp:.3f}"))
            self.messages_table.setItem(row, 1, QTableWidgetItem(f"0x{msg.can_id:08X}"))
            
            # Check if decoded
            if msg_index in self.decoded_cache:
                decoded = self.decoded_cache[msg_index]
                
                # Product
                if decoded['identification']:
                    product = decoded['identification']['product_name']
                    product_item = QTableWidgetItem(product)
                    
                    # Add tooltip with full details
                    tooltip = f"Product Type ID: {decoded['identification']['product_type_id']}\n"
                    tooltip += f"Unique ID: {decoded['identification']['unique_id']}\n"
                    tooltip += f"Product ID: {decoded['identification']['product_id']}"
                    product_item.setToolTip(tooltip)
                    
                    self.messages_table.setItem(row, 2, product_item)
                    
                    # Data Field
                    data_field = decoded['identification']['data_field_name']
                    self.messages_table.setItem(row, 3, QTableWidgetItem(data_field))
                    
                    # Message ID
                    msg_id = decoded['identification']['message_id']
                    msg_id_item = QTableWidgetItem(msg_id)
                    
                    # Add tooltip for special messages
                    if decoded['identification'].get('special_message'):
                        special = decoded['identification']['special_message']
                        msg_id_item.setToolTip(f"{special['device']}: {special['type']}")
                    
                    self.messages_table.setItem(row, 4, msg_id_item)
                    
                    # Priority
                    priority = decoded['identification'].get('broadcast_priority', '-')
                    priority_item = QTableWidgetItem(priority)
                    priority_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Add tooltip
                    if priority != '-':
                        priority_item.setToolTip(f"Broadcast priority: {priority}")
                    
                    self.messages_table.setItem(row, 5, priority_item)
                
                # Measures
                measure_count = len(decoded.get('measures', []))
                measure_item = QTableWidgetItem(str(measure_count))
                measure_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Add tooltip with measure names
                if measure_count > 0:
                    measure_names = [m['name'] for m in decoded.get('measures', [])]
                    measure_item.setToolTip('\n'.join(measure_names[:10]))  # Max 10 in tooltip
                
                self.messages_table.setItem(row, 6, measure_item)
                
                # Status
                status = "Complete" if decoded.get('is_complete') else "Incomplete"
                if decoded.get('error'):
                    status = f"Error: {decoded['error']}"
                
                status_item = QTableWidgetItem(status)
                if decoded.get('error'):
                    status_item.setForeground(QColor(255, 0, 0))
                elif decoded.get('is_complete'):
                    status_item.setForeground(QColor(0, 150, 0))
                
                self.messages_table.setItem(row, 7, status_item)
            else:
                # Not decoded yet - show placeholder
                self.messages_table.setItem(row, 2, QTableWidgetItem("Decoding..."))
                self.messages_table.setItem(row, 3, QTableWidgetItem("-"))
                self.messages_table.setItem(row, 4, QTableWidgetItem("-"))
                self.messages_table.setItem(row, 5, QTableWidgetItem("-"))
                self.messages_table.setItem(row, 6, QTableWidgetItem("-"))
                
                status_item = QTableWidgetItem("Pending")
                status_item.setForeground(QColor(128, 128, 128))
                self.messages_table.setItem(row, 7, status_item)
            
            # Raw Data (always available)
            self.messages_table.setItem(row, 8, QTableWidgetItem(msg.to_hex_string()))
        
        # Re-enable updates
        self.messages_table.setUpdatesEnabled(True)
        
        # Auto-scroll to bottom if enabled and there are new messages
        if self.auto_scroll_enabled and target_rows > 0:
            self.messages_table.scrollToBottom()
    
    def _update_measures_display(self):
        """Atualiza display de medidas (usando cache, tempo real otimizado)"""
        # Collect only the LATEST measurements (most recent)
        measures_dict = {}  # {(device, measure_name): (value, unit, raw, timestamp)}
        
        total_messages = len(self.messages)
        # Process only the last 50 messages for performance
        start_index = max(0, total_messages - 50)
        
        for idx in range(start_index, total_messages):
            # Use cached decode if available
            if idx not in self.decoded_cache:
                continue
            
            decoded = self.decoded_cache[idx]
            
            if not decoded['identification'] or not decoded.get('measures'):
                continue
            
            device = decoded['identification']['product_name']
            msg = self.messages[idx]
            
            for measure in decoded['measures']:
                key = (device, measure['name'])
                # Always use the latest value (overwrites previous)
                measures_dict[key] = (
                    measure['real_value'],
                    measure['unit'],
                    measure['raw_value'],
                    msg.timestamp
                )
        
        # Apply filter before counting rows
        current_filter = self.device_filter.currentText()
        filtered_items = []
        
        for (device, measure_name), (value, unit, raw, timestamp) in sorted(measures_dict.items()):
            if current_filter != "All Devices" and device != current_filter:
                continue
            filtered_items.append(((device, measure_name), (value, unit, raw, timestamp)))
        
        # Disable updates during batch operation
        self.measures_table.setUpdatesEnabled(False)
        
        # Update table with filtered items
        current_rows = self.measures_table.rowCount()
        target_rows = len(filtered_items)
        
        if current_rows != target_rows:
            self.measures_table.setRowCount(target_rows)
        
        for row, ((device, measure_name), (value, unit, raw, timestamp)) in enumerate(filtered_items):
            # Simplified: just set items directly (faster than checking)
            self.measures_table.setItem(row, 0, QTableWidgetItem(device))
            self.measures_table.setItem(row, 1, QTableWidgetItem(measure_name))
            self.measures_table.setItem(row, 2, QTableWidgetItem(f"{value:.3f}"))
            self.measures_table.setItem(row, 3, QTableWidgetItem(unit))
            self.measures_table.setItem(row, 4, QTableWidgetItem(str(raw)))
            self.measures_table.setItem(row, 5, QTableWidgetItem(f"{timestamp:.3f}s"))
        
        # Re-enable updates
        self.measures_table.setUpdatesEnabled(True)
        
        # Update device filter (without recursion)
        self._update_device_filter_safe()
    
    def _update_device_filter_safe(self):
        """Update device list in filter (no recursion, usando cache)"""
        # Temporarily block signals to avoid recursion
        self.device_filter.blockSignals(True)
        
        current = self.device_filter.currentText()
        
        devices = set()
        for idx, msg in enumerate(self.messages):
            # Use cached decode if available
            if idx in self.decoded_cache:
                decoded = self.decoded_cache[idx]
            else:
                # Fallback: decode synchronously
                decoded = self.decoder.decode_message(msg.can_id, msg.data)
                self.decoded_cache[idx] = decoded
            
            if decoded['identification']:
                devices.add(decoded['identification']['product_name'])
        
        self.device_filter.clear()
        self.device_filter.addItem("All Devices")
        for device in sorted(devices):
            self.device_filter.addItem(device)
        
        # Restore selection
        index = self.device_filter.findText(current)
        if index >= 0:
            self.device_filter.setCurrentIndex(index)
        
        # Reativa sinais
        self.device_filter.blockSignals(False)
    
    def _update_diagnostics(self):
        """Update diagnostic information (usando cache, otimizado)"""
        if not self.messages:
            return
        
        # General statistics
        total_messages = len(self.messages)
        ftcan_messages = sum(1 for msg in self.messages if FTCANDecoder.is_ftcan_message(msg.can_id))
        
        # Broadcast streams statistics
        stream_stats = {
            0x0FF: {'count': 0, 'measures': 0, 'last_time': 0, 'first_time': 0},
            0x1FF: {'count': 0, 'measures': 0, 'last_time': 0, 'first_time': 0},
            0x2FF: {'count': 0, 'measures': 0, 'last_time': 0, 'first_time': 0},
            0x3FF: {'count': 0, 'measures': 0, 'last_time': 0, 'first_time': 0},
        }
        
        # Unique devices (processes only cached messages)
        devices = {}
        for idx, msg in enumerate(self.messages):
            # Skip if not decoded yet
            if idx not in self.decoded_cache:
                continue
            
            decoded = self.decoded_cache[idx]
            
            if decoded['identification']:
                product_id = decoded['identification']['product_id']
                product_name = decoded['identification']['product_name']
                message_id_raw = decoded['identification']['message_id']
                
                # Extract numeric message_id
                try:
                    message_id = int(message_id_raw.replace('0x', ''), 16)
                except:
                    message_id = 0
                
                # Update stream statistics
                if message_id in stream_stats:
                    stream_stats[message_id]['count'] += 1
                    stream_stats[message_id]['last_time'] = msg.timestamp
                    if stream_stats[message_id]['first_time'] == 0:
                        stream_stats[message_id]['first_time'] = msg.timestamp
                    
                    # Count measures
                    if 'measures' in decoded and decoded['measures']:
                        stream_stats[message_id]['measures'] += len(decoded['measures'])
                
                if product_id not in devices:
                    devices[product_id] = {
                        'name': product_name,
                        'unique_id': decoded['identification']['unique_id'],
                        'count': 0,
                        'last_seen': 0
                    }
                
                devices[product_id]['count'] += 1
                devices[product_id]['last_seen'] = msg.timestamp
        
        # Update statistics
        stats_text = f"""
<b>Total Messages:</b> {total_messages}<br>
<b>FTCAN Messages:</b> {ftcan_messages}<br>
<b>Unique Devices:</b> {len(devices)}<br>
<b>Time Span:</b> {self.messages[-1].timestamp - self.messages[0].timestamp:.2f}s
        """
        self.stats_label.setText(stats_text)
        
        # Update streams table
        self.streams_table.setUpdatesEnabled(False)
        stream_rows = [0x0FF, 0x1FF, 0x2FF, 0x3FF]
        for i, msg_id in enumerate(stream_rows):
            stats = stream_stats[msg_id]
            
            # Messages count
            item = QTableWidgetItem(str(stats['count']))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.streams_table.setItem(i, 1, item)
            
            # Total measures
            item = QTableWidgetItem(str(stats['measures']))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.streams_table.setItem(i, 2, item)
            
            # Update rate (Hz)
            if stats['count'] > 1 and stats['last_time'] > stats['first_time']:
                time_span = stats['last_time'] - stats['first_time']
                rate = (stats['count'] - 1) / time_span
                item = QTableWidgetItem(f"{rate:.1f} Hz")
            else:
                item = QTableWidgetItem("-")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.streams_table.setItem(i, 3, item)
        
        self.streams_table.setUpdatesEnabled(True)
        
        # Detecta problemas
        self._detect_issues()
    
    def _detect_issues(self):
        """Detect communication issues"""
        issues = []
        
        if not self.messages:
            self.issues_text.setText("No messages to analyze")
            return
        
        # Check if there are FTCAN messages
        ftcan_count = sum(1 for msg in self.messages if FTCANDecoder.is_ftcan_message(msg.can_id))
        
        if ftcan_count == 0:
            issues.append("⚠️ No FTCAN messages detected!")
            issues.append("   - Check if baudrate is set to 1 Mbps (1000000 bit/s)")
            issues.append("   - Verify CAN bus termination (120Ω resistors)")
            issues.append("   - Check if device is powered and connected")
        
        # Check if WB-O2 Nano is present (using cache)
        has_wbo2 = False
        for idx in range(len(self.messages)):
            if idx in self.decoded_cache:
                decoded = self.decoded_cache[idx]
                if decoded['identification']:
                    if 'WBO2_NANO' in decoded['identification']['product_name']:
                        has_wbo2 = True
                        break
        
        if not has_wbo2 and ftcan_count > 0:
            issues.append("ℹ️ No WB-O2 Nano detected")
            issues.append("   - Device may not be associated with ECU")
            issues.append("   - Check CAN wiring (White/Red = CAN+, Yellow/Blue = CAN-)")
        
        # Check for incomplete segmentation (using cache)
        total_messages = len(self.messages)
        start_index = max(0, total_messages - 100)
        incomplete_segments = 0
        
        for idx in range(start_index, total_messages):
            if idx in self.decoded_cache:
                decoded = self.decoded_cache[idx]
                if not decoded.get('is_complete', True):
                    incomplete_segments += 1
        
        if incomplete_segments > 0:
            issues.append(f"⚠️ {incomplete_segments} incomplete segmented packets")
            issues.append("   - Possible message loss or buffer overflow")
        
        if not issues:
            issues.append("✅ No issues detected")
        
        self.issues_text.setText("\n".join(issues))
    
    def _on_message_selected(self):
        """Callback when message is selected (usando cache)"""
        selected_rows = self.messages_table.selectedItems()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Calculate actual message index
        total_messages = len(self.messages)
        start_index = max(0, total_messages - 100)
        msg_index = start_index + row
        
        if msg_index >= len(self.messages):
            return
        
        msg = self.messages[msg_index]
        
        # Use cached decode if available
        if msg_index in self.decoded_cache:
            decoded = self.decoded_cache[msg_index]
        else:
            decoded = self.decoder.decode_message(msg.can_id, msg.data)
            self.decoded_cache[msg_index] = decoded
        
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
        self.decoded_cache.clear()
        self.last_processed_index = -1
        self.last_display_update = 0
        
        # Clear all worker queues
        for worker in self.decoder_workers:
            with worker.lock:
                worker.priority_queue.clear()
                worker.normal_queue.clear()
        
        # Clear decoder buffers
        self.decoder.clear_segmented_buffers()
        self.decoder.clear_stream_buffers()
        
        # Clear UI
        self.messages_table.setRowCount(0)
        self.measures_table.setRowCount(0)
        if hasattr(self, "devices_detail_table"):
            self.devices_detail_table.setRowCount(0)
        self.message_details.clear()
        self.stats_label.setText("No data yet")
        self.issues_text.clear()
        
        # Reset streams table
        for i in range(4):
            self.streams_table.setItem(i, 1, QTableWidgetItem("0"))
            self.streams_table.setItem(i, 2, QTableWidgetItem("0"))
            self.streams_table.setItem(i, 3, QTableWidgetItem("-"))
    
    def _export_data(self):
        """Exporta dados decodificados para JSON"""
        if not self.messages:
            QMessageBox.warning(self, "Export", "No messages to export!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export FTCAN Analysis",
            f"ftcan_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if not filename:
            return
        
        try:
            # Prepare export data
            export_data = {
                'file_type': 'ftcan_analyzer',  # File type identifier
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'selected_bus': self.selected_bus,
                'message_count': len(self.messages),
                'messages': []
            }
            
            # Export messages with decoded data
            for idx, msg in enumerate(self.messages):
                msg_data = msg.to_dict()
                
                # Add decoded data if available in cache
                if idx in self.decoded_cache:
                    msg_data['decoded'] = self.decoded_cache[idx]
                
                export_data['messages'].append(msg_data)
            
            # Save to file
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported {len(self.messages)} messages to:\n{filename}"
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export data:\n{str(e)}"
            )
    
    def _load_data(self):
        """Carrega dados de análise FTCAN de arquivo JSON"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load FTCAN Analysis",
            "",
            "JSON Files (*.json)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Validate file type
            file_type = data.get('file_type', None)
            if file_type != 'ftcan_analyzer':
                # Show error with file type mismatch
                type_names = {
                    'tracer': t('file_type_tracer'),
                    'monitor': t('file_type_monitor'),
                    'transmit': t('file_type_transmit'),
                    'gateway': t('file_type_gateway'),
                    'ftcan_analyzer': t('file_type_ftcan_analyzer')
                }
                
                QMessageBox.critical(
                    self,
                    t('error'),
                    t('msg_wrong_file_type').format(
                        expected=type_names.get('ftcan_analyzer', 'FTCAN Analyzer'),
                        found=type_names.get(file_type, file_type or 'Unknown')
                    )
                )
                return
            
            # Clear current data
            self._clear_data()
            
            # Load messages
            messages_data = data.get('messages', [])
            for msg_data in messages_data:
                msg = CANMessage(
                    timestamp=msg_data['timestamp'],
                    can_id=msg_data['can_id'],
                    dlc=msg_data['dlc'],
                    data=bytes.fromhex(msg_data['data']),
                    comment=msg_data.get('comment', ''),
                    period=msg_data.get('period', 0),
                    count=msg_data.get('count', 0)
                )
                
                # Add message
                msg_index = len(self.messages)
                self.messages.append(msg)
                
                # Load decoded data if available
                if 'decoded' in msg_data:
                    self.decoded_cache[msg_index] = msg_data['decoded']
                else:
                    # Queue for decoding if not cached - use round-robin
                    worker = self.decoder_workers[msg_index % self.num_workers]
                    worker.add_decode_task(msg_index, msg, priority=False)
            
            # Update display
            self._update_display()
            self._update_diagnostics()
            self._update_devices_tab()
            
            QMessageBox.information(
                self,
                "Load Successful",
                f"Loaded {len(self.messages)} messages from:\n{filename}"
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load data:\n{str(e)}"
            )
    
    def closeEvent(self, event):
        """Handle dialog close - stop all worker threads"""
        for worker in self.decoder_workers:
            worker.stop()
        super().closeEvent(event)
