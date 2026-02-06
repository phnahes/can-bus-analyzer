"""
FTCAN Protocol Decoder - Plugin adapter for FTCAN 2.0 in the app's decoder manager.

- ftcan_protocol_decoder.py: Implements ProtocolDecoder interface; wraps FTCANDecoder
  and returns DecodedData for the UI/decoder manager. Use this when registering
  the decoder in the application.
"""

from typing import Optional
from ..protocol_decoder import ProtocolDecoder, DecodedData, DecoderPriority
from .ftcan_decoder import FTCANDecoder


class FTCANProtocolDecoder(ProtocolDecoder):
    """Decoder for FuelTech FTCAN 2.0 protocol (app plugin)."""
    
    def __init__(self):
        super().__init__()
        self.priority = DecoderPriority.HIGH
        self.decoder = FTCANDecoder()
    
    def get_name(self) -> str:
        return "FTCAN 2.0"
    
    def get_description(self) -> str:
        return "FuelTech CAN Protocol - ECUs, WB-O2 Nano, Sensors (1 Mbps)"
    
    def can_decode(self, can_id: int, data: bytes, is_extended: bool) -> bool:
        """Check if message is FTCAN"""
        # FTCAN usa IDs de 29 bits
        if not is_extended:
            return False
        
        return FTCANDecoder.is_ftcan_message(can_id)
    
    def decode(self, can_id: int, data: bytes, is_extended: bool, timestamp: float) -> Optional[DecodedData]:
        """Decode FTCAN message."""
        try:
            result = self.decoder.decode_message(can_id, data)
            
            if result.get('error'):
                return DecodedData(
                    protocol="FTCAN 2.0",
                    success=False,
                    confidence=0.0,
                    data={},
                    raw_description=f"Error: {result['error']}"
                )
            
            # Monta descrição
            description_parts = []
            
            if result['identification']:
                ident = result['identification']
                description_parts.append(ident['product_name'])
                
                if result.get('measures'):
                    measure_names = [m['name'] for m in result['measures'][:3]]
                    description_parts.append(f"({len(result['measures'])} measures)")
                    if measure_names:
                        description_parts.append(": " + ", ".join(measure_names))
            
            raw_description = " ".join(description_parts) if description_parts else "FTCAN Message"
            
            # Calcula confiança
            confidence = 1.0 if result.get('is_complete') else 0.5
            
            return DecodedData(
                protocol="FTCAN 2.0",
                success=True,
                confidence=confidence,
                data=result,
                raw_description=raw_description,
                detailed_info=result
            )
            
        except Exception as e:
            return DecodedData(
                protocol="FTCAN 2.0",
                success=False,
                confidence=0.0,
                data={},
                raw_description=f"Decode error: {str(e)}"
            )
    
    def clear_buffers(self):
        """Clear segmented packet buffers."""
        self.decoder.clear_segmented_buffers()
