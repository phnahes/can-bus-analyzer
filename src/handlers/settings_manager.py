"""
Settings Manager

Manages application settings and configuration changes.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import QDialog, QMessageBox
from typing import Dict, Tuple, Optional


class SettingsManager:
    """Manages application settings"""
    
    def __init__(self, parent_window, logger, config_manager):
        """
        Initialize settings manager
        
        Args:
            parent_window: Main window instance
            logger: Logger instance
            config_manager: Configuration manager instance
        """
        self.parent = parent_window
        self.logger = logger
        self.config_manager = config_manager
    
    def show_dialog(self, config, usb_monitor) -> Optional[Dict]:
        """
        Show settings dialog
        
        Args:
            config: Current configuration
            usb_monitor: USB monitor instance
            
        Returns:
            Updated config or None if cancelled
        """
        try:
            from ..dialogs import SettingsDialog
            
            self.logger.info("Opening settings dialog")
            dialog = SettingsDialog(self.parent, config, usb_monitor)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_config = dialog.get_config()
                self.logger.info(f"Settings updated: {new_config}")
                return new_config
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error opening/processing settings: {str(e)}", exc_info=True)
            QMessageBox.critical(self.parent, "Settings Error", f"Error: {str(e)}")
            return None
    
    def apply_config_changes(self, old_config: Dict, new_config: Dict) -> Tuple[bool, bool, bool]:
        """
        Apply configuration changes
        
        Args:
            old_config: Previous configuration
            new_config: New configuration
            
        Returns:
            Tuple of (language_changed, theme_changed, mode_changed)
        """
        language_changed = old_config.get('language', 'en') != new_config.get('language', 'en')
        theme_changed = old_config.get('theme', 'system') != new_config.get('theme', 'system')
        mode_changed = old_config.get('listen_only', True) != new_config.get('listen_only', True)
        
        # Save config
        self.config_manager.update(new_config)
        self.logger.info("Configuration saved to config.json")
        
        # Apply language change
        if language_changed:
            new_language = new_config.get('language', 'en')
            from ..i18n import get_i18n
            i18n = get_i18n()
            i18n.set_language(new_language)
            self.logger.info(f"Language changed to: {new_language}")
        
        # Apply theme change
        if theme_changed:
            new_theme = new_config.get('theme', 'system')
            self.logger.info(f"Theme changed to: {new_theme}")
        
        # Log mode change
        if mode_changed:
            new_listen_only = new_config.get('listen_only', True)
            self.logger.info(f"Mode changed to: {'Listen Only' if new_listen_only else 'Normal'}")
        
        return language_changed, theme_changed, mode_changed
    
    def get_notification_message(self, language_changed: bool, theme_changed: bool) -> str:
        """
        Get notification message based on changes
        
        Args:
            language_changed: Whether language was changed
            theme_changed: Whether theme was changed
            
        Returns:
            Notification message
        """
        from ..i18n import t
        
        if language_changed and theme_changed:
            return f"✅ {t('msg_language_and_theme_applied')}"
        elif language_changed:
            return f"✅ {t('msg_language_applied')}"
        elif theme_changed:
            return f"✅ {t('msg_theme_applied')}"
        else:
            return f"✅ {t('msg_settings_saved')}"
