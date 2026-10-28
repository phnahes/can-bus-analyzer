"""
Connection Manager - Handles CAN bus connection logic
Extracted from main_window.py to reduce complexity
"""
from typing import Optional, Callable, Dict, List, Any
from PyQt6.QtWidgets import QDialog, QMessageBox
from ..can_bus_manager import CANBusManager, CANBusConfig
from ..can_interface_setup import InterfaceDownError
from ..config import DEFAULT_CHANNEL

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False


class ConnectionManager:
    """Manages CAN bus connections and disconnections"""
    
    def __init__(self, 
                 message_callback: Callable,
                 logger: Any,
                 config: Dict,
                 config_manager,
                 disconnect_callback: Optional[Callable] = None):
        """
        Initialize connection manager
        
        Args:
            message_callback: Callback for received CAN messages
            logger: Logger instance
            config: Configuration dictionary
            config_manager: Configuration manager instance
            disconnect_callback: Callback when device disconnects
        """
        self.message_callback = message_callback
        self.disconnect_callback = disconnect_callback
        self.logger = logger
        self.config = config
        self.config_manager = config_manager
        self.can_bus_manager: Optional[CANBusManager] = None
        self.connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to CAN bus"""
        return self.connected
    
    def get_bus_manager(self) -> Optional[CANBusManager]:
        """Get the CAN bus manager instance"""
        return self.can_bus_manager
    
    def connect(self, parent_widget=None) -> tuple[bool, str, List[str]]:
        """
        Connect to CAN bus
        
        Args:
            parent_widget: Parent widget for dialogs
            
        Returns:
            Tuple of (success, status_message, connected_buses)
        """
        self.logger.info("Attempting to connect to CAN bus")
        
        try:
            simulation_mode = self.config.get('simulation_mode', False)
            
            # Initialize CANBusManager
            self.can_bus_manager = CANBusManager(
                message_callback=self.message_callback,
                logger=self.logger,
                disconnect_callback=self.disconnect_callback
            )
            
            # Load CAN buses from config
            can_buses = self._get_can_buses_config()
            
            # Add all CAN buses to manager
            for bus_cfg in can_buses:
                config = CANBusConfig(
                    name=bus_cfg['name'],
                    channel=bus_cfg['channel'],
                    baudrate=bus_cfg['baudrate'],
                    listen_only=bus_cfg.get('listen_only', True),
                    interface=bus_cfg.get('interface', 'socketcan'),
                    receive_own_messages=bus_cfg.get('receive_own_messages', True),
                    bring_up=bus_cfg.get('bring_up', False),
                    fd=bus_cfg.get('fd', False),
                    dbitrate=bus_cfg.get('dbitrate', 0),
                    tty_baudrate=bus_cfg.get('tty_baudrate', 0),
                )
                self.can_bus_manager.add_bus(config)
            
            # Try real connection if not in simulation mode
            if not simulation_mode and CAN_AVAILABLE:
                success, connected_buses = self._connect_real(can_buses, parent_widget)

                # SocketCAN link down/not configured: offer to fix and retry once.
                if not success and self._offer_interface_setup(can_buses, parent_widget):
                    success, connected_buses = self._connect_real(can_buses, parent_widget)

                if success:
                    self.connected = True
                    return True, self._format_status_message(can_buses, connected_buses, False), connected_buses
                else:
                    # Ask user if they want to use simulation
                    if parent_widget:
                        reply = QMessageBox.question(
                            parent_widget,
                            "Connection Error",
                            f"Não foi possível conectar aos dispositivos.\n\n"
                            f"Deseja conectar em modo simulação?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        
                        if reply == QMessageBox.StandardButton.No:
                            return False, "Connection cancelled", []
                    
                    # Enable simulation mode
                    simulation_mode = True
                    self.config['simulation_mode'] = True
                    self.config_manager.save(self.config)
                    self.logger.info("Simulation mode enabled via connection error dialog")
            
            # Simulation mode
            if simulation_mode or not CAN_AVAILABLE:
                connected_buses = self._connect_simulation(can_buses, parent_widget)
                self.connected = True
                return True, self._format_status_message(can_buses, connected_buses, True), connected_buses
            
        except Exception as e:
            self.logger.error(f"Error while connecting: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def disconnect(self) -> bool:
        """
        Disconnect from CAN bus
        
        Returns:
            True if successful
        """
        self.logger.info("Disconnecting from CAN bus")
        
        try:
            if self.can_bus_manager:
                self.can_bus_manager.disconnect_all()
                self.can_bus_manager = None
            
            self.connected = False
            return True
            
        except Exception as e:
            self.logger.error(f"Error while disconnecting: {str(e)}")
            return False
    
    def _get_can_buses_config(self) -> List[Dict]:
        """Get CAN buses configuration from config"""
        can_buses = self.config.get('can_buses', [])
        if not can_buses:
            # Fallback to legacy single-bus config
            can_buses = [{
                'name': DEFAULT_CHANNEL,
                'channel': self.config.get('channel', 'can0'),
                'baudrate': self.config.get('baudrate', 500000),
                'interface': 'socketcan',
                'listen_only': self.config.get('listen_only', True),
                'bring_up': self.config.get('bring_up', False),
                'fd': self.config.get('fd', False),
                'dbitrate': self.config.get('dbitrate', 0)
            }]
        return can_buses

    def _interface_setup_requests(self, can_buses: List[Dict]) -> List[Dict]:
        """Build dialog requests from the buses that failed with InterfaceDownError."""
        errors = getattr(self.can_bus_manager, 'connect_errors', {}) or {}
        requests = []

        for bus_name, error in errors.items():
            if not isinstance(error, InterfaceDownError):
                continue
            bus_cfg = next((b for b in can_buses if b.get('name') == bus_name), None) or {}
            requests.append({
                'channel': error.channel,
                'bitrate': bus_cfg.get('baudrate', 500000),
                'dbitrate': bus_cfg.get('dbitrate', 0),
                'fd': bus_cfg.get('fd', False),
                'listen_only': bus_cfg.get('listen_only', False),
                'command': error.command,
                'detail': str(error),
            })

        return requests

    def _offer_interface_setup(self, can_buses: List[Dict], parent_widget) -> bool:
        """Show the interface setup dialog. Returns True when the user fixed it."""
        requests = self._interface_setup_requests(can_buses)
        if not requests or parent_widget is None:
            return False

        from ..dialogs import InterfaceSetupDialog

        self.logger.warning(
            "Interface not ready: " + "; ".join(
                f"{r['channel']} ({r['detail']})" for r in requests
            )
        )

        dialog = InterfaceSetupDialog(requests, parent_widget)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return accepted and dialog.configured
    
    def _connect_real(self, can_buses: List[Dict], parent_widget) -> tuple[bool, List[str]]:
        """
        Connect to real CAN devices
        
        Returns:
            Tuple of (success, list of connected bus names)
        """
        self.logger.info("Attempting to connect all CAN buses")
        
        try:
            # Connect all CAN buses
            self.can_bus_manager.connect_all(simulation=False)
            
            # Check if at least one bus connected successfully
            connected_buses = [name for name in self.can_bus_manager.get_bus_names() 
                              if self.can_bus_manager.is_bus_connected(name)]
            
            if connected_buses:
                self.logger.info(f"Real CAN connection established: {', '.join(connected_buses)}")
                return True, connected_buses

            for bus_name, error in (getattr(self.can_bus_manager, 'connect_errors', {}) or {}).items():
                self.logger.error(f"Bus '{bus_name}' failed: {error}")

            raise Exception("No CAN bus could be connected")
                
        except Exception as e:
            self.logger.error(f"Error connecting to real devices: {str(e)}")
            self.logger.warning("Falling back to simulation mode")
            return False, []
    
    def _connect_simulation(self, can_buses: List[Dict], parent_widget) -> List[str]:
        """
        Connect in simulation mode
        
        Returns:
            List of connected bus names
        """
        self.logger.warning("Connecting in simulation mode")
        
        # Connect all buses in simulation mode
        self.can_bus_manager.connect_all(simulation=True)
        
        if not self.config.get('simulation_mode', False) and parent_widget:
            QMessageBox.information(
                parent_widget,
                "Simulation Mode",
                f"Conectado em modo simulação.\n\n"
                f"Para usar um dispositivo real:\n"
                f"1. Desmarque 'Simulation Mode' nas Settings\n"
                f"2. Selecione o dispositivo correto\n"
                f"3. Clique em Connect novamente"
            )
        
        return self.can_bus_manager.get_bus_names()
    
    def _format_status_message(self, can_buses: List[Dict], connected_buses: List[str], 
                               is_simulation: bool) -> str:
        """Format status message for UI - shows ALL buses with compact details"""
        status_parts = []
        
        for bus_config in can_buses:
            bus_name = bus_config['name']
            baudrate_kb = bus_config['baudrate'] // 1000
            channel = bus_config.get('channel', 'N/A')
            listen_only = bus_config.get('listen_only', True)
            mode = "LO" if listen_only else "N"  # Compact: Listen-Only = LO, Normal = N

            # SocketCAN owns the bit rate: show what the kernel is really using.
            info = None
            if self.can_bus_manager is not None:
                info = self.can_bus_manager.get_bus_info(bus_name)
            actual = (info or {}).get('actual_bitrate')
            if actual and actual != bus_config['baudrate']:
                baudrate_label = f"{baudrate_kb}k→{actual // 1000}k"
            else:
                baudrate_label = f"{baudrate_kb}k"
            
            is_conn = bus_name in connected_buses
            conn_icon = "✓" if is_conn else "✗"
            
            # Extract short device name (last part after last /)
            if channel and '/' in channel:
                short_channel = channel.split('/')[-1]
                # Further shorten common prefixes
                if short_channel.startswith('cu.'):
                    short_channel = short_channel[3:]  # Remove 'cu.' prefix
            else:
                short_channel = channel
            
            if is_simulation:
                status_parts.append(f"{bus_name}:{baudrate_label},SIM,{mode},{conn_icon}")
            else:
                # Limit channel name to 20 chars
                if len(short_channel) > 20:
                    short_channel = short_channel[:17] + "..."
                status_parts.append(f"{bus_name}:{baudrate_label},{short_channel},{mode},{conn_icon}")
        
        return " | ".join(status_parts)
    
    def get_device_info(self, can_buses: List[Dict], connected_buses: List[str], 
                       is_simulation: bool) -> str:
        """Get device information string for UI"""
        if len(connected_buses) > 1:
            # Multi-CAN
            device_parts = []
            for bus_name in connected_buses:
                bus_config = next((b for b in can_buses if b['name'] == bus_name), None)
                if bus_config:
                    suffix = " (Sim)" if is_simulation else ""
                    device_parts.append(f"{bus_name}→{bus_config['channel']}{suffix}")
            return " | ".join(device_parts)
        else:
            # Single CAN
            first_bus = can_buses[0] if can_buses else {'channel': 'can0'}
            device_info = first_bus['channel']
            suffix = " (Sim)" if is_simulation else ""
            return f"Device: {device_info}{suffix}"
