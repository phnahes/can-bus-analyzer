"""
Theme utilities - Dark mode detection and adaptive colors
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

# Store the original system palette on first import
_original_system_palette = None


def _save_original_palette():
    """Save the original system palette before any modifications"""
    global _original_system_palette
    if _original_system_palette is None:
        app = QApplication.instance()
        if app:
            _original_system_palette = QPalette(app.palette())


def detect_dark_mode():
    """Detect if system is in dark mode using the original system palette"""
    global _original_system_palette
    
    # Use original palette if available, otherwise current palette
    if _original_system_palette is not None:
        palette = _original_system_palette
    else:
        palette = QApplication.palette()
    
    bg_color = palette.color(QPalette.ColorRole.Window)
    # If background is dark (luminance < 128), we're in dark mode
    return bg_color.lightness() < 128


def should_use_dark_mode(theme_preference='system'):
    """
    Determine if dark mode should be used based on user preference
    
    Args:
        theme_preference: 'system', 'light', or 'dark'
    
    Returns:
        bool: True if dark mode should be used
    """
    if theme_preference == 'dark':
        return True
    elif theme_preference == 'light':
        return False
    else:  # 'system' or default
        return detect_dark_mode()


def get_adaptive_colors(theme_preference='system'):
    """
    Get colors adapted to current theme (light/dark)
    
    Args:
        theme_preference: 'system', 'light', or 'dark'
    
    Returns:
        dict: Color scheme for the selected theme
    """
    is_dark = should_use_dark_mode(theme_preference)
    
    if is_dark:
        return {
            # Table colors
            'highlight': QColor(60, 100, 140),      # Darker blue for dark mode
            'highlight_text': QColor(220, 230, 255), # Light text
            'normal_bg': QColor(45, 45, 48),        # Dark background
            'normal_text': QColor(220, 220, 220),   # Light gray text
            'alt_row': QColor(55, 55, 58),          # Slightly lighter for alternating rows
            
            # UI elements
            'separator': 'color: #666;',
            'notification': 'color: #999; font-style: italic;',
            'info_text': 'color: #999; font-size: 10px;',
            'record_active': 'background-color: #cc3333; color: white;',
            'pause_active': 'background-color: #3333cc; color: white;',
            'send_active': 'background-color: #cc3333; color: white; font-weight: bold;',
            
            # Bit Field Viewer colors (darker, more muted for dark mode)
            'bit_on': '#5a9e6f',   # Muted green for bit=1
            'bit_off': '#c85a5a',  # Muted red for bit=0
            'bit_text': 'white',
        }
    else:
        return {
            # Table colors
            'highlight': QColor(220, 240, 255),     # Light blue for light mode
            'highlight_text': QColor(0, 0, 0),      # Black text
            'normal_bg': QColor(255, 255, 255),     # White background
            'normal_text': QColor(0, 0, 0),         # Black text
            'alt_row': QColor(245, 245, 245),       # Light gray for alternating rows
            
            # UI elements
            'separator': 'color: lightgray;',
            'notification': 'color: #666; font-style: italic;',
            'info_text': 'color: gray; font-size: 10px;',
            'record_active': 'background-color: #ff4444; color: white;',
            'pause_active': 'background-color: #4444ff; color: white;',
            'send_active': 'background-color: #f44336; color: white; font-weight: bold;',
            
            # Bit Field Viewer colors (bright for light mode)
            'bit_on': '#4CAF50',   # Bright green for bit=1
            'bit_off': '#f44336',  # Bright red for bit=0
            'bit_text': 'white',
        }


def get_bit_style(bit_value, colors=None):
    """Get stylesheet for bit display widget"""
    if colors is None:
        colors = get_adaptive_colors()
    
    bg_color = colors['bit_on'] if bit_value else colors['bit_off']
    text_color = colors['bit_text']
    
    return (
        f"background-color: {bg_color}; "
        f"color: {text_color}; font-weight: bold; font-size: 16px; "
        f"padding: 10px; border-radius: 5px;"
    )


def apply_theme_to_app(app: QApplication, theme_preference='system'):
    """
    Apply complete theme to the application including palette
    
    Args:
        app: QApplication instance
        theme_preference: 'system', 'light', or 'dark'
    """
    # Save original palette on first call
    _save_original_palette()
    
    is_dark = should_use_dark_mode(theme_preference)
    
    # Set Fusion style for consistent cross-platform appearance
    app.setStyle('Fusion')
    
    # Always create a custom palette based on detected theme
    palette = QPalette()
        
    if is_dark:
        # Dark theme colors
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        # Disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(80, 80, 80))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(127, 127, 127))
    else:
        # Light theme colors
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        # Disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(120, 120, 120))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(120, 120, 120))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(200, 200, 200))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(120, 120, 120))
    
    app.setPalette(palette)
