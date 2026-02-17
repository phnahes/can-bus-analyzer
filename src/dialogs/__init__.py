"""
Dialogs Package - User interface dialogs for CAN Analyzer

This package contains all dialog windows organized by functionality:
- settings_dialog: Connection settings
- bitfield_viewer_dialog: Bit field visualization
- filter_dialog: Message filters
- diff_dialog: Diff mode configuration
- usb_device_dialog: USB/Serial device selection
- modify_rule_dialog: Gateway modify rules
- gateway_dialog: CAN gateway configuration
- trigger_dialog: Trigger-based transmission
- ftcan: FTCAN 2.0 protocol analyzer dialog
- obd2: OBD-II protocol monitor dialog
- decoder_manager: Protocol decoder management dialog
"""

# General dialogs (from dedicated modules)
from .settings_dialog import SettingsDialog
from .bitfield_viewer_dialog import BitFieldViewerDialog
from .filter_dialog import FilterDialog
from .diff_dialog import DiffDialog
from .trigger_dialog import TriggerDialog
from .usb_device_dialog import USBDeviceSelectionDialog
from .modify_rule_dialog import ModifyRuleDialog
from .gateway_dialog import GatewayDialog
from .decoder_manager import DecoderManagerDialog

# Protocol-specific dialogs
from .ftcan import FTCANDialog
from .obd2 import OBD2Dialog

__all__ = [
    # General dialogs
    'SettingsDialog',
    'BitFieldViewerDialog',
    'FilterDialog',
    'DiffDialog',
    'TriggerDialog',
    'USBDeviceSelectionDialog',
    'ModifyRuleDialog',
    'GatewayDialog',
    'DecoderManagerDialog',
    
    # Protocol dialogs
    'FTCANDialog',
    'OBD2Dialog',
]
