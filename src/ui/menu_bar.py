"""
Menu Bar Builder

Creates and manages the application menu bar.
Separated from main window for better organization.
"""

from PyQt6.QtWidgets import QMenuBar
from PyQt6.QtGui import QAction
from ..config import get_shortcut
from ..i18n import t


class MenuBarBuilder:
    """Builds the application menu bar"""
    
    def __init__(self, parent_window):
        """
        Initialize menu bar builder.
        
        Args:
            parent_window: Main window instance
        """
        self.parent = parent_window
    
    def build(self, menubar: QMenuBar) -> None:
        """
        Build the complete menu bar.
        
        Args:
            menubar: QMenuBar instance to populate
        """
        menubar.clear()
        
        self._create_file_menu(menubar)
        self._create_view_menu(menubar)
        self._create_tools_menu(menubar)
        self._create_settings_menu(menubar)
        self._create_about_menu(menubar)
    
    def _create_file_menu(self, menubar: QMenuBar) -> None:
        """Create File menu"""
        file_menu = menubar.addMenu(t('menu_file'))
        
        # Connection
        connect_action = QAction(t('menu_connect'), self.parent)
        connect_action.setShortcut(get_shortcut('connect'))
        connect_action.triggered.connect(self.parent.toggle_connection)
        file_menu.addAction(connect_action)
        
        disconnect_action = QAction(t('menu_disconnect'), self.parent)
        disconnect_action.setShortcut(get_shortcut('disconnect'))
        disconnect_action.triggered.connect(self.parent.disconnect)
        file_menu.addAction(disconnect_action)
        
        reset_action = QAction(t('menu_reset'), self.parent)
        reset_action.setShortcut(get_shortcut('reset'))
        reset_action.triggered.connect(self.parent.reset)
        file_menu.addAction(reset_action)
        
        file_menu.addSeparator()
        
        # Monitor section
        file_menu.addAction("--- Monitor ---").setEnabled(False)
        
        save_monitor_action = QAction("💾 Save Monitor Log...", self.parent)
        save_monitor_action.setShortcut(get_shortcut('save_monitor'))
        save_monitor_action.triggered.connect(self.parent.save_monitor_log)
        file_menu.addAction(save_monitor_action)
        
        load_monitor_action = QAction("📂 Load Monitor Log...", self.parent)
        load_monitor_action.setShortcut(get_shortcut('load_monitor'))
        load_monitor_action.triggered.connect(self.parent.load_monitor_log)
        file_menu.addAction(load_monitor_action)
        
        file_menu.addSeparator()
        
        # Tracer section
        file_menu.addAction("--- Tracer ---").setEnabled(False)
        
        save_tracer_action = QAction("💾 Save Tracer Log...", self.parent)
        save_tracer_action.setShortcut(get_shortcut('save_tracer'))
        save_tracer_action.triggered.connect(self.parent.save_log)
        file_menu.addAction(save_tracer_action)
        
        load_tracer_action = QAction("📂 Load Tracer Log...", self.parent)
        load_tracer_action.setShortcut(get_shortcut('load_tracer'))
        load_tracer_action.triggered.connect(self.parent.load_log)
        file_menu.addAction(load_tracer_action)
        
        file_menu.addSeparator()
        
        # Transmit section
        file_menu.addAction("--- Transmit ---").setEnabled(False)
        
        save_tx_action = QAction("💾 Save Transmit List...", self.parent)
        save_tx_action.setShortcut(get_shortcut('save_transmit'))
        save_tx_action.triggered.connect(self.parent.save_transmit_list)
        file_menu.addAction(save_tx_action)
        
        load_tx_action = QAction("📂 Load Transmit List...", self.parent)
        load_tx_action.setShortcut(get_shortcut('load_transmit'))
        load_tx_action.triggered.connect(self.parent.load_transmit_list)
        file_menu.addAction(load_tx_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction(t('menu_exit'), self.parent)
        exit_action.setShortcut(get_shortcut('exit'))
        exit_action.triggered.connect(self.parent.close)
        file_menu.addAction(exit_action)
    
    def _create_view_menu(self, menubar: QMenuBar) -> None:
        """Create View menu"""
        view_menu = menubar.addMenu(t('menu_view'))
        
        # Tracer mode
        tracer_mode_action = QAction(t('menu_tracer_mode'), self.parent)
        tracer_mode_action.setCheckable(True)
        tracer_mode_action.setShortcut(get_shortcut('tracer_mode'))
        tracer_mode_action.triggered.connect(self.parent.toggle_tracer_mode)
        view_menu.addAction(tracer_mode_action)
        
        view_menu.addSeparator()
        
        # Split screen
        split_screen_action = QAction(t('split_screen_mode'), self.parent)
        split_screen_action.setCheckable(True)
        split_screen_action.setShortcut(get_shortcut('split_screen'))
        split_screen_action.triggered.connect(self.parent.toggle_split_screen)
        view_menu.addAction(split_screen_action)
        
        view_menu.addSeparator()
        
        # Toggle transmit panel
        toggle_tx_action = QAction("Show/Hide Transmit Panel", self.parent)
        toggle_tx_action.setShortcut(get_shortcut('toggle_transmit'))
        toggle_tx_action.triggered.connect(self.parent.toggle_transmit_panel)
        view_menu.addAction(toggle_tx_action)
    
    def _create_tools_menu(self, menubar: QMenuBar) -> None:
        """Create Tools menu"""
        tools_menu = menubar.addMenu(t('menu_tools'))
        
        # Filters
        filters_action = QAction(f"🔍 {t('menu_filters')}...", self.parent)
        filters_action.setShortcut(get_shortcut('filters'))
        filters_action.triggered.connect(self.parent.show_filter_dialog)
        tools_menu.addAction(filters_action)
        
        # Triggers
        triggers_action = QAction(f"⚡ {t('menu_triggers')}...", self.parent)
        triggers_action.setShortcut(get_shortcut('triggers'))
        triggers_action.triggered.connect(self.parent.show_trigger_dialog)
        tools_menu.addAction(triggers_action)
        
        tools_menu.addSeparator()
        
        # Protocol Decoders submenu
        decoders_menu = tools_menu.addMenu("Protocol Decoders")
        
        # Decoder Manager
        decoder_manager_action = QAction("Manage Decoders...", self.parent)
        decoder_manager_action.setShortcut(get_shortcut('decoder_manager'))
        decoder_manager_action.triggered.connect(self.parent.show_decoder_manager)
        decoders_menu.addAction(decoder_manager_action)
        
        decoders_menu.addSeparator()
        
        # FTCAN Protocol Analyzer
        ftcan_action = QAction("FTCAN 2.0 Analyzer...", self.parent)
        ftcan_action.setShortcut(get_shortcut('ftcan_analyzer'))
        ftcan_action.triggered.connect(self.parent.show_ftcan_dialog)
        decoders_menu.addAction(ftcan_action)
        
        # OBD-II Monitor
        obd2_action = QAction("OBD-II Monitor...", self.parent)
        obd2_action.setShortcut(get_shortcut('obd2_monitor'))
        obd2_action.triggered.connect(self.parent.show_obd2_dialog)
        decoders_menu.addAction(obd2_action)
        
        tools_menu.addSeparator()
        
        # Gateway
        gateway_action = QAction(f"{t('menu_gateway')}...", self.parent)
        gateway_action.setShortcut(get_shortcut('gateway'))
        gateway_action.triggered.connect(self.parent.show_gateway_dialog)
        tools_menu.addAction(gateway_action)
        
        tools_menu.addSeparator()
        
        # Statistics
        stats_action = QAction(f"📊 {t('menu_statistics')}", self.parent)
        stats_action.triggered.connect(self.parent.show_statistics)
        tools_menu.addAction(stats_action)
    
    def _create_settings_menu(self, menubar: QMenuBar) -> None:
        """Create Settings menu"""
        settings_menu = menubar.addMenu(t('menu_settings'))
        
        settings_action = QAction("Settings...", self.parent)
        settings_action.setShortcut(get_shortcut('settings'))
        settings_action.triggered.connect(self.parent.show_settings)
        settings_menu.addAction(settings_action)
    
    def _create_about_menu(self, menubar: QMenuBar) -> None:
        """Create About menu"""
        about_menu = menubar.addMenu("About")
        
        about_app_action = QAction("About CAN Analyzer", self.parent)
        about_app_action.triggered.connect(self.parent.show_about)
        about_menu.addAction(about_app_action)
