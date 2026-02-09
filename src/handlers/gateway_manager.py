"""
Gateway Manager

Manages CAN Gateway configuration and operations.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QTimer
from typing import Optional, Any


class GatewayManager:
    """Manages CAN Gateway functionality"""
    
    def __init__(self, parent_window, logger):
        """
        Initialize gateway manager
        
        Args:
            parent_window: Main window instance
            logger: Logger instance
        """
        self.parent = parent_window
        self.logger = logger
        self.gateway_config = None
    
    def show_dialog(self, can_bus_manager, gateway_config):
        """
        Show the Gateway configuration dialog
        
        Args:
            can_bus_manager: CAN bus manager instance
            gateway_config: Current gateway configuration
            
        Returns:
            Updated gateway config or None if cancelled
        """
        if not can_bus_manager or len(can_bus_manager.get_bus_names()) < 2:
            from ..i18n import t
            QMessageBox.warning(
                self.parent,
                t('warning'),
                "Gateway requires at least 2 CAN buses configured.\n"
                "Please configure multiple CAN buses in Settings first."
            )
            return None
        
        bus_names = can_bus_manager.get_bus_names()
        
        from ..dialogs import GatewayDialog
        dialog = GatewayDialog(self.parent, gateway_config, bus_names)
        
        # Update stats periodically while dialog is open
        def update_stats():
            if can_bus_manager:
                stats = can_bus_manager.get_gateway_stats()
                dialog.update_stats(stats)
        
        # Create timer for stats update
        stats_timer = QTimer()
        stats_timer.timeout.connect(update_stats)
        stats_timer.start(1000)  # Update every second
        
        result = None
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get updated config
            result = dialog.get_config()
            self.logger.info(f"Gateway config updated: enabled={result.enabled}")
        
        stats_timer.stop()
        return result
    
    def toggle_from_toolbar(self, gateway_config, can_bus_manager, is_checked: bool):
        """
        Toggle Gateway enable/disable from toolbar button
        
        Args:
            gateway_config: Current gateway configuration
            can_bus_manager: CAN bus manager instance
            is_checked: New checked state
            
        Returns:
            Tuple of (success, updated_config)
        """
        if not can_bus_manager or len(can_bus_manager.get_bus_names()) < 2:
            from ..i18n import t
            QMessageBox.warning(
                self.parent,
                t('warning'),
                "Gateway requires at least 2 CAN buses configured.\n"
                "Please configure multiple CAN buses in Settings first."
            )
            return False, gateway_config
        
        # Toggle gateway state
        gateway_config.enabled = is_checked
        
        # Apply to CAN bus manager
        if can_bus_manager:
            can_bus_manager.set_gateway_config(gateway_config)
        
        # Log
        if gateway_config.enabled:
            self.logger.info("Gateway enabled from toolbar")
        else:
            self.logger.info("Gateway disabled from toolbar")
        
        return True, gateway_config
    
    def get_status_message(self, gateway_config) -> str:
        """
        Get status message for gateway
        
        Args:
            gateway_config: Gateway configuration
            
        Returns:
            Status message string
        """
        if gateway_config.enabled:
            route_count = len([r for r in gateway_config.routes if r.enabled])
            block_count = len([r for r in gateway_config.block_rules if r.enabled])
            modify_count = len([r for r in gateway_config.modify_rules if r.enabled])
            
            return f"🌉 Gateway ON | {route_count} route(s), {block_count} block(s), {modify_count} modify"
        else:
            return "🌉 Gateway OFF"
    
    def get_toolbar_status(self, gateway_config) -> str:
        """
        Get toolbar status for gateway
        
        Args:
            gateway_config: Gateway configuration
            
        Returns:
            Toolbar status string
        """
        if gateway_config.enabled:
            route_count = len([r for r in gateway_config.routes if r.enabled])
            return f"🌉 Gateway ON | {route_count} active route(s)"
        else:
            return "🌉 Gateway OFF"
