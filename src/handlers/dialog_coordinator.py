"""
Dialog Coordinator

Coordinates opening of complex dialogs with validation.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import QMessageBox
from typing import List, Tuple, Optional


class DialogCoordinator:
    """Coordinates complex dialog operations"""
    
    def __init__(self, parent_window, logger):
        """
        Initialize dialog coordinator
        
        Args:
            parent_window: Main window instance
            logger: Logger instance
        """
        self.parent = parent_window
        self.logger = logger
    
    def show_ftcan_dialog(self):
        """Show FTCAN Protocol Analyzer dialog"""
        from ..dialogs import FTCANDialog
        from ..i18n import t
        from ..can_interface import CAN_AVAILABLE
        
        simulation_mode = self.parent.config.get('simulation_mode', False)
        self.logger.info("=== FTCAN Dialog Opening ===")
        self.logger.info(f"Simulation mode: {simulation_mode}")
        self.logger.info(f"Connected: {self.parent.connected}")
        self.logger.info(f"CAN_AVAILABLE: {CAN_AVAILABLE}")
        
        buses_to_use = self._get_ftcan_buses(simulation_mode)
        
        if buses_to_use is None:
            return
        
        if hasattr(self.parent, '_ftcan_dialog') and self.parent._ftcan_dialog:
            self.parent._ftcan_dialog.raise_()
            self.parent._ftcan_dialog.activateWindow()
            return
        
        bus_names = [name for name, _ in buses_to_use]
        self.logger.info(f"Opening FTCAN Dialog with buses: {', '.join(bus_names)}")
        
        dialog = FTCANDialog(self.parent, buses_1mbps=buses_to_use)
        
        for msg in self.parent.received_messages:
            dialog.add_message(msg)
        
        self.parent._ftcan_dialog = dialog
        dialog.finished.connect(self.parent._on_ftcan_dialog_closed)
        dialog.show()
    
    def _get_ftcan_buses(self, simulation_mode: bool) -> Optional[List[Tuple]]:
        """
        Get buses for FTCAN dialog
        
        Args:
            simulation_mode: Whether simulation mode is enabled
            
        Returns:
            List of (name, bus) tuples or None if validation fails
        """
        from ..i18n import t
        from ..can_interface import CAN_AVAILABLE
        
        buses_1mbps_connected = []
        buses_1mbps_config = []
        has_any_bus = False
        
        if self.parent.can_bus_manager:
            for name, bus in self.parent.can_bus_manager.buses.items():
                has_any_bus = True
                self.logger.info(f"Bus {name}: connected={bus.connected}, baudrate={bus.config.baudrate}")
                
                if bus.config.baudrate == 1000000:
                    buses_1mbps_config.append((name, bus))
                    self.logger.info(f"  → Configured for 1Mbps")
                    if bus.connected:
                        buses_1mbps_connected.append((name, bus))
                        self.logger.info(f"  → Connected and ready!")
        
        self.logger.info(f"Results: connected={len(buses_1mbps_connected)}, configured={len(buses_1mbps_config)}")
        
        if not has_any_bus:
            self.logger.warning("No buses found at all")
            QMessageBox.warning(
                self.parent,
                t('decoder_not_connected_title'),
                t('decoder_not_connected_msg')
            )
            return None
        
        buses_to_use = []
        
        if buses_1mbps_connected:
            buses_to_use = buses_1mbps_connected
            self.logger.info(f"✓ Using {len(buses_to_use)} connected 1Mbps bus(es)")
        
        elif (simulation_mode or not CAN_AVAILABLE) and buses_1mbps_config:
            self.logger.info(f"✓ Simulation mode: using {len(buses_1mbps_config)} configured 1Mbps bus(es)")
            buses_to_use = buses_1mbps_config
            if not self.parent.connected:
                self.logger.info("Auto-connecting buses in simulation mode")
                self.parent.can_bus_manager.connect_all(simulation=True)
                self.parent.connected = True
        
        elif self.parent.connected and not buses_1mbps_connected and buses_1mbps_config:
            self.logger.warning("Connected flag is True but no buses actually connected - switching to simulation")
            buses_to_use = buses_1mbps_config
            self.parent.can_bus_manager.connect_all(simulation=True)
        
        if not buses_to_use:
            self._show_ftcan_error(buses_1mbps_config)
            return None
        
        return buses_to_use
    
    def _show_ftcan_error(self, buses_1mbps_config: List[Tuple]):
        """Show FTCAN error message"""
        from ..i18n import t
        
        bus_status = []
        all_disconnected = True
        has_1mbps_config = False
        
        if self.parent.can_bus_manager:
            for name, bus in self.parent.can_bus_manager.buses.items():
                status = "✓ connected" if bus.connected else "✗ disconnected"
                if bus.connected:
                    all_disconnected = False
                baudrate_kbps = bus.config.baudrate // 1000
                if bus.config.baudrate == 1000000:
                    has_1mbps_config = True
                    bus_status.append(f"  • {name}: {status}, {baudrate_kbps} Kbps ✓ (correct baudrate)")
                else:
                    bus_status.append(f"  • {name}: {status}, {baudrate_kbps} Kbps")
        
        status_text = "\n".join(bus_status) if bus_status else "  No buses configured"
        
        if all_disconnected and has_1mbps_config:
            bus_with_1mbps = [name for name, kbps in [(n, b.config.baudrate // 1000) for n, b in self.parent.can_bus_manager.buses.items()] if kbps == 1000]
            bus_name = bus_with_1mbps[0] if bus_with_1mbps else "CAN"
            
            message = (
                f"✓ {bus_name} is correctly configured for FTCAN (1 Mbps)\n\n"
                f"⚠️ Click the \"Connect\" button to start the CAN interface.\n\n"
                f"{t('decoder_configured_buses')}\n{status_text}"
            )
        elif all_disconnected and not has_1mbps_config:
            message = (
                f"{t('ftcan_requires_1mbps')}\n\n"
                f"{t('ftcan_all_disconnected')}\n\n"
                f"{t('decoder_configured_buses')}\n{status_text}\n\n"
                f"{t('ftcan_tip_configure')}"
            )
        else:
            message = (
                f"{t('ftcan_requires_1mbps')}\n\n"
                f"{t('ftcan_no_1mbps_bus')}\n\n"
                f"{t('decoder_current_bus_status')}\n{status_text}\n\n"
                f"{t('ftcan_tip_configure')}"
            )
        
        QMessageBox.warning(
            self.parent,
            t('ftcan_invalid_baudrate_title'),
            message
        )
