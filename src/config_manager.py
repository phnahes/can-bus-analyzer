"""
Configuration Manager - Manages application settings persistence
"""

import json
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Manages application configuration with file persistence"""
    
    DEFAULT_CONFIG = {
        'language': 'en',
        'theme': 'system',
        'baudrate': 500000,
        'interface': 'socketcan',
        'channel': 'can0',
        'listen_only': True,
        'timestamp': True,
        'com_baudrate': '115200 bit/s',
        'rts_hs': False,
        'baudrate_reg': 'FFFFFF'
    }
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = Path(config_file)
        self.config = self.load()
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file
        
        Returns:
            Configuration dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults (in case new keys were added)
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded_config)
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            # First run, create config file with defaults
            config = self.DEFAULT_CONFIG.copy()
            self.save(config)
            return config
    
    def save(self, config: Dict[str, Any] = None):
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save (uses self.config if None)
        """
        if config is not None:
            self.config = config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set configuration value and save
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
        self.save()
    
    def update(self, updates: Dict[str, Any]):
        """
        Update multiple configuration values and save
        
        Args:
            updates: Dictionary of updates
        """
        self.config.update(updates)
        self.save()
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration
        
        Returns:
            Complete configuration dictionary
        """
        return self.config.copy()
    
    def reset(self):
        """Reset configuration to defaults"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()


# Global configuration manager instance
_config_manager: ConfigManager = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def init_config_manager(config_file: str = "config.json") -> ConfigManager:
    """
    Initialize the global configuration manager
    
    Args:
        config_file: Path to configuration file
    
    Returns:
        ConfigManager instance
    """
    global _config_manager
    _config_manager = ConfigManager(config_file)
    return _config_manager
