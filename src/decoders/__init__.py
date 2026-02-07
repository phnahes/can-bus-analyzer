"""
Protocol Decoders Package

This package contains protocol-specific decoders for the CAN Analyzer.
Each protocol has two main components:
- Core decoder (decoder_*.py): Pure decoding logic
- Protocol adapter (adapter_*.py): Integration with the app

Available Protocols:
- FTCAN 2.0 (FuelTech proprietary protocol)
- OBD-II (ISO 15765-4 / SAE J1979)
"""

# Base classes
from .base import (
    ProtocolDecoder,
    DecodedData,
    DecoderPriority,
    get_decoder_manager
)

# FTCAN 2.0
from .decoder_ftcan import FTCANDecoder, MEASURE_IDS as FTCAN_MEASURE_IDS
from .adapter_ftcan import FTCANProtocolDecoder

# OBD-II
from .decoder_obd2 import OBD2Decoder, OBD2_PIDS
from .adapter_obd2 import OBD2ProtocolDecoder

__all__ = [
    # Base classes
    'ProtocolDecoder',
    'DecodedData',
    'DecoderPriority',
    'get_decoder_manager',
    
    # FTCAN
    'FTCANDecoder',
    'FTCAN_MEASURE_IDS',
    'FTCANProtocolDecoder',
    
    # OBD-II
    'OBD2Decoder',
    'OBD2_PIDS',
    'OBD2ProtocolDecoder',
]
