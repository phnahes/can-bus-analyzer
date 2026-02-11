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

from .defaults import (
    DEFAULT_CAN_ID_STR,
    DEFAULT_CHANNEL,
    DEFAULT_CHANNEL_SECOND,
    DEFAULT_DLC_STR,
    DEFAULT_DLC_STR_EMPTY,
    DEFAULT_TX_PERIOD_MS,
    DEFAULT_TX_MODE,
    DEFAULT_BUS_NAMES,
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
    'get_log_level_from_name',
    # Defaults
    'DEFAULT_CAN_ID_STR',
    'DEFAULT_CHANNEL',
    'DEFAULT_CHANNEL_SECOND',
    'DEFAULT_DLC_STR',
    'DEFAULT_DLC_STR_EMPTY',
    'DEFAULT_TX_PERIOD_MS',
    'DEFAULT_TX_MODE',
    'DEFAULT_BUS_NAMES',
]
