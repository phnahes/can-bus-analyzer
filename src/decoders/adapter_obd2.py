"""
OBD-II Protocol Adapter - Adapter for OBD-II protocol (plugin for modular system)
Wraps OBD2Decoder core implementation
"""

from typing import Optional
from .base import ProtocolDecoder, DecodedData, DecoderPriority
from .decoder_obd2 import OBD2Decoder, OBD2_PIDS


class OBD2ProtocolDecoder(ProtocolDecoder):
    """Decoder for OBD-II protocol (ISO 15765-4) - app plugin"""
    
    def __init__(self):
        super().__init__()
        self.priority = DecoderPriority.NORMAL
        self.decoder = OBD2Decoder()
    
    def get_name(self) -> str:
        return "OBD-II"
    
    def get_description(self) -> str:
        return "On-Board Diagnostics II (ISO 15765-4) - 250/500 kbps"
    
    def can_decode(self, can_id: int, data: bytes, is_extended: bool) -> bool:
        """Check if message is OBD-II"""
        return OBD2Decoder.is_obd2_message(can_id, is_extended)
    
    def decode(self, can_id: int, data: bytes, is_extended: bool, timestamp: float) -> Optional[DecodedData]:
        """Decode OBD-II message"""
        try:
            result = self.decoder.decode_message(can_id, data, is_extended)
            
            if result.get('error'):
                return DecodedData(
                    protocol="OBD-II",
                    success=False,
                    confidence=0.0,
                    data={},
                    raw_description=f"Error: {result['error']}"
                )
            
            # Build description
            description = result.get('description', 'OBD-II Message')
            
            # Calculate confidence
            confidence = 0.9 if result.get('type') in ['request', 'response'] else 0.7
            
            return DecodedData(
                protocol="OBD-II",
                success=True,
                confidence=confidence,
                data=result,
                raw_description=description,
                detailed_info=result
            )
        
        except Exception as e:
            return DecodedData(
                protocol="OBD-II",
                success=False,
                confidence=0.0,
                data={},
                raw_description=f"Decode error: {str(e)}"
            )
