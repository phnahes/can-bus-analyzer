"""
gs_usb / candleLight discovery.

Adapters running candleLight, CANnectivity or CANable 2.x firmware speak the
``gs_usb`` protocol.  On Linux the kernel driver exposes them as SocketCAN
interfaces; on macOS and Windows there is no such driver, so the application
talks to them directly through python-can's ``candle`` backend
(``python-can-candle``), which also supports CAN FD and multi-channel devices.

Everything here is optional: when ``python-can-candle`` is not installed (or
no adapter is plugged in) the helpers return empty results and the rest of the
application keeps working exactly as before.
"""

import re
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional

# python-can-candle channels look like "2088339B413250013:0" (serial:index).
CANDLE_CHANNEL_RE = re.compile(r"^[0-9A-Za-z._-]+:\d+$")


@dataclass(frozen=True)
class CandleChannel:
    """One channel exposed by a gs_usb adapter."""

    channel: str  # "serial:index", the value stored in the config
    serial: str
    index: int
    product: str = ""
    manufacturer: str = ""
    channel_count: int = 1
    software_version: int = 0
    hardware_version: int = 0

    @property
    def label(self) -> str:
        name = self.product or "gs_usb adapter"
        return f"{name} ch{self.index}"

    @property
    def description(self) -> str:
        parts = ["gs_usb"]
        if self.manufacturer:
            parts.append(self.manufacturer)
        if self.channel_count > 1:
            parts.append(f"{self.channel_count} channels")
        if self.software_version:
            parts.append(f"FW {format_version(self.software_version)}")
        return " · ".join(parts)


def format_version(value: int) -> str:
    """candleLight packs the firmware version as major.minor.patch."""
    if not value:
        return ""
    return f"{(value >> 16) & 0xFF}.{(value >> 8) & 0xFF}.{value & 0xFF}"


def candle_available() -> bool:
    """True when python-can-candle (and its native module) can be imported."""
    try:
        import candle_api  # noqa: F401
        return True
    except Exception:
        return False


def _default_lister() -> Iterable:
    import candle_api
    return candle_api.list_device()


def list_channels(lister: Optional[Callable] = None) -> List[CandleChannel]:
    """List every channel of every connected gs_usb adapter.

    ``lister`` is injectable so tests never touch USB hardware.  Failures are
    swallowed on purpose: a broken adapter or missing libusb must not break
    device scanning for the other backends.
    """
    lister = lister or _default_lister

    try:
        devices = lister()
    except Exception:
        return []

    channels: List[CandleChannel] = []
    for device in devices or []:
        try:
            serial = str(device.serial_number)
            count = int(getattr(device, "channel_count", 1) or 0)
            if count < 1:
                count = 1
            for index in range(count):
                channels.append(
                    CandleChannel(
                        channel=f"{serial}:{index}",
                        serial=serial,
                        index=index,
                        product=str(getattr(device, "product", "") or ""),
                        manufacturer=str(getattr(device, "manufacturer", "") or ""),
                        channel_count=count,
                        software_version=int(getattr(device, "software_version", 0) or 0),
                        hardware_version=int(getattr(device, "hardware_version", 0) or 0),
                    )
                )
        except Exception:
            # One malformed device must not hide the others.
            continue

    return channels


def find_channel(channel: str, lister: Optional[Callable] = None) -> Optional[CandleChannel]:
    """Return the channel info when ``channel`` is currently available."""
    wanted = str(channel)
    for candidate in list_channels(lister):
        if candidate.channel == wanted:
            return candidate
    return None


def is_candle_channel(channel) -> bool:
    """True when the value looks like a python-can-candle channel name."""
    return bool(CANDLE_CHANNEL_RE.match(str(channel)))
