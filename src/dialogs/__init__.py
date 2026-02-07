"""
Dialogs Package - User interface dialogs for CAN Analyzer

This package contains all dialog windows organized by functionality:
- general: General purpose dialogs (settings, filters, gateway, etc.)
- ftcan: FTCAN 2.0 protocol analyzer dialog
- obd2: OBD-II protocol monitor dialog
- decoder_manager: Protocol decoder management dialog
"""

# General dialogs
from .general import (
    SettingsDialog,
    BitFieldViewerDialog,
    FilterDialog,
    TriggerDialog,
    USBDeviceSelectionDialog,
    ModifyRuleDialog,
    GatewayDialog,
)
from .decoder_manager import DecoderManagerDialog

# Protocol-specific dialogs
from .ftcan import FTCANDialog
from .obd2 import OBD2Dialog

__all__ = [
    # General dialogs
    'SettingsDialog',
    'BitFieldViewerDialog',
    'FilterDialog',
    'TriggerDialog',
    'USBDeviceSelectionDialog',
    'ModifyRuleDialog',
    'GatewayDialog',
    'DecoderManagerDialog',
    
    # Protocol dialogs
    'FTCANDialog',
    'OBD2Dialog',
]
