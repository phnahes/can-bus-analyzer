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
    SWITCHPAD = 0x0244  # Generic SwitchPanel
    FT500_ECU = 0x0280
    FT600_ECU = 0x0281
    EGT_8_MODEL_A = 0x0800
    EGT_8_MODEL_B = 0x0880


# SwitchPanel variants by UniqueID
SWITCHPAD_VARIANTS = {
    0x00: "SwitchPanel Big 8-button",
    0x01: "SwitchPanel Mini 4-button", 
    0x02: "SwitchPanel Mini 5-button",
    0x03: "SwitchPanel Mini 8-button"
}


# ECU Broadcast Priorities (MessageIDs)
BROADCAST_CRITICAL = 0x0FF
BROADCAST_HIGH = 0x1FF
BROADCAST_MEDIUM = 0x2FF
BROADCAST_LOW = 0x3FF

BROADCAST_PRIORITIES = {
    BROADCAST_CRITICAL: "Critical",
    BROADCAST_HIGH: "High",
    BROADCAST_MEDIUM: "Medium",
    BROADCAST_LOW: "Low"
}

# Special MessageIDs for specific devices
SPECIAL_MESSAGE_IDS = {
    # SwitchPanel
    0x320: {"device": "SwitchPanel", "type": "Button States TX"},
    0x321: {"device": "SwitchPanel", "type": "LED Control RX"},
    # EGT-8
    0x080: {"device": "EGT-8", "type": "Channels 1-4"},
    0x100: {"device": "EGT-8", "type": "Channels 5-8"},
    # Version Info
    0x7FE: {"device": "Any", "type": "Version Request"},
    0x7FF: {"device": "Any", "type": "Version Response"},
}

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
    # SwitchPanel custom MeasureIDs
    0xF000: {"name": "SwitchPanel Button 1 State", "unit": "", "multiplier": 1.0},
    0xF001: {"name": "SwitchPanel Button 2 State", "unit": "", "multiplier": 1.0},
    0xF002: {"name": "SwitchPanel Button 3 State", "unit": "", "multiplier": 1.0},
    0xF003: {"name": "SwitchPanel Button 4 State", "unit": "", "multiplier": 1.0},
    0xF004: {"name": "SwitchPanel Button 5 State", "unit": "", "multiplier": 1.0},
    0xF005: {"name": "SwitchPanel Button 6 State", "unit": "", "multiplier": 1.0},
    0xF006: {"name": "SwitchPanel Button 7 State", "unit": "", "multiplier": 1.0},
    0xF007: {"name": "SwitchPanel Button 8 State", "unit": "", "multiplier": 1.0},
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
            product_name = ProductType(self.product_type_id).name
            
            # Handle SwitchPanel variants
            if self.product_type_id == ProductType.SWITCHPAD:
                variant = SWITCHPAD_VARIANTS.get(self.unique_id)
                if variant:
                    return variant
            
            return product_name
        except ValueError:
            return f"Unknown_0x{self.product_type_id:03X}"
    
    def get_full_product_name(self) -> str:
        """Return full name with unique ID"""
        # For SwitchPanel, variant name already includes details
        if self.product_type_id == ProductType.SWITCHPAD:
            variant = SWITCHPAD_VARIANTS.get(self.unique_id)
            if variant:
                return f"{variant} #{self.unique_id}"
        
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


def decode_switchpanel_buttons(data: bytes) -> Dict:
    """
    Decode SwitchPanel button states (MessageID 0x320)
    
    Data format (8 bytes):
    [0] State 1st row (bits for buttons 1-4)
    [1] State 2nd row (bits for buttons 5-8)
    [2] Dimming 1st row
    [3] State 2nd row (duplicate)
    [4] Dimming 2nd row
    [5] Row 1 button states
    [6] Row 2 button states
    [7] Reserved
    """
    if len(data) < 8:
        return {"error": "Insufficient data for button states"}
    
    result = {
        "row1_state": data[0],
        "row2_state": data[1],
        "row1_dimming": data[2],
        "row2_dimming": data[4],
        "buttons": {}
    }
    
    # Decode individual buttons (row 1: buttons 1-4)
    for i in range(4):
        button_num = i + 1
        pressed = bool(data[0] & (1 << i))
        result["buttons"][f"button_{button_num}"] = {
            "pressed": pressed,
            "row": 1,
            "position": i + 1
        }
    
    # Decode row 2 buttons (buttons 5-8)
    for i in range(4):
        button_num = i + 5
        pressed = bool(data[1] & (1 << i))
        result["buttons"][f"button_{button_num}"] = {
            "pressed": pressed,
            "row": 2,
            "position": i + 1
        }
    
    return result


