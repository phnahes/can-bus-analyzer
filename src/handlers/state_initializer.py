"""
State Initializer

Initializes application state and variables.
Extracted from main_window.py to reduce complexity.
"""

import threading
import queue
from typing import Optional, List, Dict
import can


class StateInitializer:
    """Initializes application state"""
    
    @staticmethod
    def init_connection_state(parent):
        """Initialize connection-related state"""
        parent.can_bus: Optional[can.BusABC] = None
        parent.can_bus_manager = None
        parent.receive_thread: Optional[threading.Thread] = None
        parent.message_queue = queue.Queue()
        parent.received_messages: List = []
        parent.transmit_messages: List[Dict] = []
    
    @staticmethod
    def init_dialog_state(parent):
        """Initialize dialog references"""
        parent._ftcan_dialog = None
        parent._obd2_dialog = None
    
    @staticmethod
    def init_playback_state(parent):
        """Initialize playback-related state"""
        parent.playback_active = False
        parent.playback_paused = False
        parent.playback_thread: Optional[threading.Thread] = None
        parent.playback_stop_event = threading.Event()
        parent.current_playback_row = -1
        parent.recording = False
    
    @staticmethod
    def init_filter_state(parent):
        """Initialize filter-related state"""
        parent.message_filters = {
            'enabled': False,
            'id_filters': [],
            'data_filters': [],
            'show_only': True,
            'channel_filters': {}
        }
        parent.triggers = []
        parent.triggers_enabled = False
        parent.logger.info(f"Message filters initialized: enabled={parent.message_filters['enabled']}")
    
    @staticmethod
    def init_transmit_state(parent):
        """Initialize transmit-related state"""
        parent.periodic_send_active = False
        parent.editing_tx_row = -1
    
    @staticmethod
    def init_split_screen_state(parent):
        """Initialize split-screen state"""
        parent.split_screen_mode = False
        parent.split_screen_left_channel = None
        parent.split_screen_right_channel = None
        parent.receive_table_left = None
        parent.receive_table_right = None
    
    @staticmethod
    def init_gateway_state(parent):
        """Initialize gateway state"""
        from ..models import GatewayConfig
        parent.gateway_config = GatewayConfig()
    
    @staticmethod
    def init_diff_state(parent):
        """Initialize diff mode state"""
        from ..handlers import DiffConfig
        parent.diff_config = DiffConfig()
        # Load from config if available
        if 'diff_mode' in parent.config:
            parent.diff_config = DiffConfig.from_dict(parent.config['diff_mode'])
        # Diff always starts OFF on app startup (even if last run had it enabled).
        parent.diff_config.enabled = False
        parent.logger.info("Diff mode initialized: enabled=False (startup default)")
    
    @staticmethod
    def init_theme_state(parent):
        """Initialize theme state"""
        from ..theme import should_use_dark_mode
        parent.theme_preference = parent.config.get('theme', 'system')
        parent.is_dark_mode = should_use_dark_mode(parent.theme_preference)
        parent.logger.info(f"Theme preference: {parent.theme_preference}, Dark mode: {parent.is_dark_mode}")
    
    @staticmethod
    def init_all_state(parent):
        """Initialize all application state"""
        StateInitializer.init_connection_state(parent)
        StateInitializer.init_dialog_state(parent)
        StateInitializer.init_playback_state(parent)
        StateInitializer.init_filter_state(parent)
        StateInitializer.init_transmit_state(parent)
        StateInitializer.init_split_screen_state(parent)
        StateInitializer.init_gateway_state(parent)
        StateInitializer.init_diff_state(parent)
        StateInitializer.init_theme_state(parent)
