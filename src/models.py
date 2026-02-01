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
    source: str = "CAN1"  # Source bus name (for multi-CAN support)
    
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
            'is_rtr': self.is_rtr,
            'source': self.source
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
            is_rtr=data.get('is_rtr', False),
            source=data.get('source', 'CAN1')
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


@dataclass
class GatewayBlockRule:
    """Regra de bloqueio de mensagens no Gateway"""
    can_id: int
    channel: str  # Nome do canal (CAN1, CAN2, etc.)
    enabled: bool = True
    
    def matches(self, msg_id: int, msg_channel: str) -> bool:
        """Verifica se a mensagem deve ser bloqueada"""
        return self.enabled and self.can_id == msg_id and self.channel == msg_channel


@dataclass
class GatewayDynamicBlock:
    """Bloqueio dinâmico de IDs (com incremento)"""
    id_from: int
    id_to: int
    channel: str
    period: int = 1000  # ms - tempo de bloqueio por ID
    enabled: bool = False
    current_id: int = 0
    
    def __post_init__(self):
        self.current_id = self.id_from
    
    def get_current_blocked_id(self) -> int:
        """Retorna o ID atualmente bloqueado"""
        return self.current_id
    
    def advance(self):
        """Avança para o próximo ID"""
        self.current_id += 1
        if self.current_id > self.id_to:
            self.current_id = self.id_from


@dataclass
class GatewayModifyRule:
    """Regra para modificar mensagens no Gateway"""
    can_id: int
    channel: str
    enabled: bool = True
    # Modificações possíveis
    new_id: Optional[int] = None  # Novo ID (se None, mantém original)
    data_mask: List[bool] = field(default_factory=lambda: [False] * 8)  # Quais bytes modificar
    new_data: bytes = bytes([0x00] * 8)  # Novos valores para os bytes marcados
    
    def apply(self, msg: CANMessage) -> CANMessage:
        """Aplica modificações na mensagem"""
        if not self.enabled:
            return msg
        
        # Cria cópia da mensagem
        modified_data = bytearray(msg.data)
        
        # Aplica modificações de dados
        for i, should_modify in enumerate(self.data_mask):
            if should_modify and i < len(modified_data):
                modified_data[i] = self.new_data[i]
        
        # Cria nova mensagem com modificações
        return CANMessage(
            timestamp=msg.timestamp,
            can_id=self.new_id if self.new_id is not None else msg.can_id,
            dlc=msg.dlc,
            data=bytes(modified_data),
            comment=msg.comment,
            period=msg.period,
            count=msg.count,
            channel=msg.channel,
            is_extended=msg.is_extended,
            is_rtr=msg.is_rtr,
            source=msg.source
        )


@dataclass
class GatewayRoute:
    """Rota de encaminhamento do Gateway"""
    source: str  # Canal de origem (ex: "CAN1")
    destination: str  # Canal de destino (ex: "CAN2")
    enabled: bool = True


@dataclass
class GatewayConfig:
    """Configuração completa do CAN Gateway"""
    # Nova estrutura de rotas (suporta múltiplas rotas)
    routes: List[GatewayRoute] = field(default_factory=list)
    
    # Mantido para compatibilidade com versões antigas
    transmit_1_to_2: bool = False  # CAN1 → CAN2
    transmit_2_to_1: bool = False  # CAN2 → CAN1
    
    # Regras de bloqueio estático
    block_rules: List[GatewayBlockRule] = field(default_factory=list)
    
    # Bloqueio dinâmico
    dynamic_blocks: List[GatewayDynamicBlock] = field(default_factory=list)
    
    # Regras de modificação
    modify_rules: List[GatewayModifyRule] = field(default_factory=list)
    
    # Estado
    enabled: bool = False
    
    def get_destination_for_source(self, source: str) -> Optional[str]:
        """Retorna o destino para uma origem específica, se habilitado"""
        for route in self.routes:
            if route.enabled and route.source == source:
                return route.destination
        return None
    
    def has_route_from(self, source: str) -> bool:
        """Verifica se existe rota ativa para a origem"""
        return any(r.enabled and r.source == source for r in self.routes)
    
    def should_block(self, msg: CANMessage) -> bool:
        """Verifica se a mensagem deve ser bloqueada"""
        # Verifica bloqueios estáticos
        for rule in self.block_rules:
            if rule.matches(msg.can_id, msg.source):
                return True
        
        # Verifica bloqueios dinâmicos
        for dyn_block in self.dynamic_blocks:
            if dyn_block.enabled and dyn_block.channel == msg.source:
                if msg.can_id == dyn_block.get_current_blocked_id():
                    return True
        
        return False
    
    def get_modify_rule(self, msg: CANMessage) -> Optional[GatewayModifyRule]:
        """Retorna regra de modificação para a mensagem, se existir"""
        for rule in self.modify_rules:
            if rule.enabled and rule.can_id == msg.can_id and rule.channel == msg.source:
                return rule
        return None
    
    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            'routes': [
                {'source': r.source, 'destination': r.destination, 'enabled': r.enabled}
                for r in self.routes
            ],
            'transmit_1_to_2': self.transmit_1_to_2,
            'transmit_2_to_1': self.transmit_2_to_1,
            'enabled': self.enabled,
            'block_rules': [
                {'can_id': r.can_id, 'channel': r.channel, 'enabled': r.enabled}
                for r in self.block_rules
            ],
            'dynamic_blocks': [
                {
                    'id_from': d.id_from,
                    'id_to': d.id_to,
                    'channel': d.channel,
                    'period': d.period,
                    'enabled': d.enabled
                }
                for d in self.dynamic_blocks
            ],
            'modify_rules': [
                {
                    'can_id': r.can_id,
                    'channel': r.channel,
                    'enabled': r.enabled,
                    'new_id': r.new_id,
                    'data_mask': r.data_mask,
                    'new_data': r.new_data.hex()
                }
                for r in self.modify_rules
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GatewayConfig':
        """Cria instância a partir de dicionário"""
        config = cls(
            transmit_1_to_2=data.get('transmit_1_to_2', False),
            transmit_2_to_1=data.get('transmit_2_to_1', False),
            enabled=data.get('enabled', False)
        )
        
        # Carrega rotas (novo formato)
        for route_data in data.get('routes', []):
            config.routes.append(GatewayRoute(
                source=route_data['source'],
                destination=route_data['destination'],
                enabled=route_data.get('enabled', True)
            ))
        
        # Carrega regras de bloqueio
        for rule_data in data.get('block_rules', []):
            config.block_rules.append(GatewayBlockRule(
                can_id=rule_data['can_id'],
                channel=rule_data['channel'],
                enabled=rule_data.get('enabled', True)
            ))
        
        # Carrega bloqueios dinâmicos
        for dyn_data in data.get('dynamic_blocks', []):
            config.dynamic_blocks.append(GatewayDynamicBlock(
                id_from=dyn_data['id_from'],
                id_to=dyn_data['id_to'],
                channel=dyn_data['channel'],
                period=dyn_data.get('period', 1000),
                enabled=dyn_data.get('enabled', False)
            ))
        
        # Carrega regras de modificação
        for mod_data in data.get('modify_rules', []):
            config.modify_rules.append(GatewayModifyRule(
                can_id=mod_data['can_id'],
                channel=mod_data['channel'],
                enabled=mod_data.get('enabled', True),
                new_id=mod_data.get('new_id'),
                data_mask=mod_data.get('data_mask', [False] * 8),
                new_data=bytes.fromhex(mod_data.get('new_data', '0000000000000000'))
            ))
        
        return config