def decode_switchpanel_light(data: bytes) -> Dict:
    """
    Decode SwitchPanel LED control (MessageID 0x321)
    
    Data format (8 bytes):
    [0] State 1st row
    [1] Dimming 1st row
    [2] State 2nd row
    [3] Dimming 2nd row
    [4] Red color button 1st row
    [5] Green color button 1st row
    [6] Blue color button 1st row
    [7] Red color button 2nd row (continues...)
    """
    if len(data) < 8:
        return {"error": "Insufficient data for light control"}
    
    result = {
        "row1_state": data[0],
        "row1_dimming": data[1],
        "row2_state": data[2],
        "row2_dimming": data[3],
        "leds": {}
    }
    
    # RGB values start at byte 4
    # Each button has 3 bytes (R, G, B)
    rgb_offset = 4
    for button_num in range(1, 9):  # 8 buttons max
        if rgb_offset + 2 < len(data):
            result["leds"][f"button_{button_num}"] = {
                "red": data[rgb_offset] if rgb_offset < len(data) else 0,
                "green": data[rgb_offset + 1] if rgb_offset + 1 < len(data) else 0,
                "blue": data[rgb_offset + 2] if rgb_offset + 2 < len(data) else 0,
            }
            rgb_offset += 3
        else:
            break
    
    return result


def get_color_channel_name(channel: int) -> str:
    """Helper to get color channel name"""
    channels = {0: "Red", 1: "Green", 2: "Blue"}
    return channels.get(channel, f"Channel_{channel}")


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


class StreamBuffer:
    """
    Buffer for ECU broadcast stream reassembly
    Based on TManiac's CanFT2p0Stream implementation
    """
    MAX_MEASURES = 24  # Maximum measures per stream
    
    def __init__(self):
        self.segment_count = 0
        self.data_count = 0  # Total bytes expected
        self.read_count = 0  # Bytes read so far
        self.buffer = bytearray()
        self.packets: List[FTCANSegmentedPacket] = []
    
    def add_packet(self, packet: FTCANSegmentedPacket) -> bool:
        """
        Add packet to stream buffer
        Returns True if stream is complete
        """
        if packet.segment_number == 0:
            # First segment - initialize buffer
            if packet.total_length is None:
                return False
            
            self.data_count = packet.total_length
            self.buffer = bytearray(self.data_count)
            self.read_count = 0
            self.segment_count = 1
            self.packets = [packet]
            
            # Store bytes in REVERSE order (as per TManiac implementation)
            payload = packet.payload
            for i, byte in enumerate(payload):
                if self.read_count < self.data_count:
                    # CRITICAL: Store in reverse order!
                    self.buffer[(self.data_count - 1) - self.read_count] = byte
                    self.read_count += 1
            
            return self.read_count >= self.data_count
        
        elif packet.segment_number == self.segment_count:
            # Expected next segment
            self.packets.append(packet)
            self.segment_count += 1
            
            # Store bytes in REVERSE order
            payload = packet.payload
            for i, byte in enumerate(payload):
                if self.read_count < self.data_count:
                    self.buffer[(self.data_count - 1) - self.read_count] = byte
                    self.read_count += 1
            
            return self.read_count >= self.data_count
        
        return False
    
    def get_complete_payload(self) -> Optional[bytes]:
        """Get complete reassembled payload if ready"""
        if self.read_count >= self.data_count and self.data_count > 0:
            return bytes(self.buffer[:self.data_count])
        return None
    
    def reset(self):
        """Reset buffer"""
        self.segment_count = 0
        self.data_count = 0
        self.read_count = 0
        self.buffer = bytearray()
        self.packets = []


