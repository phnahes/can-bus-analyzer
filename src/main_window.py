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

from .models import CANMessage
from .dialogs import (
    SettingsDialog, BitFieldViewerDialog, FilterDialog, TriggerDialog, 
    GatewayDialog, DecoderManagerDialog, FTCANDialog, OBD2Dialog
)
from .decoders.base import get_decoder_manager
from .decoders.adapter_ftcan import FTCANProtocolDecoder
from .decoders.adapter_obd2 import OBD2ProtocolDecoder
from .logger import get_logger
from .i18n import get_i18n, t
from .theme import detect_dark_mode, get_adaptive_colors, should_use_dark_mode
from .utils import get_platform_display_name
from .can_bus_manager import CANBusManager, CANBusConfig
from . import __version__, __build__

from .config import get_shortcut
from .ui import (
    MenuBarBuilder, ReceiveTable, table_helpers, ContextMenuManager, 
    ReceiveTableManager, TransmitTableManager, TransmitPanelBuilder, 
    ReceivePanelBuilder, MessageBoxHelper, ToolbarBuilder, StatusBarBuilder
)
from .handlers import (
    PlaybackHandler, FilterManager, RecordingHandler,
    ConnectionManager, DialogManager, UIStateManager,
    TransmitHandler, FileHandler, MessageHandler,
    GatewayManager, SplitScreenManager, SettingsManager,
    TracerModeManager, DialogCoordinator, StateInitializer,
    LoadLogHandler, SaveTransmitHandler, UIUpdateHandler,
    ConnectHandler, MonitorLogHandler, TransmitLoadHandler
)

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
        
        self.logger = get_logger()
        self.logger.info("Initializing CANAnalyzerWindow")
        
        from .config_manager import get_config_manager
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_all()
        self.logger.info(f"Configuration loaded: language={self.config.get('language', 'en')}")
        
        StateInitializer.init_all_state(self)
        
        self.decoder_manager = get_decoder_manager()
        self._init_protocol_decoders()
        
        self._init_handlers()
        
        from .usb_device_monitor import get_usb_monitor
        self.usb_monitor = get_usb_monitor()
        self.usb_monitor.on_device_connected = self.on_usb_device_connected
        self.usb_monitor.on_device_disconnected = self.on_usb_device_disconnected
        self.usb_monitor.start_monitoring()
        
        self.init_ui()
        self.start_ui_update()
    
    def _init_handlers(self):
        """Initialize all handlers"""
        self.connection_mgr = ConnectionManager(
            message_callback=self._on_can_message_received,
            logger=self.logger,
            config=self.config,
            config_manager=self.config_manager
        )
        
        self.transmit_handler = None  # Will be initialized after can_bus_manager
        
        self.file_handler = FileHandler(self)
        
        self.message_handler = MessageHandler(self)
        
        self.receive_table_mgr = ReceiveTableManager(self, self.message_handler)
        
        self.transmit_table_mgr = TransmitTableManager(self)
        
        self.playback_mgr = PlaybackHandler(
            send_callback=self._send_message_for_playback,
            logger=self.logger
        )
        self.playback_mgr.on_playback_start = self._on_playback_start_ui
        self.playback_mgr.on_playback_progress = self._on_playback_progress_ui
        self.playback_mgr.on_playback_complete = self._on_playback_complete_ui
        self.playback_mgr.on_playback_error = self._on_playback_error_ui
        self.playback_mgr.on_message_highlight = self.highlight_playback_row
        
        self.recording_mgr = RecordingHandler(logger=self.logger)
        self.recording_mgr.on_recording_start = self._on_recording_start_ui
        self.recording_mgr.on_recording_stop = self._on_recording_stop_ui
        
        self.filter_mgr = FilterManager(logger=self.logger)
        self.filter_mgr.on_trigger_fired = self._on_trigger_fired_ui
        
        self.dialog_mgr = DialogManager(logger=self.logger)
        
        self.ui_state = UIStateManager(logger=self.logger)
        
        self.gateway_mgr = GatewayManager(self, self.logger)
        
        self.split_screen_mgr = SplitScreenManager(self, self.logger)
        
        self.settings_mgr = SettingsManager(self, self.logger, self.config_manager)
        
        self.tracer_mode_mgr = TracerModeManager(self)
        
        self.dialog_coord = DialogCoordinator(self, self.logger)
        
        self.load_log_handler = LoadLogHandler(self)
        
        self.save_transmit_handler = SaveTransmitHandler(self)
        
        self.ui_update_handler = UIUpdateHandler(self)
        
        self.connect_handler = ConnectHandler(self)
        
        self.monitor_log_handler = MonitorLogHandler(self)
        
        self.transmit_load_handler = TransmitLoadHandler(self)
    
    @property
    def connected(self) -> bool:
        return self.ui_state.is_connected()
    
    @connected.setter
    def connected(self, value: bool):
        self.ui_state.set_connected(value)
    
    @property
    def paused(self) -> bool:
        return self.ui_state.is_paused()
    
    @paused.setter
    def paused(self, value: bool):
        self.ui_state.set_paused(value)
    
    @property
    def tracer_mode(self) -> bool:
        return self.ui_state.is_tracer_mode()
    
    @tracer_mode.setter
    def tracer_mode(self, value: bool):
        self.ui_state.set_tracer_mode(value)
    
    @property
    def message_counters(self):
        return self.ui_state.message_counters
    
    @property
    def message_last_timestamp(self):
        return self.ui_state.message_last_timestamp
    
    def _send_message_for_playback(self, msg: CANMessage) -> bool:
        """Send message during playback"""
        try:
            if self.can_bus_manager and self.transmit_handler:
                # Create message data dict
                msg_data = {
                    'can_id': msg.can_id,
                    'data': msg.data,
                    'is_extended': msg.is_extended,
                    'is_rtr': msg.is_rtr,
                    'dlc': msg.dlc,
                    'target_bus': msg.source
                }
                return self.transmit_handler.send_single(msg_data, msg.source)
            return False
        except Exception as e:
            self.logger.error(f"Error sending playback message: {e}")
            return False
    
    def _on_playback_start_ui(self):
        """Update UI when playback starts"""
        self.playback_active = True
        self.playback_paused = False
        self.btn_play_all.setText("⏸ Pause")
        self.btn_play_all.setEnabled(True)
        self.btn_play_all.setChecked(True)
        self.btn_play_selected.setEnabled(False)
        self.btn_stop_play.setEnabled(True)
        self.playback_label.setText("Playing...")
    
    def _on_playback_progress_ui(self, current: int, total: int):
        """Update UI with playback progress"""
        self.playback_label.setText(f"Playing {current}/{total}")
    
    def _on_playback_complete_ui(self):
        """Update UI when playback completes"""
        self.playback_active = False
        self.playback_paused = False
        self.btn_play_all.setText("▶ Play All")
        self.btn_play_all.setChecked(False)
        self.btn_play_all.setEnabled(True)
        self.btn_play_selected.setEnabled(True)
        self.btn_stop_play.setEnabled(False)
        self.playback_label.setText("Ready")
    
    def _on_playback_error_ui(self, error: str):
        """Handle playback error"""
        self.playback_label.setText(f"Error: {error}")
        MessageBoxHelper.show_warning(self, "Playback Error", error)
    
    def _on_recording_start_ui(self):
        """Update UI when recording starts"""
        self.btn_record.setChecked(True)
        self.btn_record.setText("⏹ Stop Recording")
    
    def _on_recording_stop_ui(self, count: int):
        """Update UI when recording stops"""
        self.btn_record.setChecked(False)
        self.btn_record.setText("⏺ Record")
        
        # Enable playback buttons if we have messages
        if count > 0:
            self.btn_play_all.setEnabled(True)
            self.btn_play_selected.setEnabled(True)
        
        self.show_notification(f"Recording stopped: {count} messages", 3000)
    
    def _on_trigger_fired_ui(self, trigger: Dict, msg: CANMessage):
        """Handle trigger fired"""
        trigger_name = trigger.get('name', 'Unnamed')
        self.show_notification(f"⚡ Trigger fired: {trigger_name}", 5000)
        self.logger.info(f"Trigger '{trigger_name}' fired for message 0x{msg.can_id:X}")
        
        # Check transmit table for trigger-based messages
        self._check_transmit_triggers(msg)
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"{t('app_title')} - {get_platform_display_name()}")
        self.setGeometry(100, 100, 1200, 800)
        
        self.colors = get_adaptive_colors(self.theme_preference)
        
        self.context_menu_mgr = ContextMenuManager(self)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.create_menu_bar()
        
        toolbar_layout = self._create_toolbar()
        main_layout.addLayout(toolbar_layout)
        
        splitter = self._create_main_content()
        main_layout.addWidget(splitter)
        
        status_bar_layout = self._create_status_bar()
        main_layout.addLayout(status_bar_layout)
        
        self.update_ui_translations()
    
    def _create_toolbar(self) -> QHBoxLayout:
        """Create toolbar with connection and mode controls"""
        return ToolbarBuilder.create_toolbar(self)
    
    def _create_main_content(self) -> QSplitter:
        """Create main content area with receive and transmit panels"""
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        receive_panel = self._create_receive_panel()
        transmit_panel = self._create_transmit_panel()
        
        splitter.addWidget(receive_panel)
        splitter.addWidget(transmit_panel)
        splitter.setSizes([500, 300])
        
        return splitter
    
    def _create_receive_panel(self) -> QGroupBox:
        """Create receive panel with table and tracer controls"""
        callbacks = {
            'show_context_menu': self.show_receive_context_menu,
            'toggle_recording': self.toggle_recording,
            'clear_tracer': self.clear_tracer_messages,
            'play_all': self.play_all_messages,
            'play_selected': self.play_selected_message,
            'stop_playback': self.stop_playback,
            'toggle_playback_pause': self.toggle_playback_pause,
            'save_trace': self.save_log,
            'load_trace': self.load_log
        }
        
        (self.receive_group, self.receive_table, 
         self.receive_container_layout, self.tracer_controls_widget) = ReceivePanelBuilder.create_panel(
            self, self.colors, callbacks
        )
        
        self.receive_container = self.receive_group.findChild(QWidget)
        self.setup_receive_table()
        
        return self.receive_group
    
    def _create_transmit_panel(self) -> QGroupBox:
        """Create transmit panel with message list and controls"""
        callbacks = {
            'load_to_edit': self.load_tx_message_to_edit,
            'show_context_menu': self.show_transmit_context_menu,
            'on_dlc_changed': self.on_dlc_changed,
            'add_message': self.add_tx_message,
            'delete_message': self.delete_tx_message,
            'clear_fields': self.clear_tx_fields,
            'send_single': self.send_single,
            'send_all': self.send_all,
            'save_list': self.save_transmit_list,
            'load_list': self.load_transmit_list
        }
        
        self.transmit_group, self.transmit_table = TransmitPanelBuilder.create_panel(
            self, self.colors, callbacks
        )
        return self.transmit_group
    
    def _create_status_bar(self) -> QHBoxLayout:
        """Create status bar with connection and statistics info"""
        return StatusBarBuilder.create_status_bar(self)
    
    def setup_receive_table(self):
        """Configure the receive table based on mode"""
        self.receive_table_mgr.setup_table(self.receive_table, self.tracer_mode)
    
    def toggle_tracer_mode(self):
        """Toggle between Tracer (chronological) and Monitor (grouped) mode"""
        self.tracer_mode_mgr.toggle_mode()
        
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
        self.setWindowTitle(f"{t('app_title')} - {get_platform_display_name()}")
        
        self.btn_connect.setText(f"🔌 {t('btn_connect')}")
        self.btn_disconnect.setText(f"⏹ {t('btn_disconnect')}")
        self.btn_reset.setText(f"🔄 {t('btn_reset')}")
        self.btn_pause.setText(f"⏸ {t('btn_pause')}")
        self.btn_clear_tracer.setText(f"🗑 {t('btn_clear')}")
        self.btn_tracer.setText(f"📊 {t('btn_tracer') if not self.tracer_mode else t('btn_monitor')}")
        
        if hasattr(self, 'mode_label'):
            if self.config.get('listen_only', True):
                self.mode_label.setText(t('status_listen_only'))
            else:
                self.mode_label.setText(t('status_normal'))
        
        if hasattr(self, 'device_label'):
            if self.connected:
                device_info = self.config.get('channel', 'can0')
                self.device_label.setText(f"{t('status_device')}: {device_info}")
            else:
                self.device_label.setText(f"{t('status_device')}: N/A")
        
        if hasattr(self, 'btn_play_all'):
            self.btn_play_all.setText(f"▶ {t('btn_play_all')}")
        if hasattr(self, 'btn_play_selected'):
            self.btn_play_selected.setText(f"▶ {t('btn_play_selected')}")
        if hasattr(self, 'btn_stop_play'):
            self.btn_stop_play.setText(f"⏹ {t('btn_stop')}")
        
        pass
        
        if hasattr(self, 'receive_group'):
            if self.tracer_mode:
                self.receive_group.setTitle(t('label_receive').replace('Monitor', 'Tracer'))
            else:
                self.receive_group.setTitle(t('label_receive'))
        
        if hasattr(self, 'transmit_group'):
            self.transmit_group.setTitle(t('label_transmit'))
        
        self.create_menu_bar()
    
    def apply_theme(self, theme_preference='system'):
        """Apply theme colors to all UI elements"""
        self.theme_preference = theme_preference
        self.is_dark_mode = should_use_dark_mode(theme_preference)
        self.colors = get_adaptive_colors(theme_preference)
        
        self.logger.info(f"Applying theme: {theme_preference}, Dark mode: {self.is_dark_mode}")
        
        from .theme import apply_theme_to_app
        app = QApplication.instance()
        if app:
            apply_theme_to_app(app, theme_preference)
        
        if hasattr(self, 'receive_table'):
            for row in range(self.receive_table.rowCount()):
                for col in range(self.receive_table.columnCount()):
                    item = self.receive_table.item(row, col)
                    if item:
                        item.setBackground(self.colors['normal_bg'])
                        item.setForeground(self.colors['normal_text'])
        
        if hasattr(self, 'transmit_table'):
            for row in range(self.transmit_table.rowCount()):
                for col in range(self.transmit_table.columnCount()):
                    item = self.transmit_table.item(row, col)
                    if item:
                        item.setBackground(self.colors['normal_bg'])
                        item.setForeground(self.colors['normal_text'])
        
        self.update()
        
        self.logger.info("Theme applied successfully")
    
    def create_menu_bar(self):
        """Create menu bar using MenuBarBuilder"""
        menu_builder = MenuBarBuilder(self)
        menu_builder.build(self.menuBar())
    
    def _on_can_message_received(self, bus_name: str, msg: CANMessage):
        """Callback when a CAN message is received from any bus"""
        self.message_queue.put(msg)
        
        if hasattr(self, '_obd2_dialog') and self._obd2_dialog:
            self._obd2_dialog.on_can_message(bus_name, msg)
    
    def _send_can_message(self, can_msg: 'can.Message', target_bus: str = None):
        """Send CAN message to specified bus or all buses
        
        Args:
            can_msg: python-can Message object
            target_bus: Bus name to send to (None = send to all)
        """
        if self.can_bus_manager:
            if target_bus:
                self.can_bus_manager.send_to(target_bus, can_msg)
            else:
                self.can_bus_manager.send_to_all(can_msg)
        elif self.can_bus:
            self.can_bus.send(can_msg)
    
    def toggle_connection(self):
        """Connect or disconnect from CAN bus"""
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        """Connect to CAN bus (with multi-CAN support)"""
        self.connect_handler.connect()
    
    def disconnect(self):
        """Disconnect from CAN bus"""
        if self.periodic_send_active:
            self.stop_all()
        
        if self.recording_mgr.is_recording_active():
            self.recording_mgr.stop_recording()
        
        self.connection_mgr.disconnect()
        self.connected = False
        self.can_bus_manager = None
        
        self.connection_status.setText("Not Connected")
        self.device_label.setText("Device: N/A")
        
        # Update consolidated status bar
        self.update_consolidated_status()
        
        self.show_notification(t('notif_disconnected'), 3000)
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_gateway.setEnabled(False)
        
        if self.config.get('listen_only', True):
            self.mode_label.setText("Listen Only Mode")
        else:
            self.mode_label.setText("Normal Mode")
    
    def reset(self):
        """Reset the application without dropping the connection"""
        self.receive_table.setRowCount(0)
        
        if self.split_screen_mode:
            if self.receive_table_left:
                self.receive_table_left.setRowCount(0)
            if self.receive_table_right:
                self.receive_table_right.setRowCount(0)
        
        self.received_messages.clear()
        self.message_counters.clear()
        self.message_last_timestamp.clear()
        
        self.recording_mgr.clear_recording()
        
        if hasattr(self, 'btn_play_all'):
            self.btn_play_all.setEnabled(False)
            self.btn_play_selected.setEnabled(False)
        
        if self.recording:
            self.btn_record.setChecked(False)
            self.btn_record.setText("⏺ Record")
            self.btn_record.setStyleSheet("")
            self.recording = False
        
        self.update_message_count()
        self.show_notification(t('notif_reset'))
    
    def toggle_recording(self):
        """Start/stop recording messages for playback (Tracer only)"""
        is_recording = self.recording_mgr.toggle_recording()
        self.recording = is_recording
        
        if is_recording:
            self.receive_table.setRowCount(0)
            self.btn_record.setStyleSheet(self.colors['record_active'])
            self.btn_play_all.setEnabled(False)
            self.btn_play_selected.setEnabled(False)
        else:
            self.btn_record.setStyleSheet("")
            if self.recording_mgr.get_message_count() > 0:
                self.btn_play_all.setEnabled(True)
                self.btn_play_selected.setEnabled(True)
    
    def toggle_transmit_panel(self):
        """Show/hide the Transmit panel"""
        self.transmit_panel_visible = not self.transmit_panel_visible
        
        if self.transmit_panel_visible:
            self.transmit_group.setVisible(True)
            self.btn_toggle_transmit.setText("📤 Hide TX")
            self.show_notification(t('notif_tx_panel_visible'), 2000)
        else:
            self.transmit_group.setVisible(False)
            self.btn_toggle_transmit.setText("📤 Show TX")
            self.show_notification(t('notif_tx_panel_hidden'), 2000)
    
    def show_notification(self, message: str, duration: int = 3000):
        """Show temporary notification in the bottom-right corner"""
        self.notification_label.setText(message)
        
        QTimer.singleShot(duration, lambda: self.notification_label.setText(""))
    
    def clear_tracer_messages(self):
        """Clear recorded messages in Tracer"""
        self.recording_mgr.clear_recording()
        self.receive_table.setRowCount(0)
        self.btn_play_all.setEnabled(False)
        self.btn_play_selected.setEnabled(False)
        self.show_notification(t('notif_recorded_cleared'))
    
    def toggle_pause(self):
        """Pause/resume display"""
        self.paused = not self.paused
        if self.paused:
            self.btn_pause.setText("▶ Resume")
            self.btn_pause.setStyleSheet(self.colors['pause_active'])
        else:
            self.btn_pause.setText("⏸ Pause")
            self.btn_pause.setStyleSheet("")
    
    def clear_receive(self):
        """Clear the receive table (and split-screen if active)"""
        self.receive_table.setRowCount(0)
        
        if self.split_screen_mode:
            if self.receive_table_left:
                self.receive_table_left.setRowCount(0)
            if self.receive_table_right:
                self.receive_table_right.setRowCount(0)
        
        self.update_message_count()
    
    def receive_loop(self):
        """CAN message receive loop"""
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
                print(f"Reception error: {e}")
                time.sleep(0.1)
    
    def generate_sample_data(self):
        """Generate sample data"""
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
        """Start timer for UI updates"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)  # Update every 50ms
    
    def update_ui(self):
        """Update interface with new messages"""
        self.ui_update_handler.update_ui()
    
    def add_message_tracer_mode(self, msg: CANMessage, highlight: bool = True):
        """Add message in Tracer mode"""
        if not self.message_passes_filter(msg):
            return
        
        self.receive_table_mgr.add_message_tracer(self.receive_table, msg, highlight)
    
    def add_message_monitor_mode(self, msg: CANMessage, highlight: bool = True, target_table: QTableWidget = None):
        """Add message in Monitor mode (grouped by ID)"""
        if not self.message_passes_filter(msg):
            return
        
        table = target_table if target_table else self.receive_table
        
        self.receive_table_mgr.add_message_monitor(table, msg, self.colors, highlight)
        
        if table == self.receive_table:
            self.update_sequential_ids()
    
    def update_sequential_ids(self):
        """Update sequential IDs in column 0 of Monitor mode"""
        if not self.tracer_mode:  # Only in Monitor mode
            for row in range(self.receive_table.rowCount()):
                id_item = QTableWidgetItem(str(row + 1))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.receive_table.setItem(row, 0, id_item)
    
    def update_message_count(self):
        """Update message counter"""
        if self.tracer_mode:
            count = self.receive_table.rowCount()
        else:
            count = sum(self.message_counters.values())
        self.msg_count_label.setText(f"Messages: {count}")
        
        # Update consolidated status bar
        self.update_consolidated_status()
    
    def update_consolidated_status(self):
        """Update consolidated status bar with all information"""
        try:
            status_parts = []
            
            # Build CAN bus status from scratch (don't use current text to avoid duplication)
            if hasattr(self, 'connected') and self.connected and hasattr(self, 'can_bus_manager') and self.can_bus_manager:
                # Get CAN buses info directly from config
                can_buses = self.config.get('can_buses', [])
                if can_buses:
                    bus_parts = []
                    for bus_config in can_buses:
                        bus_name = bus_config['name']
                        baudrate_kb = bus_config['baudrate'] // 1000
                        channel = bus_config.get('channel', 'N/A')
                        listen_only = bus_config.get('listen_only', True)
                        mode = "LO" if listen_only else "N"
                        
                        # Check if bus is connected
                        is_conn = self.can_bus_manager.is_bus_connected(bus_name)
                        conn_icon = "✓" if is_conn else "✗"
                        
                        # Extract short device name
                        if channel and '/' in channel:
                            short_channel = channel.split('/')[-1]
                            if short_channel.startswith('cu.'):
                                short_channel = short_channel[3:]
                        else:
                            short_channel = channel
                        
                        # Limit channel name
                        if len(short_channel) > 20:
                            short_channel = short_channel[:17] + "..."
                        
                        bus_parts.append(f"{bus_name}: {baudrate_kb}k, {short_channel}, {mode} - {conn_icon}")
                    
                    if bus_parts:
                        status_parts.append(" | ".join(bus_parts))
                else:
                    status_parts.append("Connected")
            else:
                status_parts.append("Not Connected")
            
            # Add Filter status
            if hasattr(self, 'message_filters'):
                if self.message_filters.get('enabled', False):
                    channel_filters = self.message_filters.get('channel_filters', {})
                    total_ids = sum(len(cf.get('ids', [])) for cf in channel_filters.values())
                    if total_ids > 0:
                        status_parts.append(f"Filter: ON ({total_ids} IDs)")
                    else:
                        status_parts.append("Filter: ON")
                else:
                    status_parts.append("Filter: OFF")
            else:
                status_parts.append("Filter: OFF")
            
            # Add Trigger status
            if hasattr(self, 'triggers_enabled') and hasattr(self, 'triggers'):
                if self.triggers_enabled and len(self.triggers) > 0:
                    status_parts.append(f"Trigger: ON ({len(self.triggers)})")
                else:
                    status_parts.append("Trigger: OFF")
            else:
                status_parts.append("Trigger: OFF")
            
            # Add Message count
            if hasattr(self, 'receive_table') and hasattr(self, 'tracer_mode'):
                if self.tracer_mode:
                    count = self.receive_table.rowCount()
                else:
                    count = sum(self.message_counters.values())
                status_parts.append(f"Messages: {count}")
            else:
                status_parts.append("Messages: 0")
            
            # Update the connection_status label with all info
            if hasattr(self, 'connection_status'):
                final_status = " | ".join(status_parts)
                
                # Limit status bar length to avoid UI issues (max 500 chars)
                if len(final_status) > 500:
                    self.logger.warning(f"Status bar too long ({len(final_status)} chars), truncating")
                    final_status = final_status[:497] + "..."
                
                self.connection_status.setText(final_status)
        except Exception as e:
            self.logger.error(f"Error updating consolidated status: {e}", exc_info=True)
    
    def on_dlc_changed(self, value):
        """Enable/disable data fields based on DLC"""
        # Don't enable data fields if RTR is checked
        is_rtr = self.tx_rtr_check.isChecked()
        for i in range(8):
            self.tx_data_bytes[i].setEnabled(i < value and not is_rtr)
            if i >= value:
                self.tx_data_bytes[i].setText("00")
    
    def on_rtr_changed(self, state):
        """Handle RTR checkbox state change"""
        is_rtr = self.tx_rtr_check.isChecked()
        
        if is_rtr:
            # RTR frames don't carry data
            self.tx_dlc_input.setValue(0)
            self.tx_dlc_input.setEnabled(False)
            for i in range(8):
                self.tx_data_bytes[i].setEnabled(False)
                self.tx_data_bytes[i].setText("00")
        else:
            # Re-enable DLC and data fields
            self.tx_dlc_input.setEnabled(True)
            dlc = self.tx_dlc_input.value()
            for i in range(8):
                self.tx_data_bytes[i].setEnabled(i < dlc)
    
    def get_data_from_bytes(self):
        """Get data bytes from individual fields"""
        data_bytes = []
        dlc = self.tx_dlc_input.value()
        for i in range(dlc):
            byte_str = self.tx_data_bytes[i].text()
            if not byte_str or len(byte_str) == 0:
                byte_str = "00"
            data_bytes.append(byte_str)
        return bytes.fromhex(''.join(data_bytes))
    
    def set_data_to_bytes(self, data_str):
        """Set data bytes in individual fields"""
        data_clean = data_str.replace(' ', '')
        
        for i in range(8):
            if i * 2 < len(data_clean):
                byte_hex = data_clean[i*2:i*2+2]
                if len(byte_hex) == 1:
                    byte_hex = '0' + byte_hex
                self.tx_data_bytes[i].setText(byte_hex.upper())
            else:
                self.tx_data_bytes[i].setText("00")
    
    def get_tx_message_data_from_table(self, row):
        """Get data of a message from the transmit table"""
        return self.transmit_table_mgr.get_message_data(self.transmit_table, row)
    
    def send_single(self):
        """Send a single message"""
        if not self.transmit_handler:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        try:
            can_id = int(self.tx_id_input.text(), 16)
            is_rtr = self.tx_rtr_check.isChecked()
            
            # RTR frames don't carry data, only request it
            if is_rtr:
                dlc = 0
                data = bytes()
            else:
                dlc = self.tx_dlc_input.value()
                data = self.get_data_from_bytes()[:dlc]
            
            msg_data = {
                'id': can_id,
                'dlc': dlc,
                'data': data,
                'extended': self.tx_29bit_check.isChecked(),
                'is_rtr': is_rtr
            }
            
            target_bus = self.tx_source_combo.currentText() if self.can_bus_manager else None
            
            if self.transmit_handler.send_single(msg_data, target_bus):
                if self.editing_tx_row >= 0 and self.editing_tx_row < self.transmit_table.rowCount():
                    self._increment_tx_count(self.editing_tx_row)
                
                self.show_notification(t('notif_message_sent', id=can_id), 1000)
            else:
                self.show_notification(t('notif_error', error="Failed to send"), 2000)
                
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            self.show_notification(t('notif_error', error=str(e)), 3000)
    
    def clear_tx_fields(self):
        """Clear all transmit edit fields"""
        self.transmit_table_mgr.clear_fields()
    
    def add_tx_message(self):
        """Add or update message in the transmit list"""
        self.transmit_table_mgr.add_message(self.transmit_table)
    
    def load_tx_message_to_edit(self, item=None):
        """Load message from table into edit fields (double-click or copy)"""
        self.transmit_table_mgr.load_message_to_edit(self.transmit_table)
    
    def delete_tx_message(self):
        """Remove message from list"""
        self.transmit_table_mgr.delete_message(self.transmit_table)
    
    def send_all(self):
        """Start periodic send of all messages with TX Mode = 'on'"""
        if not self.transmit_handler:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        if self.transmit_handler.periodic_send_active:
            self.show_notification(t('notif_periodic_already_active'), 2000)
            return
        
        if self.transmit_table.rowCount() == 0:
            self.show_notification(t('notif_no_messages_in_table'), 2000)
            return
        
        messages = []
        for row in range(self.transmit_table.rowCount()):
            try:
                msg_data = self.get_tx_message_data_from_table(row)
                messages.append(msg_data)
            except Exception as e:
                self.logger.error(f"Error getting data from row {row}: {e}")
        
        messages_started = self.transmit_handler.start_all_periodic(messages)
        
        if messages_started > 0:
            self.periodic_send_active = True
            self.show_notification(t('notif_periodic_started', count=messages_started), 3000)
            self.btn_send_all.setText("Stop All")
            self.btn_send_all.setStyleSheet(self.colors['send_active'])
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.stop_all)
        else:
            self.show_notification("⚠️ Nenhuma mensagem com TX Mode = 'on' e período válido", 2000)
    
    def stop_all(self):
        """Stop all periodic transmissions"""
        if not self.transmit_handler or not self.transmit_handler.periodic_send_active:
            self.show_notification(t('notif_no_periodic_active'), 2000)
            return
        
        self.transmit_handler.stop_all_periodic()
        self.periodic_send_active = False
        
        self.btn_send_all.setText("Send All")
        self.btn_send_all.setStyleSheet("")
        self.btn_send_all.clicked.disconnect()
        self.btn_send_all.clicked.connect(self.send_all)
        
        self.show_notification(t('notif_periodic_stopped'), 2000)
        self.logger.info("Periodic Send: All periodic transmissions stopped")
    
    def _increment_tx_count(self, row: int):
        """Increment transmit counter in table (must be called from main thread)"""
        self.transmit_table_mgr.increment_count(self.transmit_table, row)
    
    def _update_tx_count(self, row: int, count: int):
        """Update transmit counter in table (must be called from main thread)"""
        try:
            if row < self.transmit_table.rowCount():
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    count_item.setText(str(count))
                else:
                    new_item = QTableWidgetItem(str(count))
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transmit_table.setItem(row, 15, new_item)
        except Exception as e:
            self.logger.error(f"Error updating counter: {e}")
    
    def show_settings(self):
        """Show settings window"""
        new_config = self.settings_mgr.show_dialog(self.config, self.usb_monitor)
        
        if new_config:
            old_config = self.config.copy()
            self.config.update(new_config)
            
            language_changed, theme_changed, mode_changed = self.settings_mgr.apply_config_changes(
                old_config, new_config
            )
            
            if language_changed:
                self.update_ui_translations()
            
            if theme_changed:
                self.apply_theme(new_config.get('theme', 'system'))
            
            if self.config.get('listen_only', True):
                self.mode_label.setText(t('status_listen_only'))
            else:
                self.mode_label.setText(t('status_normal'))
            
            notification_msg = self.settings_mgr.get_notification_message(language_changed, theme_changed)
            duration = 5000 if (language_changed and theme_changed) else 3000
            self.show_notification(notification_msg, duration)
    
    def change_language(self, language_code: str):
        """Change application language"""
        try:
            old_language = self.config.get('language', 'en')
            
            if old_language == language_code:
                return  # Already in selected language
            
            self.config['language'] = language_code
            self.config_manager.update(self.config)
            
            from .i18n import get_i18n
            i18n = get_i18n()
            i18n.set_language(language_code)
            self.logger.info(f"Language changed to: {language_code}")
            
            self.update_ui_translations()
            
            lang_name = {"en": "English", "pt": "Português", "es": "Español", "de": "Deutsch", "fr": "Français"}.get(language_code, language_code)
            self.show_notification(t('notif_language_changed', language=lang_name), 3000)
            
        except Exception as e:
            self.logger.error(f"Error changing language: {str(e)}", exc_info=True)
            MessageBoxHelper.show_error(self, "Language Error", f"Error changing language: {str(e)}")
    
    def show_filters(self):
        """Show filter configuration"""
        MessageBoxHelper.show_info(self, "Filters", "Filters under development")
    
    def show_statistics(self):
        """Show statistics"""
        total_msgs = sum(self.message_counters.values())
        unique_ids = len(self.message_counters)
        
        stats_text = f"CAN Bus Statistics\n\n"
        stats_text += f"Total Messages: {total_msgs}\n"
        stats_text += f"Unique IDs: {unique_ids}\n"
        stats_text += f"Connected: {'Yes' if self.connected else 'No'}\n"
        stats_text += f"Recording: {'Yes' if self.recording else 'No'}\n"
        stats_text += f"Mode: {'Tracer' if self.tracer_mode else 'Monitor'}\n\n"
        
        if self.message_counters:
            stats_text += "Top 5 most frequent IDs:\n"
            sorted_ids = sorted(self.message_counters.items(), key=lambda x: x[1], reverse=True)[:5]
            for counter_key, count in sorted_ids:
                can_id, source = counter_key
                stats_text += f"  0x{can_id:03X} ({source}): {count} messages\n"
        
        MessageBoxHelper.show_info(self, "Statistics", stats_text)
    
    def show_about(self):
        """Show application information"""
        platform_name = get_platform_display_name()
        about_text = f"""
        <h2>{t('about_heading', platform=platform_name)}</h2>
        <p><b>{t('about_version')}:</b> {__version__}</p>
        <p><b>{t('about_build')}:</b> {__build__}</p>
        
        <h3>{t('about_desc_heading')}:</h3>
        <p>{t('about_desc_text')}</p>
        
        <h3>{t('about_platforms_heading')}:</h3>
        <ul>
            <li>{t('about_platform_macos')}</li>
            <li>{t('about_platform_linux')}</li>
        </ul>
        
        <h3>{t('about_dependencies_heading')}:</h3>
        <p>{t('about_dependencies_text')}</p>
        
        <h3>{t('about_license_heading')}:</h3>
        <p>{t('about_license_text')}</p>
        
        <p>{t('about_copyright')}</p>
        """
        QMessageBox.about(self, t('dialog_about_title'), about_text)
    
    def save_log(self):
        """Save received messages log"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Receive Log",
            "",
            "JSON Files (*.json);;Trace Files (*.trc);;CSV Files (*.csv);;All Files (*)"
        )
        if filename:
            try:
                self.logger.info(f"Saving log: {filename}")
                
                messages_to_save = self.recording_mgr.get_recorded_messages() if self.tracer_mode else self.received_messages
                
                success = False
                if filename.endswith('.csv'):
                    success = self.file_handler.save_log_csv(filename, messages_to_save)
                elif filename.endswith('.trc'):
                    success = self.file_handler.save_log_trace(filename, messages_to_save)
                else:
                    success = self.file_handler.save_log_json(filename, messages_to_save)
                
                if success:
                    import os
                    filename_short = os.path.basename(filename)
                    self.show_notification(
                        t('notif_log_saved', filename=filename_short, count=len(messages_to_save)),
                        5000
                    )
            except Exception as e:
                self.logger.error(f"Error saving log: {str(e)}", exc_info=True)
                MessageBoxHelper.show_error(self, "Save Error", f"Error saving: {str(e)}")
    
    def load_log(self):
        """Load messages log"""
        self.load_log_handler.load_log()
    
    def _validate_file_type(self, data: dict, expected_type: str, filename: str) -> bool:
        """Validate loaded file type
        
        Args:
            data: Data loaded from JSON
            expected_type: Expected type ('tracer', 'monitor', 'transmit', 'gateway')
            filename: Filename (for error message)
        
        Returns:
            True if valid, False otherwise (shows error message)
        """
        if isinstance(data, list):
            return True
        
        file_type = data.get('file_type', data.get('mode', None))
        
        if file_type is None:
            return True
        
        if file_type != expected_type:
            type_names = {
                'tracer': t('file_type_tracer'),
                'monitor': t('file_type_monitor'),
                'transmit': t('file_type_transmit'),
                'gateway': t('file_type_gateway')
            }
            
            import os
            filename_short = os.path.basename(filename)
            
            QMessageBox.warning(
                self,
                t('warning'),
                t('msg_wrong_file_type').format(
                    filename=filename_short,
                    expected=type_names.get(expected_type, expected_type),
                    found=type_names.get(file_type, file_type)
                )
            )
            return False
        
        return True
    
    def save_monitor_log(self):
        """Save Monitor log (received_messages)"""
        self.monitor_log_handler.save_monitor_log()
    
    def load_monitor_log(self):
        """Load log to Monitor (received_messages)"""
        self.monitor_log_handler.load_monitor_log()
    
    def save_transmit_list(self):
        """Save transmit message list"""
        self.save_transmit_handler.save_transmit_list()
    
    def show_receive_context_menu(self, position):
        """Show context menu on main receive table"""
        self.context_menu_mgr.show_receive_menu(self.receive_table, position)
    
    def show_transmit_context_menu(self, position):
        """Show context menu on transmit table"""
        self.context_menu_mgr.show_transmit_menu(position)
    
    def start_selected_periodic(self):
        """Start periodic send of selected messages"""
        if not self.transmit_handler:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        started_count = 0
        for index in selected_rows:
            row = index.row()
            
            if self.transmit_handler.is_periodic_active(row):
                continue
            
            try:
                msg_data = self.get_tx_message_data_from_table(row)
                
                period = msg_data.get('period', 'off')
                if period == "off" or period == "0":
                    continue
                
                try:
                    period_ms = int(period)
                    if period_ms <= 0:
                        continue
                except ValueError:
                    continue
                
                if self.transmit_handler.start_periodic(row, period_ms, msg_data):
                    started_count += 1
                    self.logger.info(f"Periodic Send: Started 0x{msg_data['id']:03X} every {period_ms}ms")
                
            except Exception as e:
                self.logger.error(f"Error starting periodic send for row {row}: {e}")
        
        if started_count > 0:
            self.periodic_send_active = True
            self.show_notification(t('notif_periodic_started', count=started_count), 2000)
            self.btn_send_all.setText("Stop All")
            self.btn_send_all.setStyleSheet(self.colors['send_active'])
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.stop_all)
    
    def stop_selected_periodic(self):
        """Stop periodic send of selected messages"""
        if not self.transmit_handler:
            return
        
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        stopped_count = 0
        for index in selected_rows:
            row = index.row()
            
            if self.transmit_handler.stop_periodic(row):
                stopped_count += 1
                
                count_item = self.transmit_table.item(row, 15)
                if count_item:
                    count_item.setText("0")
        
        if not self.transmit_handler.periodic_send_active:
            self.periodic_send_active = False
            self.btn_send_all.setText("Send All")
            self.btn_send_all.setStyleSheet("")
            self.btn_send_all.clicked.disconnect()
            self.btn_send_all.clicked.connect(self.send_all)
        
        if stopped_count > 0:
            self.show_notification(t('notif_periodic_stopped_count', count=stopped_count), 2000)
    
    def delete_selected_tx_messages(self):
        """Delete selected messages from transmit table"""
        selected_rows = self.transmit_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        rows_to_delete = sorted([index.row() for index in selected_rows], reverse=True)
        
        for row in rows_to_delete:
            if self.transmit_handler and self.transmit_handler.is_periodic_active(row):
                self.transmit_handler.stop_periodic(row)
            
            self.transmit_table.removeRow(row)
        
        self.show_notification(t('notif_messages_deleted', count=len(rows_to_delete)), 2000)
    
    def load_transmit_list(self):
        """Load transmit message list"""
        self.transmit_load_handler.load_transmit_list()
    
    def toggle_playback_pause(self):
        """Pause or resume playback"""
        # Use PlaybackHandler's pause/resume
        if self.playback_mgr.is_paused:
            self.playback_mgr.resume()
            self.playback_paused = False
            self.btn_play_all.setText("⏸ Pause")
            self.playback_label.setText("Playing...")
            self.show_notification(t('notif_playback_resumed'), 2000)
        else:
            self.playback_mgr.pause()
            self.playback_paused = True
            self.btn_play_all.setText("▶ Continue")
            self.playback_label.setText("Paused")
            self.show_notification(t('notif_playback_paused'), 2000)
    
    def highlight_playback_row(self, row: int):
        """Highlight current row during playback"""
        try:
            if self.current_playback_row >= 0 and self.current_playback_row < self.receive_table.rowCount():
                for col in range(self.receive_table.columnCount()):
                    item = self.receive_table.item(self.current_playback_row, col)
                    if item:
                        item.setBackground(self.colors['normal_bg'])
            
            self.current_playback_row = row
            if row >= 0 and row < self.receive_table.rowCount():
                for col in range(self.receive_table.columnCount()):
                    item = self.receive_table.item(row, col)
                    if item:
                        item.setBackground(self.colors['highlight'])
                
                first_item = self.receive_table.item(row, 0)
                if first_item:
                    self.receive_table.scrollToItem(first_item)
        except Exception as e:
            print(f"Erro ao destacar linha {row}: {e}")
    
    def clear_playback_highlight(self):
        """Clear playback highlight"""
        if self.current_playback_row >= 0 and self.current_playback_row < self.receive_table.rowCount():
            for col in range(self.receive_table.columnCount()):
                item = self.receive_table.item(self.current_playback_row, col)
                if item:
                    item.setBackground(self.colors['normal_bg'])
        self.current_playback_row = -1
    
    def play_all_messages(self):
        """Play (send) all recorded messages or pause/resume"""
        # If already playing, toggle pause
        if self.playback_active:
            self.toggle_playback_pause()
            return
        
        messages = self.recording_mgr.get_recorded_messages()
        
        if not messages:
            MessageBoxHelper.show_warning(self, "Playback", "No recorded messages!\n\nClick 'Record' to record messages first.")
            return
        
        if not self.connected or not self.can_bus_manager:
            MessageBoxHelper.show_warning(self, "Playback", "Connect to CAN bus first!")
            return
        
        self.logger.log_playback("started (Play All)", len(messages))
        self.playback_mgr.play_all(messages, respect_timing=True)
        self.playback_label.setText("Playing...")
        self.show_notification(t('notif_playback_playing', count=len(messages)), 3000)
    
    def play_selected_message(self):
        """Play (send) only selected messages"""
        selected_rows = self.receive_table.selectionModel().selectedRows()
        
        if not selected_rows:
            return
        
        if not self.connected or not self.can_bus_manager:
            self.show_notification(t('notif_connect_first'), 3000)
            return
        
        selected_messages = []
        recorded_messages = self.recording_mgr.get_recorded_messages()
        
        if not recorded_messages:
            self.show_notification("No recorded messages. Click 'Record' first.", 2000)
            return
        
        for index in selected_rows:
            row = index.row()
            
            # Use row index directly if within bounds
            if row < len(recorded_messages):
                selected_messages.append(recorded_messages[row])
            else:
                # Fallback: try to get from UserRole
                id_item = self.receive_table.item(row, 0)
                if id_item:
                    msg_index = id_item.data(Qt.ItemDataRole.UserRole)
                    if msg_index is not None and msg_index < len(recorded_messages):
                        selected_messages.append(recorded_messages[msg_index])
        
        if selected_messages:
            self.logger.info(f"Playing {len(selected_messages)} selected message(s)")
            self.playback_mgr.play_selected(selected_messages, respect_timing=False)
        else:
            self.show_notification("No valid messages selected", 2000)
    
    def stop_playback(self):
        """Stop message playback"""
        self.playback_mgr.stop()
        self.clear_playback_highlight()
        
        self.playback_active = False
        self.playback_paused = False
        
        has_recorded = self.recording_mgr.get_message_count() > 0
        self.btn_play_all.setText("▶ Play All")
        self.btn_play_all.setChecked(False)
        self.btn_play_all.setEnabled(has_recorded)
        self.btn_play_selected.setEnabled(has_recorded)
        self.btn_stop_play.setEnabled(False)
        self.playback_label.setText("Ready")
        self.playback_paused = False
        self.show_notification(t('notif_playback_stopped'), 2000)
    
    def show_bit_field_viewer(self, table: QTableWidget = None):
        """Show Bit Field Viewer for selected message"""
        if table is None:
            table = self.receive_table
        
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        if self.tracer_mode:
            pid_str = table.item(row, 3).text() if table.item(row, 3) else "0x000"
            dlc_str = table.item(row, 4).text() if table.item(row, 4) else "0"
            data_str = table.item(row, 5).text() if table.item(row, 5) else ""
            
            can_id = int(pid_str.replace('0x', ''), 16)
            dlc = int(dlc_str)
            data = bytes.fromhex(data_str.replace(' ', ''))
            
            message = CANMessage(
                timestamp=0,
                can_id=can_id,
                dlc=dlc,
                data=data
            )
        else:
            pid_str = table.item(row, 3).text() if table.item(row, 3) else "0x000"
            dlc_str = table.item(row, 4).text() if table.item(row, 4) else "0"
            data_str = table.item(row, 5).text() if table.item(row, 5) else ""
            
            can_id = int(pid_str.replace('0x', ''), 16)
            dlc = int(dlc_str)
            data = bytes.fromhex(data_str.replace(' ', ''))
            
            message = CANMessage(
                timestamp=0,
                can_id=can_id,
                dlc=dlc,
                data=data
            )
        
        if message:
            
            dialog = BitFieldViewerDialog(self, message)
            dialog.show()
        else:
            MessageBoxHelper.show_warning(self, "Bit Field Viewer", "Message not found!")
    
    def show_filter_dialog(self):
        """Show filter configuration dialog"""
        dialog = FilterDialog(self, self.message_filters)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.message_filters = dialog.get_filters()
            
            self.apply_message_filters()
            
            if self.message_filters['enabled']:
                filter_count = len(self.message_filters['id_filters'])
                self.show_notification(
                    t('notif_filters_enabled', count=filter_count),
                    3000
                )
            else:
                self.show_notification(t('notif_filters_disabled'), 2000)
    
    def show_trigger_dialog(self):
        """Show trigger configuration dialog"""
        from PyQt6.QtWidgets import QDialog
        
        self.logger.info("Opening triggers dialog")
        
        # Pass current state to dialog
        current_config = {
            'enabled': self.triggers_enabled,
            'triggers': self.triggers
        }
        dialog = TriggerDialog(self, current_config)
        
        result = dialog.exec()
        
        # Always get the current state from dialog (even if cancelled, user might have clicked Apply)
        trigger_config = dialog.get_triggers()
        self.triggers_enabled = trigger_config['enabled']
        self.triggers = trigger_config['triggers']
        
        self.logger.info(f"Triggers updated: {len(self.triggers)} configured, Enabled={self.triggers_enabled}")
        
        # Update consolidated status bar
        self.update_consolidated_status()
        
        if result == QDialog.DialogCode.Accepted:
            if self.triggers_enabled:
                self.show_notification(
                    f"⚡ Triggers enabled: {len(self.triggers)} configured",
                    3000
                )
            else:
                self.show_notification(t('notif_triggers_disabled'), 2000)
    
    def apply_message_filters(self):
        """Apply filters to displayed messages"""
        self.filter_mgr.set_filters(self.message_filters)
        
        # Update filter status label
        if self.message_filters['enabled']:
            channel_filters = self.message_filters.get('channel_filters', {})
            data_count = len(self.message_filters.get('data_filters', []))
            
            # Count total filtered IDs across all channels
            total_ids = sum(len(cf.get('ids', [])) for cf in channel_filters.values())
            
            self.filter_status_label.setText(f"Filter: ON (Channels:{len(channel_filters)}, IDs:{total_ids}, Data:{data_count})")
        else:
            self.filter_status_label.setText("Filter: OFF")
        
        # Update consolidated status bar
        self.update_consolidated_status()
    
    def check_and_fire_triggers(self, msg: CANMessage):
        """Check if received message activates any trigger (delegated to FilterManager)"""
        self.filter_mgr.check_triggers(msg)
        # Also check transmit table triggers
        self._check_transmit_triggers(msg)
    
    def _check_dialog_triggers(self, msg: CANMessage):
        """Check if received message matches any dialog-configured triggers"""
        if not self.triggers_enabled or not self.triggers:
            return
        
        for trigger in self.triggers:
            try:
                # Skip disabled triggers
                if not trigger.get('enabled', True):
                    continue
                
                # Check RX Channel filter
                rx_channel = trigger.get('rx_channel', 'ANY').upper()
                if rx_channel != 'ANY':
                    # Get message source (bus name like "CAN1", "CAN2")
                    msg_source = getattr(msg, 'source', 'CAN1').upper()
                    if msg_source != rx_channel:
                        continue
                
                # Parse trigger ID
                trigger_id_str = trigger.get('trigger_id', '').replace('0x', '').replace('0X', '')
                if not trigger_id_str:
                    continue
                trigger_id = int(trigger_id_str, 16)
                
                # Check if ID matches
                if msg.can_id != trigger_id:
                    continue
                
                # Check trigger data if specified
                trigger_data_str = trigger.get('trigger_data', '').strip()
                if trigger_data_str and trigger_data_str.lower() != 'any':
                    trigger_data_hex = trigger_data_str.replace(' ', '')
                    if trigger_data_hex:
                        trigger_data = bytes.fromhex(trigger_data_hex)
                        # Check if data matches
                        match = True
                        for i, byte_val in enumerate(trigger_data):
                            if i >= len(msg.data) or msg.data[i] != byte_val:
                                match = False
                                break
                        if not match:
                            continue
                
                # Trigger matched! Parse and send TX message
                tx_id_str = trigger.get('tx_id', '').replace('0x', '').replace('0X', '')
                if not tx_id_str:
                    continue
                tx_id = int(tx_id_str, 16)
                
                # Parse TX data
                tx_data_str = trigger.get('tx_data', '').replace(' ', '')
                tx_data = bytes.fromhex(tx_data_str) if tx_data_str else bytes()
                
                # Get TX Channel
                tx_channel = trigger.get('tx_channel', 'ALL').upper()
                
                # Create message data
                msg_data = {
                    'can_id': tx_id,
                    'data': tx_data,
                    'is_extended': tx_id > 0x7FF,
                    'is_rtr': False,
                    'dlc': len(tx_data),
                    'target_bus': tx_channel
                }
                
                # Send the message
                self.logger.info(f"Dialog trigger fired: RX[{rx_channel}] 0x{trigger_id:03X} -> TX[{tx_channel}] 0x{tx_id:03X}")
                if self.transmit_handler.send_single(msg_data, tx_channel):
                    self.show_notification(
                        f"⚡ Trigger: [{rx_channel}]0x{trigger_id:03X} → [{tx_channel}]0x{tx_id:03X}",
                        2000
                    )
                
            except Exception as e:
                self.logger.error(f"Error processing dialog trigger: {e}")
    
    def _check_transmit_triggers(self, msg: CANMessage):
        """Check if received message triggers any transmit table entries"""
        if not self.transmit_handler:
            return
        
        # Check dialog-based triggers first
        self._check_dialog_triggers(msg)
        
        # Then check transmit table triggers
        for row in range(self.transmit_table.rowCount()):
            try:
                # Get TX Mode
                tx_mode_item = self.transmit_table.item(row, 4)
                if not tx_mode_item or tx_mode_item.text().lower() != "trigger":
                    continue
                
                # Get Trigger ID
                trigger_id_item = self.transmit_table.item(row, 5)
                if not trigger_id_item or not trigger_id_item.text():
                    continue
                
                trigger_id_str = trigger_id_item.text().replace('0x', '').replace('0X', '')
                trigger_id = int(trigger_id_str, 16)
                
                # Check if ID matches
                if msg.can_id != trigger_id:
                    continue
                
                # Get Trigger Data (optional)
                trigger_data_item = self.transmit_table.item(row, 6)
                if trigger_data_item and trigger_data_item.text():
                    trigger_data_str = trigger_data_item.text().replace(' ', '')
                    trigger_data = bytes.fromhex(trigger_data_str)
                    
                    # Check if data matches
                    if len(trigger_data) > 0:
                        match = True
                        for i, byte_val in enumerate(trigger_data):
                            if i >= len(msg.data) or msg.data[i] != byte_val:
                                match = False
                                break
                        if not match:
                            continue
                
                # Trigger matched! Send the message
                self.logger.info(f"Transmit trigger fired: row {row}, trigger ID 0x{trigger_id:03X}")
                msg_data = self.get_tx_message_data_from_table(row)
                target_bus = msg_data.get('target_bus')
                
                if self.transmit_handler.send_single(msg_data, target_bus):
                    # Increment count
                    self._increment_tx_count(row)
                    self.show_notification(f"⚡ Trigger TX: 0x{msg_data['can_id']:03X}", 2000)
                
            except Exception as e:
                self.logger.error(f"Error checking trigger for row {row}: {e}")
    
    def message_passes_filter(self, msg: CANMessage) -> bool:
        """Check if a message passes configured filters"""
        if not self.filter_mgr.message_passes_filter(msg):
            return False
        
        if not self.message_filters['enabled']:
            return True
        
        # Get filter configuration
        data_filters = self.message_filters.get('data_filters', [])
        channel_filters = self.message_filters.get('channel_filters', {})
        
        self.logger.debug(f"message_passes_filter: ID=0x{msg.can_id:03X}, source={msg.source}")
        
        # Check channel-specific filters
        if channel_filters and len(channel_filters) > 0:
            # Check specific channel first
            if msg.source in channel_filters:
                channel_filter = channel_filters[msg.source]
                channel_ids = channel_filter.get('ids', [])
                channel_show_only = channel_filter.get('show_only', True)
                
                if channel_ids:
                    id_match = msg.can_id in channel_ids
                    self.logger.debug(f"message_passes_filter: [{msg.source}] id_match={id_match}, show_only={channel_show_only}")
                    # Whitelist: show only matching
                    if channel_show_only and not id_match:
                        self.logger.debug(f"message_passes_filter: BLOCKED (whitelist, no match)")
                        return False
                    # Blacklist: hide matching
                    elif not channel_show_only and id_match:
                        self.logger.debug(f"message_passes_filter: BLOCKED (blacklist, match)")
                        return False
            # Check 'ALL' channel filter if no specific filter
            elif 'ALL' in channel_filters:
                channel_filter = channel_filters['ALL']
                channel_ids = channel_filter.get('ids', [])
                channel_show_only = channel_filter.get('show_only', True)
                
                if channel_ids:
                    id_match = msg.can_id in channel_ids
                    self.logger.debug(f"message_passes_filter: [ALL] id_match={id_match}, show_only={channel_show_only}")
                    # Whitelist: show only matching
                    if channel_show_only and not id_match:
                        self.logger.debug(f"message_passes_filter: BLOCKED (whitelist, no match)")
                        return False
                    # Blacklist: hide matching
                    elif not channel_show_only and id_match:
                        self.logger.debug(f"message_passes_filter: BLOCKED (blacklist, match)")
                        return False
        
        # Check data filters (all must match)
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
        """Callback when a USB device is connected (thread-safe)"""
        self.logger.info(f"USB device connected: {device}")
        
        QTimer.singleShot(0, lambda: self.show_notification(
            f"🔌 {t('msg_device_connected').format(device=device.name)}",
            5000
        ))
    
    def on_usb_device_disconnected(self, device):
        """Callback when a USB device is disconnected (thread-safe)"""
        self.logger.info(f"USB device disconnected: {device}")
        
        current_device = self.config.get('channel', '')
        if device.path == current_device:
            self.logger.warning(f"Device in use was disconnected: {device.path}")
            
            if self.connected:
                self.logger.info("Automatically disconnecting due to device removal")
                
                QTimer.singleShot(0, self._handle_device_disconnection)
        
        QTimer.singleShot(0, lambda: self.show_notification(
            f"🔌 {t('msg_device_disconnected').format(device=device.name)}",
            5000
        ))
    
    def _handle_device_disconnection(self):
        """Handle device disconnection in main thread"""
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
    
    def _init_protocol_decoders(self):
        """Initialize protocol decoders"""
        try:
            ftcan_decoder = FTCANProtocolDecoder()
            obd2_decoder = OBD2ProtocolDecoder()
            
            self.decoder_manager.register_decoder(ftcan_decoder)
            self.decoder_manager.register_decoder(obd2_decoder)
            
            decoder_config = self.config.get('protocol_decoders', {})
            if decoder_config:
                self.decoder_manager.load_config(decoder_config)
            else:
                self.decoder_manager.set_decoder_enabled('FTCAN 2.0', False)
                self.decoder_manager.set_decoder_enabled('OBD-II', False)
                self.logger.info("Protocol decoders initialized as DISABLED by default")
            
            self.logger.info(f"Protocol decoders initialized: {len(self.decoder_manager.get_all_decoders())} decoders")
        except Exception as e:
            self.logger.error(f"Error initializing protocol decoders: {e}")
    
    def show_decoder_manager(self):
        """Show Decoder Manager dialog"""
        dialog = DecoderManagerDialog(self)
        dialog.exec()
        
        decoder_config = self.decoder_manager.save_config()
        self.config['protocol_decoders'] = decoder_config
        self.config_manager.save(self.config)
    
    def show_ftcan_dialog(self):
        """Show FTCAN Protocol Analyzer dialog"""
        self.dialog_coord.show_ftcan_dialog()
    
    def _on_ftcan_dialog_closed(self):
        """Callback when FTCAN Analyzer is closed"""
        self._ftcan_dialog = None
    
    def show_obd2_dialog(self):
        """Show OBD-II Monitor dialog"""
        simulation_mode = self.config.get('simulation_mode', False)
        
        has_any_bus = False
        has_connected_bus = False
        
        if self.can_bus_manager:
            for name, bus in self.can_bus_manager.buses.items():
                has_any_bus = True
                if bus.connected:
                    has_connected_bus = True
                    break
        
        if (simulation_mode or not CAN_AVAILABLE) and has_any_bus:
            self.logger.info("Simulation/No-CAN mode: allowing OBD-II Monitor")
            if not has_connected_bus:
                self.logger.info("Auto-connecting buses in simulation mode for OBD-II")
                self.can_bus_manager.connect_all(simulation=True)
                self.connected = True
        elif self.connected and not has_connected_bus and has_any_bus:
            self.logger.warning("Connected flag is True but no buses are actually connected - switching to simulation")
            self.can_bus_manager.connect_all(simulation=True)
        elif not has_connected_bus:
            QMessageBox.warning(
                self,
                t('decoder_not_connected_title'),
                t('decoder_not_connected_msg')
            )
            return
        
        if hasattr(self, '_obd2_dialog') and self._obd2_dialog:
            self._obd2_dialog.raise_()
            self._obd2_dialog.activateWindow()
            return
        
        dialog = OBD2Dialog(self, can_bus_manager=self.can_bus_manager)
        
        self._obd2_dialog = dialog
        
        dialog.finished.connect(self._on_obd2_dialog_closed)
        
        dialog.show()
    
    def _on_obd2_dialog_closed(self):
        """Callback when OBD-II Monitor is closed"""
        self._obd2_dialog = None
    
    def show_gateway_dialog(self):
        """Show the Gateway configuration dialog"""
        result = self.gateway_mgr.show_dialog(self.can_bus_manager, self.gateway_config)
        
        if result:
            self.gateway_config = result
            
            if self.can_bus_manager:
                self.can_bus_manager.set_gateway_config(self.gateway_config)
                
                self.update_gateway_button_state()
                
                status_msg = self.gateway_mgr.get_status_message(self.gateway_config)
                self.statusBar().showMessage(status_msg, 5000)
                
                if self.gateway_config.enabled:
                    self.show_notification("Gateway enabled", 3000)
                else:
                    self.show_notification("Gateway disabled", 3000)
    
    def toggle_gateway_from_toolbar(self):
        """Toggle Gateway enable/disable from toolbar button"""
        success, updated_config = self.gateway_mgr.toggle_from_toolbar(
            self.gateway_config, 
            self.can_bus_manager, 
            self.btn_gateway.isChecked()
        )
        
        if not success:
            self.btn_gateway.setChecked(False)
            return
        
        self.gateway_config = updated_config
        
        self.update_gateway_button_state()
        
        status_msg = self.gateway_mgr.get_toolbar_status(self.gateway_config)
        self.statusBar().showMessage(status_msg, 5000 if self.gateway_config.enabled else 3000)
        
        if self.gateway_config.enabled:
            self.show_notification("🌉 Gateway enabled", 2000)
        else:
            self.show_notification("Gateway disabled", 2000)
    
    def update_gateway_button_state(self):
        """Update gateway button text and style based on state"""
        if self.gateway_config.enabled:
            self.btn_gateway.setText("🌉 Gateway: ON")
            self.btn_gateway.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_gateway.setChecked(True)
        else:
            self.btn_gateway.setText("🌉 Gateway: OFF")
            self.btn_gateway.setStyleSheet("")
            self.btn_gateway.setChecked(False)
    
    def toggle_split_screen(self):
        """Toggle split-screen mode"""
        result = self.split_screen_mgr.toggle(self.can_bus_manager)
        self.split_screen_mode = self.split_screen_mgr.is_active
        
        if result:
            self.split_screen_left_channel = self.split_screen_mgr.left_channel
            self.split_screen_right_channel = self.split_screen_mgr.right_channel
            self._setup_split_screen_view()
            self.show_notification(f"Split-screen enabled: {self.split_screen_left_channel} | {self.split_screen_right_channel}", 3000)
        elif self.split_screen_mode == False:
            self._setup_single_screen_view()
            self.show_notification("Split-screen disabled", 3000)
    
    def _setup_split_screen_view(self):
        """Setup split-screen view with two tables"""
        self.receive_table_left, self.receive_table_right = self.split_screen_mgr.setup_view(
            self.receive_container_layout,
            self.setup_receive_table_for_widget
        )
        
        self.receive_group.setTitle(f"Receive (Monitor) - Split: {self.split_screen_left_channel} | {self.split_screen_right_channel}")
        
        self._reload_messages_split_screen()
    
    def _setup_single_screen_view(self):
        """Restore single screen view"""
        self.split_screen_mgr.teardown_view(self.receive_container_layout, self.receive_table)
        
        self.receive_table_left = None
        self.receive_table_right = None
        
        mode_text = "Tracer" if self.tracer_mode else "Monitor"
        self.receive_group.setTitle(f"Receive ({mode_text})")
        
        self._reload_all_messages()
        
        self.logger.info("Single screen view restored")
    
    def setup_receive_table_for_widget(self, table_widget):
        """Setup a receive table widget with proper configuration"""
        if self.tracer_mode:
            table_widget.setColumnCount(8)
            table_widget.setHorizontalHeaderLabels(['ID', 'Time', t('col_channel'), 'PID', 'DLC', 'Data', 'ASCII', 'Comment'])
            table_widget.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        else:
            table_widget.setColumnCount(9)
            table_widget.setHorizontalHeaderLabels(['ID', 'Count', t('col_channel'), 'PID', 'DLC', 'Data', 'Period', 'ASCII', 'Comment'])
            table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        table_widget.verticalHeader().setVisible(False)
        font = QFont("Courier New", 14)
        table_widget.setFont(font)
        table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_widget.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table_widget.customContextMenuRequested.connect(self.show_receive_context_menu)
        
        header = table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        if self.tracer_mode:
            header.resizeSection(0, 60)   # ID
            header.resizeSection(1, 100)  # Time
            header.resizeSection(2, 70)   # Channel
            header.resizeSection(3, 110)  # PID - 12 characters
            header.resizeSection(4, 60)   # DLC
            header.resizeSection(5, 250)  # Data
            header.resizeSection(6, 100)  # ASCII
            header.resizeSection(7, 150)  # Comment
        else:
            header.resizeSection(0, 40)   # ID
            header.resizeSection(1, 60)   # Count
            header.resizeSection(2, 70)   # Channel
            header.resizeSection(3, 110)  # PID - 12 characters
            header.resizeSection(4, 50)   # DLC
            header.resizeSection(5, 250)  # Data
            header.resizeSection(6, 70)   # Period
            header.resizeSection(7, 100)  # ASCII
            header.resizeSection(8, 150)  # Comment
        
        header.setStretchLastSection(True)
    
    def _reload_messages_split_screen(self):
        """Reload all messages in split-screen mode"""
        if not self.split_screen_mode or not self.receive_table_left or not self.receive_table_right:
            return
        
        self.receive_table_left.setRowCount(0)
        self.receive_table_right.setRowCount(0)
        
        for msg in self.received_messages:
            if self.tracer_mode:
                if msg.source == self.split_screen_left_channel:
                    self._add_message_to_table(msg, self.receive_table_left, highlight=False)
                elif msg.source == self.split_screen_right_channel:
                    self._add_message_to_table(msg, self.receive_table_right, highlight=False)
            else:
                pass  # Will be handled by normal monitor logic
    
    def _reload_all_messages(self):
        """Reload all messages in single screen mode"""
        self.receive_table.setRowCount(0)
        self.message_counters.clear()
        self.message_last_timestamp.clear()
        
        for msg in self.received_messages:
            if self.tracer_mode:
                self.add_message_tracer_mode(msg, highlight=False)
            else:
                self.add_message_monitor_mode(msg, highlight=False)
    
    def _add_message_to_table(self, msg: CANMessage, table: QTableWidget, highlight: bool = True):
        """Add message to a specific table (for split-screen)"""
        if self.tracer_mode:
            dt = datetime.fromtimestamp(msg.timestamp)
            time_str = dt.strftime("%S.%f")[:-3]
            pid_str = f"0x{msg.can_id:03X}"
            data_str = " ".join([f"{b:02X}" for b in msg.data])
            ascii_str = msg.to_ascii()
            
            row = table.rowCount()
            table.insertRow(row)
            
            id_item = QTableWidgetItem(str(row + 1))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            dlc_item = QTableWidgetItem(str(msg.dlc))
            dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            table.setItem(row, 0, id_item)
            table.setItem(row, 1, QTableWidgetItem(time_str))
            
            channel_item = QTableWidgetItem(msg.source)
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, channel_item)
            
            table.setItem(row, 3, QTableWidgetItem(pid_str))
            table.setItem(row, 4, dlc_item)
            table.setItem(row, 5, QTableWidgetItem(data_str))
            table.setItem(row, 6, QTableWidgetItem(ascii_str))
            table.setItem(row, 7, QTableWidgetItem(msg.comment))
            
            table.scrollToBottom()
        else:
            pass
    
    def closeEvent(self, event):
        """Event called when closing the window"""
        # Stop UI update timer
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
            self.timer = None
        
        # Stop USB monitoring
        if hasattr(self, 'usb_monitor'):
            self.usb_monitor.stop_monitoring()
        
        # Disconnect from CAN bus
        if self.connected:
            self.disconnect()
        
        event.accept()

