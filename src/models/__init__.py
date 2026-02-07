"""
Models Package - Data models for CAN Analyzer

This package contains all data models organized by domain:
- can_message: Core CAN message and filter classes
- config: CAN bus and application configuration
- transmit: Message transmission and playback
- gateway: Gateway routing and modification rules
"""

# CAN Message and Filter
from .can_message import CANMessage, CANFilter

# Configuration
from .config import CANConfig

# Transmit and Playback
from .transmit import TransmitMessage, TraceRecord, BomberConfig

# Gateway
from .gateway import (
    GatewayBlockRule,
    GatewayDynamicBlock,
    GatewayModifyRule,
    GatewayRoute,
    GatewayConfig
)

__all__ = [
    # CAN Message
    'CANMessage',
    'CANFilter',
    
    # Configuration
    'CANConfig',
    
    # Transmit
    'TransmitMessage',
    'TraceRecord',
    'BomberConfig',
    
    # Gateway
    'GatewayBlockRule',
    'GatewayDynamicBlock',
    'GatewayModifyRule',
    'GatewayRoute',
    'GatewayConfig',
]
