"""
Dialogs - Application dialog windows (refactored version)

Re-exports TriggerDialog for backward compatibility.
Other dialogs have been extracted to their own modules:
- settings_dialog, bitfield_viewer_dialog, filter_dialog
- usb_device_dialog, modify_rule_dialog, gateway_dialog
"""

from .trigger_dialog import TriggerDialog

__all__ = ['TriggerDialog']
