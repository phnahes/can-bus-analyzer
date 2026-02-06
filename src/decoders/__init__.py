"""
Protocol Decoders Package

This package contains protocol-specific decoders for the CAN Analyzer.
Each protocol has two main components:
- Core decoder (*_decoder.py): Pure decoding logic
- Protocol adapter (*_protocol_decoder.py): Integration with the app

Available Protocols:
- FTCAN 2.0 (FuelTech proprietary protocol)
- OBD-II (ISO 15765-4 / SAE J1979)
"""

# FTCAN 2.0
from .ftcan_decoder import FTCANDecoder, MEASURE_IDS as FTCAN_MEASURE_IDS
from .ftcan_protocol_decoder import FTCANProtocolDecoder

# OBD-II
from .obd2_decoder import OBD2Decoder, OBD2_PIDS
from .obd2_protocol_decoder import OBD2ProtocolDecoder

__all__ = [
    # FTCAN
    'FTCANDecoder',
    'FTCAN_MEASURE_IDS',
    'FTCANProtocolDecoder',
    
    # OBD-II
    'OBD2Decoder',
    'OBD2_PIDS',
    'OBD2ProtocolDecoder',
]
