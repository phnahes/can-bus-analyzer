"""
CAN Message Models - Core CAN message and filter classes
"""

from dataclasses import dataclass

from ..config import DEFAULT_CHANNEL


@dataclass
class CANMessage:
    """Represents a CAN message"""
    timestamp: float
    can_id: int
    dlc: int
    data: bytes
    comment: str = ""
    period: int = 0
    count: int = 0
    channel: int = 1  # CAN channel (1 or 2)
    is_extended: bool = False  # 29-bit ID
    is_rtr: bool = False  # Remote Transmission Request
    source: str = DEFAULT_CHANNEL  # Source bus name (for multi-CAN support)
    gateway_processed: bool = False  # Flag to prevent gateway loops
    gateway_action: str = ""  # Gateway action: "blocked", "modified", "forwarded", ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'can_id': self.can_id,
            'dlc': self.dlc,
            'data': self.data.hex(),
            'comment': self.comment,
            'period': self.period,
            'count': self.count,
            'channel': self.channel,
            'is_extended': self.is_extended,
            'is_rtr': self.is_rtr,
            'source': self.source,
            'gateway_processed': self.gateway_processed,
            'gateway_action': self.gateway_action
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CANMessage':
        """Create instance from dictionary"""
        return cls(
            timestamp=data['timestamp'],
            can_id=data['can_id'],
            dlc=data['dlc'],
            data=bytes.fromhex(data['data']),
            comment=data.get('comment', ''),
            period=data.get('period', 0),
            count=data.get('count', 0),
            channel=data.get('channel', 1),
            is_extended=data.get('is_extended', False),
            is_rtr=data.get('is_rtr', False),
            source=data.get('source', DEFAULT_CHANNEL),
            gateway_processed=data.get('gateway_processed', False),
            gateway_action=data.get('gateway_action', '')
        )
    
    def to_ascii(self) -> str:
        """Convert data to ASCII (printable characters only)"""
        ascii_str = ""
        for byte in self.data:
            if 32 <= byte <= 126:
                ascii_str += chr(byte)
            else:
                ascii_str += "."
        return ascii_str
    
    def to_hex_string(self) -> str:
        """Return data in hexadecimal format with spaces"""
        return " ".join([f"{b:02X}" for b in self.data])
    
    def get_bit(self, byte_index: int, bit_index: int) -> int:
        """Return the value of a specific bit"""
        if byte_index >= len(self.data):
            return 0
        return (self.data[byte_index] >> bit_index) & 1
    
    def get_bits_string(self) -> str:
        """Return bit representation of all bytes"""
        return " ".join([f"{b:08b}" for b in self.data])


@dataclass
class CANFilter:
    """Represents a CAN filter (hardware or software)"""
    filter_id: int
    mask: int
    channel: int = 1
    is_29bit: bool = False
    enabled: bool = False
    
    def matches(self, can_id: int) -> bool:
        """Check if an ID passes the filter"""
        if not self.enabled:
            return True
        return (can_id & self.mask) == (self.filter_id & self.mask)
