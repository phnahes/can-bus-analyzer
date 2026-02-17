"""
Connect Handler
Handles CAN bus connection logic
"""

from ..config import DEFAULT_CHANNEL
from ..handlers.transmit_handler import TransmitHandler
from ..i18n import t


class ConnectHandler:
    """Handles CAN bus connection"""
    
    def __init__(self, parent):
        """Initialize the handler
        
        Args:
            parent: The parent window (main_window)
        """
        self.parent = parent
        self.logger = parent.logger
    
    def connect(self):
        """Connect to CAN bus (with multi-CAN support)"""
        success, status_msg, connected_buses = self.parent.connection_mgr.connect(
            parent_widget=self.parent
        )
        
        if not success:
            return
        
        try:
            simulation_mode = self.parent.config.get('simulation_mode', False)
            can_buses = self._get_can_buses_config()
            
            # Initialize bus manager and connection state
            self.parent.can_bus_manager = self.parent.connection_mgr.get_bus_manager()
            self.parent.connected = True
            # Only these buses should be considered "expected" for watchdog.
            self.parent._expected_connected_buses = set(connected_buses)
            
            # Initialize transmit handler
            self.parent.transmit_handler = TransmitHandler(
                self.parent, 
                self.parent.can_bus_manager
            )
            self.parent.transmit_handler.on_count_updated = self.parent._update_tx_count
            
            # Update TX source combo
            self._update_tx_source_combo(connected_buses)
            
            # Update UI status
            self._update_connection_status(status_msg, can_buses, connected_buses, simulation_mode)
            
            # Enable/disable buttons
            self._update_button_states()
            
            # Update mode label
            self._update_mode_label()
            
            # Start receive thread if needed
            self._start_receive_thread()
            
        except Exception as e:
            self.logger.error(f"Error during connection: {e}", exc_info=True)
            from ..ui.message_box_helper import MessageBoxHelper
            MessageBoxHelper.show_error(
                self.parent, 
                "Connection Error", 
                f"Error during connection: {str(e)}"
            )
    
    def _get_can_buses_config(self) -> list:
        """Get CAN buses configuration from config"""
        can_buses = self.parent.config.get('can_buses', [])
        if not can_buses:
            can_buses = [{
                'name': DEFAULT_CHANNEL,
                'channel': self.parent.config.get('channel', 'can0'),
                'baudrate': self.parent.config.get('baudrate', 500000)
            }]
        return can_buses
    
    def _update_tx_source_combo(self, connected_buses: list):
        """Update TX source combo box with connected buses"""
        self.parent.tx_source_combo.clear()
        for bus_name in connected_buses:
            self.parent.tx_source_combo.addItem(bus_name)
    
    def _update_connection_status(self, status_msg: str, can_buses: list, 
                                   connected_buses: list, simulation_mode: bool):
        """Update connection status labels and show notification"""
        self.parent.connection_status.setText(status_msg)
        
        device_info = self.parent.connection_mgr.get_device_info(
            can_buses, connected_buses, simulation_mode
        )
        self.parent.device_label.setText(device_info)
        
        # Update consolidated status bar
        self.parent.update_consolidated_status()
        
        first_bus = can_buses[0] if can_buses else {'baudrate': 500000}
        if simulation_mode:
            self.parent.show_notification(
                t('notif_simulation_mode', baudrate=first_bus['baudrate']//1000), 
                5000
            )
        else:
            self.parent.show_notification(
                t('notif_connected', 
                  channel=', '.join(connected_buses), 
                  baudrate=first_bus['baudrate']//1000), 
                5000
            )
    
    def _update_button_states(self):
        """Update button enabled states after connection"""
        self.parent.btn_connect.setEnabled(False)
        self.parent.btn_disconnect.setEnabled(True)
        self.parent.btn_pause.setEnabled(True)
        self.parent.btn_record.setEnabled(True)
        
        # Enable gateway button if multiple buses
        if (self.parent.can_bus_manager and 
            len(self.parent.can_bus_manager.get_bus_names()) >= 2):
            self.parent.btn_gateway.setEnabled(True)
            self.parent.update_gateway_button_state()
    
    def _update_mode_label(self):
        """Update mode label based on listen_only setting"""
        if self.parent.config.get('listen_only', True):
            self.parent.mode_label.setText(t('status_listen_only'))
        else:
            self.parent.mode_label.setText(t('status_normal'))
    
    def _start_receive_thread(self):
        """Start receive thread if using legacy mode (single CAN bus)"""
        if not self.parent.can_bus_manager and self.parent.can_bus:
            import threading
            self.parent.receive_thread = threading.Thread(
                target=self.parent.receive_loop, 
                daemon=True
            )
            self.parent.receive_thread.start()
            self.logger.info("Thread de recepção iniciada (legacy mode)")
        elif self.parent.can_bus_manager:
            self.logger.info("Using CANBusManager receive threads")
        
        # Generate sample data if in simulation mode
        simulation_mode = self.parent.config.get('simulation_mode', False)
        try:
            from ..can_interface import CAN_AVAILABLE
        except ImportError:
            CAN_AVAILABLE = False
        
        if simulation_mode or not CAN_AVAILABLE:
            self.parent.generate_sample_data()
        
        self.logger.info("Connection established successfully")
