"""
UI and model default values.

Centralizes default constants used across the application (PID, channel, DLC, etc.)
so they can be changed in one place.
"""

# CAN ID / PID display default (e.g. empty table cell, placeholders)
DEFAULT_CAN_ID_STR = "0x000"

# Default bus/channel name (first bus)
DEFAULT_CHANNEL = "CAN1"

# Second bus name (e.g. gateway default list)
DEFAULT_CHANNEL_SECOND = "CAN2"

# Default DLC when creating or displaying a full message (e.g. Add to Transmit)
DEFAULT_DLC_STR = "8"

# Default DLC when cell is empty (e.g. Bit Field Viewer fallback)
DEFAULT_DLC_STR_EMPTY = "0"

# Default transmit period (ms) for new messages and after Add
DEFAULT_TX_PERIOD_MS = 100

# Default TX Mode for new messages and after Add: "off", "on", or "trigger"
DEFAULT_TX_MODE = "on"

# Default list of bus names for gateway / multi-bus UI
DEFAULT_BUS_NAMES = [DEFAULT_CHANNEL, DEFAULT_CHANNEL_SECOND]
