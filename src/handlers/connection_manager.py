"""
Connection Manager - Handles CAN bus connection logic
Extracted from main_window.py to reduce complexity
"""
from typing import Optional, Callable, Dict, List, Any
from PyQt6.QtWidgets import QMessageBox
from ..can_bus_manager import CANBusManager, CANBusConfig
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
        self.logger.info("Tentando conectar ao barramento CAN")
        
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
                    receive_own_messages=bus_cfg.get('receive_own_messages', True)
                )
                self.can_bus_manager.add_bus(config)
            
            # Try real connection if not in simulation mode
            if not simulation_mode and CAN_AVAILABLE:
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
            self.logger.error(f"Erro ao conectar: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def disconnect(self) -> bool:
        """
        Disconnect from CAN bus
        
        Returns:
            True if successful
        """
        self.logger.info("Desconectando do barramento CAN")
        
        try:
            if self.can_bus_manager:
                self.can_bus_manager.disconnect_all()
                self.can_bus_manager = None
            
            self.connected = False
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao desconectar: {str(e)}")
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
                'listen_only': self.config.get('listen_only', True)
            }]
        return can_buses
    
    def _connect_real(self, can_buses: List[Dict], parent_widget) -> tuple[bool, List[str]]:
        """
        Connect to real CAN devices
        
        Returns:
            Tuple of (success, list of connected bus names)
        """
        self.logger.info("Tentando conectar todos os barramentos CAN")
        
        try:
            # Connect all CAN buses
            self.can_bus_manager.connect_all(simulation=False)
            
            # Check if at least one bus connected successfully
            connected_buses = [name for name in self.can_bus_manager.get_bus_names() 
                              if self.can_bus_manager.is_bus_connected(name)]
            
            if connected_buses:
                self.logger.info(f"Conexão real estabelecida: {', '.join(connected_buses)}")
                return True, connected_buses
            else:
                raise Exception("Nenhum barramento CAN conseguiu conectar")
                
        except Exception as e:
            self.logger.error(f"Erro ao conectar aos dispositivos reais: {str(e)}")
            self.logger.warning("Tentando modo simulação como fallback")
            return False, []
    
    def _connect_simulation(self, can_buses: List[Dict], parent_widget) -> List[str]:
        """
        Connect in simulation mode
        
        Returns:
            List of connected bus names
        """
        self.logger.warning("Conectando em modo simulação")
        
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
                status_parts.append(f"{bus_name}:{baudrate_kb}k,SIM,{mode},{conn_icon}")
            else:
                # Limit channel name to 20 chars
                if len(short_channel) > 20:
                    short_channel = short_channel[:17] + "..."
                status_parts.append(f"{bus_name}:{baudrate_kb}k,{short_channel},{mode},{conn_icon}")
        
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
