"""
Models - Classes de dados para CAN Analyzer
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class CANMessage:
    """Representa uma mensagem CAN"""
    timestamp: float
    can_id: int
    dlc: int
    data: bytes
    comment: str = ""
    period: int = 0
    count: int = 0
    channel: int = 1  # Canal CAN (1 ou 2)
    is_extended: bool = False  # ID de 29 bits
    is_rtr: bool = False  # Remote Transmission Request
    
    def to_dict(self) -> dict:
        """Converte para dicionário"""
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
            'is_rtr': self.is_rtr
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CANMessage':
        """Cria instância a partir de dicionário"""
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
            is_rtr=data.get('is_rtr', False)
        )
    
    def to_ascii(self) -> str:
        """Converte dados para ASCII (caracteres imprimíveis apenas)"""
        ascii_str = ""
        for byte in self.data:
            if 32 <= byte <= 126:
                ascii_str += chr(byte)
            else:
                ascii_str += "."
        return ascii_str
    
    def to_hex_string(self) -> str:
        """Retorna dados em formato hexadecimal com espaços"""
        return " ".join([f"{b:02X}" for b in self.data])
    
    def get_bit(self, byte_index: int, bit_index: int) -> int:
        """Retorna o valor de um bit específico"""
        if byte_index >= len(self.data):
            return 0
        return (self.data[byte_index] >> bit_index) & 1
    
    def get_bits_string(self) -> str:
        """Retorna representação em bits de todos os bytes"""
        return " ".join([f"{b:08b}" for b in self.data])


@dataclass
class CANFilter:
    """Representa um filtro CAN (hardware ou software)"""
    filter_id: int
    mask: int
    channel: int = 1
    is_29bit: bool = False
    enabled: bool = False
    
    def matches(self, can_id: int) -> bool:
        """Verifica se um ID passa pelo filtro"""
        if not self.enabled:
            return True
        return (can_id & self.mask) == (self.filter_id & self.mask)


@dataclass
class CANConfig:
    """Configuração do adaptador CAN"""
    channel: str = "can0"
    baudrate: int = 500000
    com_baudrate: str = "115200 bit/s"
    interface: str = "socketcan"
    listen_only: bool = True
    timestamp: bool = True
    rts_hs: bool = False
    baudrate_reg: str = "FFFFFF"
    custom_baudrate: Optional[int] = None
    low_accuracy: bool = False
    
    def get_baudrate_kbps(self) -> int:
        """Retorna baudrate em Kbps"""
        return self.baudrate // 1000


@dataclass
class TransmitMessage:
    """Mensagem configurada para transmissão"""
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
    count: int = 0  # Contador de mensagens enviadas
    enabled: bool = False


@dataclass
class TraceRecord:
    """Registro de trace para playback"""
    messages: List[CANMessage] = field(default_factory=list)
    filename: str = ""
    duration: float = 0.0  # segundos
    
    def get_message_count(self) -> int:
        """Retorna número de mensagens"""
        return len(self.messages)
    
    def get_unique_ids(self) -> List[int]:
        """Retorna lista de IDs únicos"""
        return list(set(msg.can_id for msg in self.messages))


@dataclass
class BomberConfig:
    """Configuração do CAN Bomber"""
    mode: str = "id_counter"  # id_counter, id_list, data_counter, data_counter_shift
    id_from: int = 0x000
    id_to: int = 0x7FF
    id_list: List[int] = field(default_factory=list)
    data: bytes = bytes([0x00] * 8)
    data_mask: List[bool] = field(default_factory=lambda: [True] * 8)  # Quais bytes incrementar
    increment: List[int] = field(default_factory=lambda: [1] * 8)  # Incremento por byte
    period: int = 100  # ms
    msg_per_step: int = 1
    channel: int = 1
    is_29bit: bool = False
    crc_mode: str = "none"  # none, toyota, iso_j1850
    crc_byte: int = 7  # Byte onde inserir CRC
    running: bool = False
