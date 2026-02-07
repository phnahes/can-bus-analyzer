"""
Transmit Models - Message transmission and playback
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .can_message import CANMessage


@dataclass
class TransmitMessage:
    """Message configured for transmission"""
    can_id: int
    dlc: int
    data: bytes
    period: int = 0  # ms, 0 = single shot
    comment: str = ""
    is_29bit: bool = False
    is_rtr: bool = False
    tx_mode: str = "off"  # off, on, trigger
    trigger_id: Optional[int] = None
    trigger_data: Optional[bytes] = None
    count: int = 0  # Counter of sent messages
    enabled: bool = False


@dataclass
class TraceRecord:
    """Trace record for playback"""
    messages: List[CANMessage] = field(default_factory=list)
    filename: str = ""
    duration: float = 0.0  # seconds
    
    def get_message_count(self) -> int:
        """Return number of messages"""
        return len(self.messages)
    
    def get_unique_ids(self) -> List[int]:
        """Return list of unique IDs"""
        return list(set(msg.can_id for msg in self.messages))


@dataclass
class BomberConfig:
    """CAN Bomber configuration"""
    mode: str = "id_counter"  # id_counter, id_list, data_counter, data_counter_shift
    id_from: int = 0x000
    id_to: int = 0x7FF
    id_list: List[int] = field(default_factory=list)
    data: bytes = bytes([0x00] * 8)
    data_mask: List[bool] = field(default_factory=lambda: [True] * 8)  # Which bytes to increment
    increment: List[int] = field(default_factory=lambda: [1] * 8)  # Increment per byte
    period: int = 100  # ms
    msg_per_step: int = 1
    channel: int = 1
    is_29bit: bool = False
    crc_mode: str = "none"  # none, toyota, iso_j1850
    crc_byte: int = 7  # Byte where to insert CRC
    running: bool = False
