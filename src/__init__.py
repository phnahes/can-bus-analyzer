"""
CAN Analyzer - Main modules
"""

__version__ = "1.2.0"
# Build/release identifier (YYYY.MM); update on release
__build__ = "2026.02"
# Export models from new models package
from .models import (
    CANMessage,
    CANFilter,
    CANConfig,
    TransmitMessage,
    TraceRecord,
    BomberConfig,
    GatewayBlockRule,
    GatewayDynamicBlock,
    GatewayModifyRule,
    GatewayRoute,
    GatewayConfig,
)

__all__ = [
    '__version__',
    '__build__',
    'CANMessage',
    'CANFilter',
    'CANConfig',
    'TransmitMessage',
    'TraceRecord',
    'BomberConfig',
    'GatewayBlockRule',
    'GatewayDynamicBlock',
    'GatewayModifyRule',
    'GatewayRoute',
    'GatewayConfig',
]
