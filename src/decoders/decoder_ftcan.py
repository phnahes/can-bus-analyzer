"""
FTCAN 2.0 Protocol Decoder

Component responsible for decoding the FuelTech FTCAN 2.0 protocol, as defined in Protocol_FTCAN20_Public_R026.pdf.

ftcan_decoder.py: Implements the core protocol logic, including:
- Extended (29-bit) CAN ID decoding
- Segmented message reassembly
- MEASURE_IDS definitions
- ProductType enumeration
- FTCANDecoder.decode_message() method

This component is application-agnostic and has no external dependencies.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import IntEnum
import struct


class DataFieldID(IntEnum):
    """Data layout types"""
    STANDARD_CAN = 0x00
    STANDARD_CAN_BRIDGE = 0x01
    FTCAN_2_0 = 0x02
    FTCAN_2_0_BRIDGE = 0x03


class ProductType(IntEnum):
    """FuelTech product types"""
    DEVICE_SEARCHING = 0x0FFF
    GEAR_CONTROLLER = 0x0140
    KNOCK_METER = 0x0141
    BOOST_CONTROLLER_2 = 0x0142
    INJECTOR_DRIVER = 0x0150
    INPUT_EXPANDER = 0x023F
    WBO2_NANO = 0x0240
    WBO2_SLIM = 0x0241
    ALCOHOL_O2 = 0x0242
    FTSPARK_A = 0x0243
    SWITCHPAD_8 = 0x0244
    FT500_ECU = 0x0280
    FT600_ECU = 0x0281


# Dictionary of MeasureIDs (DataIDs) - main sensors
MEASURE_IDS = {
    0x0000: {"name": "Unknown", "unit": "", "multiplier": 1.0},
    0x0001: {"name": "TPS", "unit": "%", "multiplier": 0.1},
    0x0002: {"name": "MAP", "unit": "Bar", "multiplier": 0.001},
    0x0003: {"name": "Air Temperature", "unit": "°C", "multiplier": 0.1},
    0x0004: {"name": "Engine Temperature", "unit": "°C", "multiplier": 0.1},
    0x0005: {"name": "Oil Pressure", "unit": "Bar", "multiplier": 0.001},
    0x0006: {"name": "Fuel Pressure", "unit": "Bar", "multiplier": 0.001},
    0x0007: {"name": "Water Pressure", "unit": "Bar", "multiplier": 0.001},
    0x0008: {"name": "ECU Launch Mode", "unit": "", "multiplier": 1.0},
    0x0009: {"name": "ECU Battery Voltage", "unit": "V", "multiplier": 0.01},
    0x000A: {"name": "Traction Speed", "unit": "Km/h", "multiplier": 1.0},
    0x000B: {"name": "Drag Speed", "unit": "Km/h", "multiplier": 1.0},
    0x0011: {"name": "Gear", "unit": "", "multiplier": 1.0},
    0x0012: {"name": "Disabled O2", "unit": "λ", "multiplier": 0.001},
    0x0013: {"name": "Cylinder 1 O2", "unit": "λ", "multiplier": 0.001},
    0x0014: {"name": "Cylinder 2 O2", "unit": "λ", "multiplier": 0.001},
    0x0015: {"name": "Cylinder 3 O2", "unit": "λ", "multiplier": 0.001},
    0x0016: {"name": "Cylinder 4 O2", "unit": "λ", "multiplier": 0.001},
    0x0017: {"name": "Cylinder 5 O2", "unit": "λ", "multiplier": 0.001},
    0x0018: {"name": "Cylinder 6 O2", "unit": "λ", "multiplier": 0.001},
    0x0019: {"name": "Cylinder 7 O2", "unit": "λ", "multiplier": 0.001},
    0x001A: {"name": "Cylinder 8 O2", "unit": "λ", "multiplier": 0.001},
    0x0025: {"name": "Left Bank O2", "unit": "λ", "multiplier": 0.001},
    0x0026: {"name": "Right Bank O2", "unit": "λ", "multiplier": 0.001},
    0x0027: {"name": "Exhaust O2", "unit": "λ", "multiplier": 0.001},
    0x0042: {"name": "ECU RPM", "unit": "RPM", "multiplier": 1.0},
    0x0043: {"name": "ECU Injection Bank A Time", "unit": "ms", "multiplier": 0.01},
    0x0044: {"name": "ECU Injection Bank B Time", "unit": "ms", "multiplier": 0.01},
    0x0045: {"name": "ECU Injection Bank A Duty Cycle", "unit": "%", "multiplier": 0.1},
    0x0046: {"name": "ECU Injection Bank B Duty Cycle", "unit": "%", "multiplier": 0.1},
    0x0047: {"name": "ECU Ignition Advance/Retard", "unit": "°", "multiplier": 0.1},
}


@dataclass
class FTCANIdentification:
    """FTCAN identification (29 bits)"""
    product_id: int  # 15 bits (28-14)
    data_field_id: int  # 3 bits (13-11)
    message_id: int  # 11 bits (10-0)
    
    # Derived fields
    product_type_id: int  # 10 bits (bits 14-5 of ProductID)
    unique_id: int  # 5 bits (bits 4-0 of ProductID)
    is_response: bool  # bit 10 of MessageID
    
    @classmethod
    def from_can_id(cls, can_id: int) -> 'FTCANIdentification':
        """Decode 29-bit CAN ID"""
        product_id = (can_id >> 14) & 0x7FFF  # bits 28-14
        data_field_id = (can_id >> 11) & 0x07  # bits 13-11
        message_id = can_id & 0x7FF  # bits 10-0
        
        # Decode ProductID
        product_type_id = (product_id >> 5) & 0x3FF  # bits 14-5
        unique_id = product_id & 0x1F  # bits 4-0
        
        # Decode MessageID
        is_response = bool((message_id >> 10) & 0x01)
        
        return cls(
            product_id=product_id,
            data_field_id=data_field_id,
            message_id=message_id,
            product_type_id=product_type_id,
            unique_id=unique_id,
            is_response=is_response
        )
    
    def get_product_name(self) -> str:
        """Return product name"""
        try:
            return ProductType(self.product_type_id).name
        except ValueError:
            return f"Unknown_0x{self.product_type_id:03X}"
    
    def get_full_product_name(self) -> str:
        """Return full name with unique ID"""
        return f"{self.get_product_name()} #{self.unique_id}"


@dataclass
class FTCANMeasure:
    """FTCAN measure (4 bytes)"""
    measure_id: int  # 16 bits
    value: int  # 16 bits signed
    
    # Derived fields
    data_id: int  # 15 bits (bits 15-1 of MeasureID)
    is_status: bool  # bit 0 of MeasureID
    
    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> 'FTCANMeasure':
        """Decode 4-byte measure (big-endian)"""
        if len(data) < offset + 4:
            raise ValueError("Insufficient data to decode measure")
        
        # Big-endian: most significant bytes first
        measure_id = struct.unpack('>H', data[offset:offset+2])[0]
        value = struct.unpack('>h', data[offset+2:offset+4])[0]  # signed
        
        data_id = (measure_id >> 1) & 0x7FFF
        is_status = bool(measure_id & 0x01)
        
        return cls(
            measure_id=measure_id,
            value=value,
            data_id=data_id,
            is_status=is_status
        )
    
    def get_real_value(self) -> float:
        """Return real value with multiplier applied"""
        info = MEASURE_IDS.get(self.data_id, {"multiplier": 1.0})
        return self.value * info["multiplier"]
    
    def get_name(self) -> str:
        """Return measure name"""
        info = MEASURE_IDS.get(self.data_id, {"name": f"Unknown_0x{self.data_id:04X}"})
        return info["name"]
    
    def get_unit(self) -> str:
        """Return measure unit"""
        info = MEASURE_IDS.get(self.data_id, {"unit": ""})
        return info["unit"]
    
    def __str__(self) -> str:
        """String representation"""
        real_value = self.get_real_value()
        unit = self.get_unit()
        status_str = " (Status)" if self.is_status else ""
        return f"{self.get_name()}: {real_value:.3f} {unit}{status_str}"


@dataclass
class FTCANSegmentedPacket:
    """FTCAN segmented packet"""
    segment_number: int  # 0x00 to 0xFE
    total_length: Optional[int] = None  # Only in first segment
    payload: bytes = b''
    
    @classmethod
    def from_data_field(cls, data: bytes) -> 'FTCANSegmentedPacket':
        """Decode FTCAN data field"""
        if len(data) == 0:
            raise ValueError("Empty data")
        
        segment_number = data[0]
        
        if segment_number == 0xFF:
            # Single packet
            return cls(
                segment_number=0xFF,
                total_length=None,
                payload=data[1:]
            )
        elif segment_number == 0x00:
            # First segment
            if len(data) < 3:
                raise ValueError("Incomplete first segment")
            
            # Segmentation data (2 bytes, big-endian)
            total_length = struct.unpack('>H', data[1:3])[0] & 0x07FF  # bits 10-0
            payload = data[3:]
            
            return cls(
                segment_number=0,
                total_length=total_length,
                payload=payload
            )
        else:
            # Subsequent segments (0x01 to 0xFE)
            return cls(
                segment_number=segment_number,
                total_length=None,
                payload=data[1:]
            )


class FTCANDecoder:
    """FTCAN 2.0 protocol decoder"""
    
    def __init__(self):
        self.segmented_packets: Dict[int, List[FTCANSegmentedPacket]] = {}
    
    def decode_message(self, can_id: int, data: bytes) -> Dict:
        """
        Decode a complete FTCAN message
        
        Returns:
            Dict with decoded information
        """
        result = {
            'raw_id': can_id,
            'raw_data': data.hex(),
            'identification': None,
            'measures': [],
            'error': None,
            'is_complete': False
        }
        
        try:
            # Decode identification
            ident = FTCANIdentification.from_can_id(can_id)
            result['identification'] = {
                'product_id': f"0x{ident.product_id:04X}",
                'product_name': ident.get_full_product_name(),
                'product_type_id': f"0x{ident.product_type_id:03X}",
                'unique_id': ident.unique_id,
                'data_field_id': ident.data_field_id,
                'data_field_name': DataFieldID(ident.data_field_id).name,
                'message_id': f"0x{ident.message_id:03X}",
                'is_response': ident.is_response
            }
            
            # Decode data based on DataFieldID
            if ident.data_field_id in [DataFieldID.STANDARD_CAN, DataFieldID.STANDARD_CAN_BRIDGE]:
                # Standard CAN: direct payload
                result['payload'] = data.hex()
                result['is_complete'] = True
                
                # Try to decode measures if it's a reading broadcast
                if ident.message_id in [0x0FF, 0x1FF, 0x2FF, 0x3FF]:
                    result['measures'] = self._decode_measures(data)
                
            elif ident.data_field_id in [DataFieldID.FTCAN_2_0, DataFieldID.FTCAN_2_0_BRIDGE]:
                # FTCAN 2.0: may be segmented
                packet = FTCANSegmentedPacket.from_data_field(data)
                
                if packet.segment_number == 0xFF:
                    # Single packet
                    result['payload'] = packet.payload.hex()
                    result['is_complete'] = True
                    
                    # Try to decode measures
                    if ident.message_id in [0x0FF, 0x1FF, 0x2FF, 0x3FF]:
                        result['measures'] = self._decode_measures(packet.payload)
                else:
                    # Segmented packet
                    result['segment_number'] = packet.segment_number
                    result['total_length'] = packet.total_length
                    result['payload'] = packet.payload.hex()
                    
                    # Store segment for reassembly
                    if can_id not in self.segmented_packets:
                        self.segmented_packets[can_id] = []
                    
                    self.segmented_packets[can_id].append(packet)
                    
                    # Check if complete
                    if packet.segment_number == 0 and packet.total_length is not None:
                        # First segment
                        result['is_complete'] = False
                    else:
                        # Try reassembly
                        complete_payload = self._try_reassembly(can_id)
                        if complete_payload:
                            result['payload'] = complete_payload.hex()
                            result['is_complete'] = True
                            result['measures'] = self._decode_measures(complete_payload)
                            # Clear buffer
                            del self.segmented_packets[can_id]
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _decode_measures(self, data: bytes) -> List[Dict]:
        """Decode measures from a payload"""
        measures = []
        offset = 0
        
        while offset + 4 <= len(data):
            try:
                measure = FTCANMeasure.from_bytes(data, offset)
                measures.append({
                    'measure_id': f"0x{measure.measure_id:04X}",
                    'data_id': f"0x{measure.data_id:04X}",
                    'name': measure.get_name(),
                    'raw_value': measure.value,
                    'real_value': measure.get_real_value(),
                    'unit': measure.get_unit(),
                    'is_status': measure.is_status,
                    'formatted': str(measure)
                })
                offset += 4
            except Exception as e:
                break
        
        return measures
    
    def _try_reassembly(self, can_id: int) -> Optional[bytes]:
        """Try to reassemble segmented packets"""
        if can_id not in self.segmented_packets:
            return None
        
        packets = self.segmented_packets[can_id]
        
        # Check if has first segment
        first_packet = next((p for p in packets if p.segment_number == 0), None)
        if not first_packet or first_packet.total_length is None:
            return None
        
        # Sort packets by segment number
        sorted_packets = sorted(packets, key=lambda p: p.segment_number)
        
        # Check if complete
        expected_segments = set(range(len(sorted_packets)))
        actual_segments = set(p.segment_number for p in sorted_packets)
        
        if expected_segments != actual_segments:
            return None  # Missing segments
        
        # Reassemble payload
        payload = b''.join(p.payload for p in sorted_packets)
        
        # Verify size
        if len(payload) == first_packet.total_length:
            return payload
        
        return None
    
    def clear_segmented_buffers(self):
        """Clear segmented packet buffers"""
        self.segmented_packets.clear()
    
    @staticmethod
    def is_ftcan_message(can_id: int) -> bool:
        """Check if it is a valid FTCAN message"""
        # FTCAN uses 29-bit IDs
        if can_id > 0x1FFFFFFF:
            return False
        
        # Extract ProductID
        product_id = (can_id >> 14) & 0x7FFF
        product_type_id = (product_id >> 5) & 0x3FF
        
        # Check if it's a known ProductTypeID
        try:
            ProductType(product_type_id)
            return True
        except ValueError:
            # Check if in reserved ranges
            if 0x0282 <= product_type_id <= 0x02E4:  # ECU range
                return True
            if product_type_id == 0x0FFF:  # Device searching
                return True
            return False
    
    @staticmethod
    def get_expected_baudrate() -> int:
        """Return expected FTCAN baudrate"""
        return 1000000  # 1 Mbps
