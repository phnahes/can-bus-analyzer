"""
Gateway Models - CAN Gateway configuration and rules
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .can_message import CANMessage


@dataclass
class GatewayBlockRule:
    """Message blocking rule in Gateway"""
    can_id: int
    channel: str  # Channel name (CAN1, CAN2, etc.)
    enabled: bool = True
    
    def matches(self, msg_id: int, msg_channel: str) -> bool:
        """Check if message should be blocked"""
        return self.enabled and self.can_id == msg_id and self.channel == msg_channel


@dataclass
class GatewayDynamicBlock:
    """Dynamic ID blocking (with increment)"""
    id_from: int
    id_to: int
    channel: str
    period: int = 1000  # ms - blocking time per ID
    enabled: bool = False
    current_id: int = 0
    
    def __post_init__(self):
        self.current_id = self.id_from
    
    def get_current_blocked_id(self) -> int:
        """Return currently blocked ID"""
        return self.current_id
    
    def advance(self):
        """Advance to next ID"""
        self.current_id += 1
        if self.current_id > self.id_to:
            self.current_id = self.id_from


@dataclass
class GatewayModifyRule:
    """Rule to modify messages in Gateway"""
    can_id: int
    channel: str
    enabled: bool = True
    # Possible modifications
    new_id: Optional[int] = None  # New ID (if None, keep original)
    data_mask: List[bool] = field(default_factory=lambda: [False] * 8)  # Which bytes to modify
    new_data: bytes = bytes([0x00] * 8)  # New values for marked bytes
    
    def apply(self, msg: CANMessage) -> CANMessage:
        """Apply modifications to message"""
        if not self.enabled:
            return msg
        
        # Create message copy
        modified_data = bytearray(msg.data)
        
        # Apply data modifications
        for i, should_modify in enumerate(self.data_mask):
            if should_modify and i < len(modified_data):
                modified_data[i] = self.new_data[i]
        
        # Create new message with modifications
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
    """Gateway forwarding route"""
    source: str  # Source channel (e.g., "CAN1")
    destination: str  # Destination channel (e.g., "CAN2")
    enabled: bool = True


@dataclass
class GatewayConfig:
    """Complete CAN Gateway configuration"""
    # New route structure (supports multiple routes)
    routes: List[GatewayRoute] = field(default_factory=list)
    
    # Kept for backward compatibility
    transmit_1_to_2: bool = False  # CAN1 → CAN2
    transmit_2_to_1: bool = False  # CAN2 → CAN1
    
    # Static blocking rules
    block_rules: List[GatewayBlockRule] = field(default_factory=list)
    
    # Dynamic blocking
    dynamic_blocks: List[GatewayDynamicBlock] = field(default_factory=list)
    
    # Modification rules
    modify_rules: List[GatewayModifyRule] = field(default_factory=list)
    
    # State
    enabled: bool = False
    
    def get_destination_for_source(self, source: str) -> Optional[str]:
        """Return destination for a specific source, if enabled"""
        for route in self.routes:
            if route.enabled and route.source == source:
                return route.destination
        return None
    
    def has_route_from(self, source: str) -> bool:
        """Check if there's an active route for the source"""
        return any(r.enabled and r.source == source for r in self.routes)
    
    def should_block(self, msg: CANMessage) -> bool:
        """Check if message should be blocked"""
        # Check static blocks
        for rule in self.block_rules:
            if rule.matches(msg.can_id, msg.source):
                return True
        
        # Check dynamic blocks
        for dyn_block in self.dynamic_blocks:
            if dyn_block.enabled and dyn_block.channel == msg.source:
                if msg.can_id == dyn_block.get_current_blocked_id():
                    return True
        
        return False
    
    def get_modify_rule(self, msg: CANMessage) -> Optional[GatewayModifyRule]:
        """Return modification rule for message, if exists"""
        for rule in self.modify_rules:
            if rule.enabled and rule.can_id == msg.can_id and rule.channel == msg.source:
                return rule
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
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
        """Create instance from dictionary"""
        config = cls(
            transmit_1_to_2=data.get('transmit_1_to_2', False),
            transmit_2_to_1=data.get('transmit_2_to_1', False),
            enabled=data.get('enabled', False)
        )
        
        # Load routes (new format)
        for route_data in data.get('routes', []):
            config.routes.append(GatewayRoute(
                source=route_data['source'],
                destination=route_data['destination'],
                enabled=route_data.get('enabled', True)
            ))
        
        # Load blocking rules
        for rule_data in data.get('block_rules', []):
            config.block_rules.append(GatewayBlockRule(
                can_id=rule_data['can_id'],
                channel=rule_data['channel'],
                enabled=rule_data.get('enabled', True)
            ))
        
        # Load dynamic blocks
        for dyn_data in data.get('dynamic_blocks', []):
            config.dynamic_blocks.append(GatewayDynamicBlock(
                id_from=dyn_data['id_from'],
                id_to=dyn_data['id_to'],
                channel=dyn_data['channel'],
                period=dyn_data.get('period', 1000),
                enabled=dyn_data.get('enabled', False)
            ))
        
        # Load modification rules
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
