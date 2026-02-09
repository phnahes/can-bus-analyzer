"""
Configuration Models - CAN bus and application configuration
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CANConfig:
    """CAN adapter configuration"""
    channel: str = "can0"
    baudrate: int = 500000
    com_baudrate: str = "115200 bit/s"
    interface: str = "socketcan"
    listen_only: bool = True
    rts_hs: bool = False
    baudrate_reg: str = "FFFFFF"
    custom_baudrate: Optional[int] = None
    low_accuracy: bool = False
    
    def get_baudrate_kbps(self) -> int:
        """Return baudrate in Kbps"""
        return self.baudrate // 1000
