"""
Dialog Manager - Handles dialog opening logic
Extracted from main_window.py to reduce complexity
"""
from typing import Optional, List, Tuple, Any
from PyQt6.QtWidgets import QMessageBox

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False


class DialogManager:
    """Manages dialog opening and validation logic"""
    
    def __init__(self, logger: Any):
        """
        Initialize dialog manager
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def validate_ftcan_buses(self, 
                            can_bus_manager,
                            connected: bool,
                            simulation_mode: bool,
                            parent_widget=None) -> Tuple[bool, List, str]:
        """
        Validate CAN buses for FTCAN dialog
        
        Args:
            can_bus_manager: CANBusManager instance
            connected: Connection status
            simulation_mode: Simulation mode flag
            parent_widget: Parent widget for dialogs
            
        Returns:
            Tuple of (success, list of buses to use, error message if any)
        """
        self.logger.info(f"=== FTCAN Dialog Validation ===")
        self.logger.info(f"Simulation mode: {simulation_mode}")
        self.logger.info(f"Connected: {connected}")
        self.logger.info(f"CAN_AVAILABLE: {CAN_AVAILABLE}")
        
        # Check if there is at least one bus at 1 Mbps
        buses_1mbps_connected = []  # Actually connected buses at 1Mbps
        buses_1mbps_config = []     # Configured for 1Mbps (for simulation mode)
        has_any_bus = False
        
        if can_bus_manager:
            for name, bus in can_bus_manager.buses.items():
                has_any_bus = True
                self.logger.info(f"Bus {name}: connected={bus.connected}, baudrate={bus.config.baudrate}")
                
                # Check if configured for 1Mbps
                if bus.config.baudrate == 1000000:
                    buses_1mbps_config.append((name, bus))
                    self.logger.info(f"  → Configured for 1Mbps")
                    # If connected, add to connected list
                    if bus.connected:
                        buses_1mbps_connected.append((name, bus))
                        self.logger.info(f"  → Connected and ready!")
        
        self.logger.info(f"Results: connected={len(buses_1mbps_connected)}, configured={len(buses_1mbps_config)}")
        
        # If no buses at all, show connection error
        if not has_any_bus:
            self.logger.warning("No buses found at all")
            error_msg = "No CAN buses configured. Please connect first."
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "Not Connected",
                    "Please connect to CAN bus first."
                )
            return False, [], error_msg
        
        # Determine which buses to use
        buses_to_use = []
        
        # Priority 1: Use connected 1Mbps buses (real connection)
        if buses_1mbps_connected:
            buses_to_use = buses_1mbps_connected
            self.logger.info(f"✓ Using {len(buses_to_use)} connected 1Mbps bus(es)")
        
        # Priority 2: In simulation mode, use configured 1Mbps buses
        elif (simulation_mode or not CAN_AVAILABLE) and buses_1mbps_config:
            self.logger.info(f"✓ Simulation mode: using {len(buses_1mbps_config)} configured 1Mbps bus(es)")
            buses_to_use = buses_1mbps_config
        
        # Priority 3: Connected but buses show disconnected - try simulation
        elif connected and not buses_1mbps_connected and buses_1mbps_config:
            self.logger.warning("Connected flag is True but no buses actually connected")
            buses_to_use = buses_1mbps_config
        
        # If no buses at 1Mbps, show baudrate error
        if not buses_to_use:
            error_msg = self._build_baudrate_error_message(can_bus_manager, buses_1mbps_config)
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "Invalid Baudrate",
                    error_msg
                )
            return False, [], error_msg
        
        # Success
        bus_names = [name for name, _ in buses_to_use]
        self.logger.info(f"Validation successful: {', '.join(bus_names)}")
        return True, buses_to_use, ""
    
    def _build_baudrate_error_message(self, can_bus_manager, buses_1mbps_config: List) -> str:
        """Build detailed error message for baudrate mismatch"""
        # Build detailed message with current bus status
        bus_status = []
        all_disconnected = True
        has_1mbps_config = len(buses_1mbps_config) > 0
        
        if can_bus_manager:
            for name, bus in can_bus_manager.buses.items():
                status = "✓ connected" if bus.connected else "✗ disconnected"
                if bus.connected:
                    all_disconnected = False
                baudrate_kbps = bus.config.baudrate // 1000
                # Check if this bus is configured for 1Mbps
                if bus.config.baudrate == 1000000:
                    bus_status.append(f"  • {name}: {status}, {baudrate_kbps} Kbps ✓ (correct baudrate)")
                else:
                    bus_status.append(f"  • {name}: {status}, {baudrate_kbps} Kbps")
        
        status_text = "\n".join(bus_status) if bus_status else "  No buses configured"
        
        # Different message based on situation
        if all_disconnected and has_1mbps_config:
            # Has correct config but not connected
            bus_with_1mbps = [name for name, bus in can_bus_manager.buses.items() 
                            if bus.config.baudrate == 1000000]
            bus_name = bus_with_1mbps[0] if bus_with_1mbps else "CAN"
            
            message = (
                f"✓ {bus_name} is correctly configured for FTCAN (1 Mbps)\n\n"
                f"⚠️ Click the \"Connect\" button to start the CAN interface.\n\n"
                f"Configured buses:\n{status_text}"
            )
        elif all_disconnected and not has_1mbps_config:
            # Not connected AND no 1Mbps config
            message = (
                f"FTCAN protocol requires 1 Mbps baudrate.\n\n"
                f"All buses are disconnected.\n\n"
                f"Configured buses:\n{status_text}\n\n"
                f"Tip: Configure at least one bus with 1 Mbps in Settings."
            )
        else:
            # Connected but wrong baudrate
            message = (
                f"FTCAN protocol requires 1 Mbps baudrate.\n\n"
                f"No bus configured with 1 Mbps.\n\n"
                f"Current bus status:\n{status_text}\n\n"
                f"Tip: Configure at least one bus with 1 Mbps in Settings."
            )
        
        return message
