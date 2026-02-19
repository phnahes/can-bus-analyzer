"""
Keyboard Shortcuts Configuration

Centralizes all keyboard shortcuts for the CAN Analyzer application.
Automatically detects platform (macOS/Windows/Linux) and applies appropriate modifiers.
"""

import sys
from typing import Dict


def get_modifier_key() -> str:
    """
    Get the modifier key string for QKeySequence.
    Use 'Ctrl' for all platforms: on macOS Qt maps Ctrl to Command (⌘),
    so shortcuts show and work as Command+key. On Windows/Linux, Ctrl is Control.
    """
    # Qt convention: "Ctrl" in QKeySequence = Command on macOS, Control on Windows/Linux
    return 'Ctrl'


def get_shortcuts() -> Dict[str, str]:
    """
    Get all keyboard shortcuts for the application.
    
    Returns:
        Dict[str, str]: Dictionary mapping action names to keyboard shortcuts
    """
    mod = get_modifier_key()
    
    return {
        # File Menu
        'connect': f'{mod}+C',                   # Connect
        'disconnect': f'{mod}+C',                 # Disconnect (same key, toggles state)
        'reset': f'{mod}+R',                     # Reset
        'save_monitor': f'{mod}+Shift+M',        # Save Monitor Log
        'load_monitor': f'{mod}+Alt+Shift+M',   # Load Monitor Log
        'save_tracer': f'{mod}+Shift+T',        # Save Tracer Log
        'load_tracer': f'{mod}+Alt+Shift+T',    # Load Tracer Log
        'save_transmit': f'{mod}+Shift+S',      # Save Transmit List
        'load_transmit': f'{mod}+Alt+Shift+S',  # Load Transmit List
        'exit': f'{mod}+Q',                     # Exit
        # View Menu
        'tracer_mode': f'{mod}+T',              # Toggle Tracer/Monitor Mode
        'split_screen': f'{mod}+S',             # Toggle Split Screen
        'toggle_transmit': f'{mod}+Shift+P',    # Show/Hide Transmit Panel (avoid conflict with Save Tracer)
        # Tools Menu
        'filters': f'{mod}+F',                  # Open Filters
        'gateway': f'{mod}+G',                  # Gateway Configuration
        'triggers': f'{mod}+Shift+R',           # Trigger Configuration (Shift+R to avoid conflict with Reset)
        'diff_mode': f'{mod}+D',                # Diff Mode Settings
        # Decoders Menu
        'decoder_manager': f'{mod}+Shift+D',
        'ftcan_analyzer': f'{mod}+1',
        'obd2_monitor': f'{mod}+2',
        'bap_analyzer': f'{mod}+3',
        # Settings Menu
        'settings': f'{mod}+,',
    }


def get_shortcut_descriptions() -> Dict[str, str]:
    """
    Get human-readable descriptions for all shortcuts.
    
    Returns:
        Dict[str, str]: Dictionary mapping action names to descriptions
    """
    return {
        # File Menu
        'connect': 'Connect',
        'disconnect': 'Disconnect',
        'reset': 'Reset',
        'save_monitor': 'Save Monitor Log',
        'load_monitor': 'Load Monitor Log',
        'save_tracer': 'Save Tracer Log',
        'load_tracer': 'Load Tracer Log',
        'save_transmit': 'Save Transmit List',
        'load_transmit': 'Load Transmit List',
        'exit': 'Exit',
        # View Menu
        'tracer_mode': 'Toggle Tracer/Monitor Mode',
        'split_screen': 'Toggle Split Screen',
        'toggle_transmit': 'Show/Hide Transmit Panel',
        # Tools Menu
        'filters': 'Open Filters',
        'triggers': 'Trigger Configuration',
        'gateway': 'Gateway Configuration',
        'diff_mode': 'Diff Mode Settings',
        # Decoders Menu
        'decoder_manager': 'Manage Protocol Decoders',
        'ftcan_analyzer': 'Open FTCAN 2.0 Protocol Analyzer',
        'obd2_monitor': 'Open OBD-II Monitor',
        'bap_analyzer': 'Open VAG BAP Analyzer',
        # Settings Menu
        'settings': 'Open Settings dialog',
    }


def format_shortcut_for_display(shortcut: str) -> str:
    """
    Format a shortcut string for display in UI.
    
    Args:
        shortcut: Shortcut string (e.g., 'Cmd+S' or 'Ctrl+S')
    
    Returns:
        str: Formatted shortcut for display
    """
    # On macOS we use 'Ctrl' in QKeySequence (Qt maps it to Command), so show ⌘
    if sys.platform == 'darwin':
        shortcut = shortcut.replace('Ctrl', '⌘')
        shortcut = shortcut.replace('Alt', '⌥')
        shortcut = shortcut.replace('Shift', '⇧')
    else:
        shortcut = shortcut.replace('Ctrl', '⌃')
        shortcut = shortcut.replace('Alt', '⌥')
        shortcut = shortcut.replace('Shift', '⇧')
    
    return shortcut


# Convenience function to get a single shortcut
def get_shortcut(action: str) -> str:
    """
    Get a specific shortcut by action name.
    
    Args:
        action: Action name (e.g., 'connect', 'save_tracer')
    
    Returns:
        str: Keyboard shortcut string
    """
    shortcuts = get_shortcuts()
    return shortcuts.get(action, '')


# Export for easy access
__all__ = [
    'get_shortcuts',
    'get_shortcut',
    'get_shortcut_descriptions',
    'get_modifier_key',
    'format_shortcut_for_display'
]