class FTCANDecoder:
    """FTCAN 2.0 protocol decoder"""
    
    def __init__(self):
        # Legacy buffer for non-ECU devices (WB-O2, etc)
        self.segmented_packets: Dict[int, List[FTCANSegmentedPacket]] = {}
        
        # Stream buffers for ECU broadcasts (4 priority levels)
        self.stream_buffers: Dict[int, Dict[int, StreamBuffer]] = {
            BROADCAST_CRITICAL: {},  # Key: ProductID
            BROADCAST_HIGH: {},
            BROADCAST_MEDIUM: {},
            BROADCAST_LOW: {}
        }
    
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
                'is_response': ident.is_response,
                'broadcast_priority': self.get_broadcast_priority(ident.message_id),
                'special_message': self.get_special_message_info(ident.message_id)
            }
            
            # Check for SwitchPanel special messages
            if ident.product_type_id == ProductType.SWITCHPAD:
                if ident.message_id == 0x320:
                    result['switchpanel_buttons'] = decode_switchpanel_buttons(data)
                    result['is_complete'] = True
                    return result
                elif ident.message_id == 0x321:
                    result['switchpanel_light'] = decode_switchpanel_light(data)
                    result['is_complete'] = True
                    return result
            
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
                    
                    # Check if this is an ECU broadcast stream
                    is_ecu = ident.product_type_id in [ProductType.FT500_ECU, ProductType.FT600_ECU]
                    is_broadcast = ident.message_id in self.stream_buffers
                    
                    if is_ecu and is_broadcast:
                        # Use stream buffer system
                        stream_result = self._process_stream_packet(ident, packet)
                        if stream_result:
                            result.update(stream_result)
                        else:
                            result['is_complete'] = False
                    else:
                        # Use legacy reassembly for non-ECU devices
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
    
    def _process_stream_packet(self, ident: FTCANIdentification, packet: FTCANSegmentedPacket) -> Optional[Dict]:
        """
        Process packet using stream buffer system (for ECU broadcasts)
        Returns result dict if stream is complete, None otherwise
        """
        message_id = ident.message_id
        product_id = ident.product_id
        
        # Check if this is a broadcast stream
        if message_id not in self.stream_buffers:
            return None
        
        # Get or create stream buffer for this device+stream
        if product_id not in self.stream_buffers[message_id]:
            self.stream_buffers[message_id][product_id] = StreamBuffer()
        
        stream_buffer = self.stream_buffers[message_id][product_id]
        
        # Add packet to stream
        is_complete = stream_buffer.add_packet(packet)
        
        if is_complete:
            # Get complete payload
            complete_payload = stream_buffer.get_complete_payload()
            if complete_payload:
                # Reset buffer for next stream
                stream_buffer.reset()
                
                return {
                    'payload': complete_payload.hex(),
                    'is_complete': True,
                    'measures': self._decode_measures(complete_payload),
                    'stream_info': {
                        'priority': self.get_broadcast_priority(message_id),
                        'total_bytes': len(complete_payload),
                        'total_measures': len(complete_payload) // 4
                    }
                }
        
        return None
    
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
    
    def clear_stream_buffers(self):
        """Clear all stream buffers"""
        for priority_buffers in self.stream_buffers.values():
            for stream_buffer in priority_buffers.values():
                stream_buffer.reset()
            priority_buffers.clear()
    
    def clear_all_buffers(self):
        """Clear all buffers (legacy and stream)"""
        self.clear_segmented_buffers()
        self.clear_stream_buffers()
    
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
    
    @staticmethod
    def get_broadcast_priority(message_id: int) -> Optional[str]:
        """Get broadcast priority level"""
        return BROADCAST_PRIORITIES.get(message_id)
    
    @staticmethod
    def get_special_message_info(message_id: int) -> Optional[Dict]:
        """Get special message information"""
        return SPECIAL_MESSAGE_IDS.get(message_id)
