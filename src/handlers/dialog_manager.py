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
                            simulation_mode: bool) -> Tuple[bool, List, str, str]:
        """
        Validate CAN buses for FTCAN dialog.
        Does not show UI; caller is responsible for showing error messages.

        Args:
            can_bus_manager: CANBusManager instance
            connected: Connection status
            simulation_mode: Simulation mode flag

        Returns:
            Tuple of (success, buses_to_use, error_message, error_title).
            On success: error_message and error_title are empty strings.
            On failure: caller should show QMessageBox.warning(parent, error_title, error_message).
        """
        from ..i18n import t

        self.logger.info("=== FTCAN Dialog Validation ===")
        self.logger.info(f"Simulation mode: {simulation_mode}")
        self.logger.info(f"Connected: {connected}")
        self.logger.info(f"CAN_AVAILABLE: {CAN_AVAILABLE}")

        buses_1mbps_connected = []
        buses_1mbps_config = []
        has_any_bus = False

        if can_bus_manager:
            for name, bus in can_bus_manager.buses.items():
                has_any_bus = True
                self.logger.info(f"Bus {name}: connected={bus.connected}, baudrate={bus.config.baudrate}")
                if bus.config.baudrate == 1000000:
                    buses_1mbps_config.append((name, bus))
                    self.logger.info("  → Configured for 1Mbps")
                    if bus.connected:
                        buses_1mbps_connected.append((name, bus))
                        self.logger.info("  → Connected and ready!")

        self.logger.info(f"Results: connected={len(buses_1mbps_connected)}, configured={len(buses_1mbps_config)}")

        if not has_any_bus:
            self.logger.warning("No buses found at all")
            return False, [], t('decoder_not_connected_msg'), t('decoder_not_connected_title')

        buses_to_use = []

        if buses_1mbps_connected:
            buses_to_use = buses_1mbps_connected
            self.logger.info(f"✓ Using {len(buses_to_use)} connected 1Mbps bus(es)")
        elif (simulation_mode or not CAN_AVAILABLE) and buses_1mbps_config:
            self.logger.info(f"✓ Simulation mode: using {len(buses_1mbps_config)} configured 1Mbps bus(es)")
            buses_to_use = buses_1mbps_config
        elif connected and not buses_1mbps_connected and buses_1mbps_config:
            self.logger.warning("Connected flag is True but no buses actually connected")
            buses_to_use = buses_1mbps_config

        if not buses_to_use:
            error_msg = self._build_baudrate_error_message(can_bus_manager, buses_1mbps_config)
            return False, [], error_msg, t('ftcan_invalid_baudrate_title')

        bus_names = [name for name, _ in buses_to_use]
        self.logger.info(f"Validation successful: {', '.join(bus_names)}")
        return True, buses_to_use, "", ""

    def _build_baudrate_error_message(self, can_bus_manager, buses_1mbps_config: List) -> str:
        """Build detailed error message for baudrate mismatch (i18n)."""
        from ..i18n import t

        bus_status = []
        all_disconnected = True
        has_1mbps_config = len(buses_1mbps_config) > 0

        if can_bus_manager:
            for name, bus in can_bus_manager.buses.items():
                status = "✓ connected" if bus.connected else "✗ disconnected"
                if bus.connected:
                    all_disconnected = False
                baudrate_kbps = bus.config.baudrate // 1000
                if bus.config.baudrate == 1000000:
                    bus_status.append(f"  • {name}: {status}, {baudrate_kbps} Kbps ✓ (correct baudrate)")
                else:
                    bus_status.append(f"  • {name}: {status}, {baudrate_kbps} Kbps")

        status_text = "\n".join(bus_status) if bus_status else "  No buses configured"

        if all_disconnected and has_1mbps_config:
            bus_with_1mbps = [name for name, bus in can_bus_manager.buses.items()
                              if bus.config.baudrate == 1000000]
            bus_name = bus_with_1mbps[0] if bus_with_1mbps else "CAN"
            message = (
                f"✓ {bus_name} {t('ftcan_bus_configured_1mbps')}\n\n"
                f"⚠️ {t('ftcan_click_connect')}\n\n"
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
        return message
