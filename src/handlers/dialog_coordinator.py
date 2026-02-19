"""
Dialog Coordinator

Coordinates opening of complex dialogs with validation.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import QMessageBox


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

        simulation_mode = self.parent.config.get('simulation_mode', False)
        success, buses_to_use, error_msg, error_title = self.parent.dialog_mgr.validate_ftcan_buses(
            self.parent.can_bus_manager,
            self.parent.connected,
            simulation_mode
        )

        if not success:
            if error_msg and error_title:
                QMessageBox.warning(self.parent, error_title, error_msg)
            return

        # When using config buses (none actually connected at 1Mbps), auto-connect in simulation
        any_connected = any(bus.connected for _, bus in buses_to_use)
        if not any_connected and self.parent.can_bus_manager:
            self.logger.info("Auto-connecting buses in simulation mode")
            self.parent.can_bus_manager.connect_all(simulation=True)
            self.parent.connected = True

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

    def show_bap_dialog(self):
        """Show VAG BAP Analyzer dialog"""
        from ..dialogs import BAPDialog

        if hasattr(self.parent, '_bap_dialog') and self.parent._bap_dialog:
            self.parent._bap_dialog.raise_()
            self.parent._bap_dialog.activateWindow()
            return

        dialog = BAPDialog(self.parent)

        # Seed with already captured messages (helps when opening after running).
        for msg in getattr(self.parent, "received_messages", []):
            try:
                dialog.add_message(msg)
            except Exception:
                continue

        self.parent._bap_dialog = dialog
        dialog.finished.connect(self.parent._on_bap_dialog_closed)
        dialog.show()
