"""
Configuration module for CAN Analyzer
"""

from .shortcuts import (
    get_shortcuts,
    get_shortcut,
    get_shortcut_descriptions,
    get_modifier_key,
    format_shortcut_for_display
)

from .logger_config import (
    LoggerConfig,
    LOG_LEVELS,
    get_log_level_name,
    get_log_level_from_name
)

__all__ = [
    # Shortcuts
    'get_shortcuts',
    'get_shortcut',
    'get_shortcut_descriptions',
    'get_modifier_key',
    'format_shortcut_for_display',
    
    # Logger
    'LoggerConfig',
    'LOG_LEVELS',
    'get_log_level_name',
    'get_log_level_from_name'
]
