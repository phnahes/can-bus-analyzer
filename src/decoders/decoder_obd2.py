"""
OBD-II Decoder - Core implementation of OBD-II protocol decoding
Supports ISO 15765-4 (CAN) - 11-bit and 29-bit

Based on SAE J1979 and contributions from:
- https://en.wikipedia.org/wiki/OBD-II_PIDs
- https://github.com/Knio/carhack/blob/master/carhack/lib/obd2/pids.py
"""

import struct
from typing import Optional, Dict, List


# OBD-II PIDs (Mode 01 - Current Data)
# Based on: https://en.wikipedia.org/wiki/OBD-II_PIDs
OBD2_PIDS = {
    # PIDs suportados
    0x00: {"name": "PIDs supported [01-20]", "bytes": 4, "unit": "", "type": "bitfield"},
    0x20: {"name": "PIDs supported [21-40]", "bytes": 4, "unit": "", "type": "bitfield"},
    0x40: {"name": "PIDs supported [41-60]", "bytes": 4, "unit": "", "type": "bitfield"},
    0x60: {"name": "PIDs supported [61-80]", "bytes": 4, "unit": "", "type": "bitfield"},
    0x80: {"name": "PIDs supported [81-A0]", "bytes": 4, "unit": "", "type": "bitfield"},
    0xA0: {"name": "PIDs supported [A1-C0]", "bytes": 4, "unit": "", "type": "bitfield"},
    0xC0: {"name": "PIDs supported [C1-E0]", "bytes": 4, "unit": "", "type": "bitfield"},
    
    # Status e diagnóstico
    0x01: {"name": "Monitor status since DTCs cleared", "bytes": 4, "unit": "", "type": "bitfield"},
    0x02: {"name": "DTC that caused freeze frame", "bytes": 2, "unit": "", "type": "dtc"},
    0x03: {"name": "Fuel system status", "bytes": 2, "unit": "", "type": "enum"},
    
    # Engine básico
    0x04: {"name": "Calculated engine load", "bytes": 1, "unit": "%", "type": "percent"},
    0x05: {"name": "Engine coolant temperature", "bytes": 1, "unit": "°C", "type": "temp_offset"},
    0x0C: {"name": "Engine RPM", "bytes": 2, "unit": "RPM", "type": "rpm"},
    0x0D: {"name": "Vehicle speed", "bytes": 1, "unit": "km/h", "type": "direct"},
    0x0E: {"name": "Timing advance", "bytes": 1, "unit": "° before TDC", "type": "timing"},
    0x0F: {"name": "Intake air temperature", "bytes": 1, "unit": "°C", "type": "temp_offset"},
    0x1F: {"name": "Run time since engine start", "bytes": 2, "unit": "s", "type": "uint16"},
    
    # Ar e combustível
    0x10: {"name": "MAF air flow rate", "bytes": 2, "unit": "g/s", "type": "maf"},
    0x11: {"name": "Throttle position", "bytes": 1, "unit": "%", "type": "percent"},
    0x45: {"name": "Relative throttle position", "bytes": 1, "unit": "%", "type": "percent"},
    0x47: {"name": "Absolute throttle position B", "bytes": 1, "unit": "%", "type": "percent"},
    0x48: {"name": "Absolute throttle position C", "bytes": 1, "unit": "%", "type": "percent"},
    0x49: {"name": "Accelerator pedal position D", "bytes": 1, "unit": "%", "type": "percent"},
    0x4A: {"name": "Accelerator pedal position E", "bytes": 1, "unit": "%", "type": "percent"},
    0x4B: {"name": "Accelerator pedal position F", "bytes": 1, "unit": "%", "type": "percent"},
    0x4C: {"name": "Commanded throttle actuator", "bytes": 1, "unit": "%", "type": "percent"},
    
    # Pressões
    0x0A: {"name": "Fuel pressure (gauge)", "bytes": 1, "unit": "kPa", "type": "fuel_pressure"},
    0x0B: {"name": "Intake manifold pressure", "bytes": 1, "unit": "kPa", "type": "direct"},
    0x22: {"name": "Fuel rail pressure (relative)", "bytes": 2, "unit": "kPa", "type": "fuel_rail_rel"},
    0x23: {"name": "Fuel rail gauge pressure", "bytes": 2, "unit": "kPa", "type": "fuel_rail_abs"},
    0x33: {"name": "Absolute barometric pressure", "bytes": 1, "unit": "kPa", "type": "direct"},
    0x59: {"name": "Fuel rail absolute pressure", "bytes": 2, "unit": "kPa", "type": "fuel_rail_abs"},
    
    # Temperaturas
    0x46: {"name": "Ambient air temperature", "bytes": 1, "unit": "°C", "type": "temp_offset"},
    0x5C: {"name": "Engine oil temperature", "bytes": 1, "unit": "°C", "type": "temp_offset"},
    
    # Combustível
    0x2F: {"name": "Fuel tank level input", "bytes": 1, "unit": "%", "type": "percent"},
    0x51: {"name": "Fuel type", "bytes": 1, "unit": "", "type": "fuel_type"},
    0x52: {"name": "Ethanol fuel %", "bytes": 1, "unit": "%", "type": "percent"},
    0x5E: {"name": "Engine fuel rate", "bytes": 2, "unit": "L/h", "type": "fuel_rate"},
    
    # Sondas lambda (O2)
    0x14: {"name": "O2 Sensor 1 (Voltage + STFT)", "bytes": 2, "unit": "V/%", "type": "o2_voltage"},
    0x15: {"name": "O2 Sensor 2 (Voltage + STFT)", "bytes": 2, "unit": "V/%", "type": "o2_voltage"},
    0x16: {"name": "O2 Sensor 3 (Voltage + STFT)", "bytes": 2, "unit": "V/%", "type": "o2_voltage"},
    0x17: {"name": "O2 Sensor 4 (Voltage + STFT)", "bytes": 2, "unit": "V/%", "type": "o2_voltage"},
    0x24: {"name": "O2 Sensor 1 (Lambda + Voltage)", "bytes": 4, "unit": "λ/V", "type": "o2_lambda"},
    0x25: {"name": "O2 Sensor 2 (Lambda + Voltage)", "bytes": 4, "unit": "λ/V", "type": "o2_lambda"},
    0x26: {"name": "O2 Sensor 3 (Lambda + Voltage)", "bytes": 4, "unit": "λ/V", "type": "o2_lambda"},
    0x27: {"name": "O2 Sensor 4 (Lambda + Voltage)", "bytes": 4, "unit": "λ/V", "type": "o2_lambda"},
    0x34: {"name": "O2 Sensor 1 (Lambda + Current)", "bytes": 4, "unit": "λ/mA", "type": "o2_lambda_current"},
    0x35: {"name": "O2 Sensor 2 (Lambda + Current)", "bytes": 4, "unit": "λ/mA", "type": "o2_lambda_current"},
    0x44: {"name": "Commanded Air-Fuel Ratio", "bytes": 2, "unit": "λ", "type": "commanded_lambda"},
    
    # Fuel trim
    0x06: {"name": "Short term fuel trim - Bank 1", "bytes": 1, "unit": "%", "type": "fuel_trim"},
    0x07: {"name": "Long term fuel trim - Bank 1", "bytes": 1, "unit": "%", "type": "fuel_trim"},
    0x08: {"name": "Short term fuel trim - Bank 2", "bytes": 1, "unit": "%", "type": "fuel_trim"},
    0x09: {"name": "Long term fuel trim - Bank 2", "bytes": 1, "unit": "%", "type": "fuel_trim"},
    
    # Distâncias e tempo
    0x21: {"name": "Distance with MIL on", "bytes": 2, "unit": "km", "type": "uint16"},
    0x31: {"name": "Distance since codes cleared", "bytes": 2, "unit": "km", "type": "uint16"},
    0x4D: {"name": "Time run with MIL on", "bytes": 2, "unit": "min", "type": "uint16"},
    0x4E: {"name": "Time since codes cleared", "bytes": 2, "unit": "min", "type": "uint16"},
    
    # Sistema elétrico
    0x42: {"name": "Control module voltage", "bytes": 2, "unit": "V", "type": "voltage"},
    0x5B: {"name": "Hybrid battery pack remaining life", "bytes": 1, "unit": "%", "type": "percent"},
    
    # Avançado
    0x43: {"name": "Absolute load value", "bytes": 2, "unit": "%", "type": "absolute_load"},
    0x5D: {"name": "Fuel injection timing", "bytes": 2, "unit": "°", "type": "injection_timing"},
    0x61: {"name": "Driver demand torque", "bytes": 1, "unit": "%", "type": "torque"},
    0x62: {"name": "Actual engine torque", "bytes": 1, "unit": "%", "type": "torque"},
    0x63: {"name": "Engine reference torque", "bytes": 2, "unit": "Nm", "type": "uint16"},
}


class OBD2Decoder:
    """Core OBD-II protocol decoder (ISO 15765-4)"""
    
    def __init__(self):
        # IDs padrão OBD-II
        self.standard_11bit_ids = {
            0x7DF: "Functional broadcast",
            0x7E0: "Engine ECU request",
            0x7E8: "Engine ECU response",
        }
        
        # Range de IDs de resposta (0x7E8 - 0x7EF)
        self.response_id_range = range(0x7E8, 0x7F0)
        self.request_id_range = range(0x7E0, 0x7E8)
    
    def decode_message(self, can_id: int, data: bytes, is_extended: bool) -> Dict:
        """
        Decode an OBD-II CAN message
        
        Args:
            can_id: CAN identifier
            data: Message data bytes
            is_extended: True if 29-bit ID, False if 11-bit
        
        Returns:
            Dictionary with decoded information
        """
        result = {
            'raw_id': can_id,
            'raw_data': data.hex(),
            'is_extended': is_extended,
            'error': None,
            'type': None,
            'service': None,
            'pid': None,
            'pid_name': None,
            'value': None,
            'description': None
        }
        
        try:
            if len(data) < 2:
                result['error'] = "Data too short"
                return result
            
            # Decode based on ID type
            if is_extended:
                self._decode_29bit(can_id, data, result)
            else:
                self._decode_11bit(can_id, data, result)
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _decode_11bit(self, can_id: int, data: bytes, result: Dict):
        """Decode 11-bit OBD-II message"""
        # First byte: PCI (Protocol Control Information)
        pci = data[0] >> 4  # Upper 4 bits
        length = data[0] & 0x0F  # Lower 4 bits
        
        # Single Frame (SF)
        if pci == 0:
            self._decode_single_frame(can_id, data, length, result)
        
        # First Frame (FF)
        elif pci == 1:
            total_length = ((data[0] & 0x0F) << 8) | data[1]
            result['type'] = 'first_frame'
            result['total_length'] = total_length
            result['description'] = f"First Frame (total: {total_length} bytes)"
        
        # Consecutive Frame (CF)
        elif pci == 2:
            sequence = data[0] & 0x0F
            result['type'] = 'consecutive_frame'
            result['sequence'] = sequence
            result['description'] = f"Consecutive Frame #{sequence}"
        
        # Flow Control (FC)
        elif pci == 3:
            flow_status = data[0] & 0x0F
            flow_names = {0: "CTS", 1: "Wait", 2: "Overflow"}
            result['type'] = 'flow_control'
            result['status'] = flow_status
            result['description'] = f"Flow Control: {flow_names.get(flow_status, 'Unknown')}"
    
    def _decode_single_frame(self, can_id: int, data: bytes, length: int, result: Dict):
        """Decode Single Frame OBD-II message"""
        if length < 1 or len(data) < length + 1:
            result['error'] = "Invalid frame length"
            return
        
        # Service/Mode (second byte)
        service = data[1]
        
        # Check if request or response
        is_response = can_id in self.response_id_range
        
        if is_response:
            # Response: service + 0x40
            actual_service = service - 0x40 if service >= 0x40 else service
            service_name = self._get_service_name(actual_service)
            result['type'] = 'response'
            result['service'] = actual_service
            
            # If Mode 01 (Current Data)
            if actual_service == 0x01 and length >= 2:
                pid = data[2]
                pid_info = OBD2_PIDS.get(pid, {"name": f"Unknown PID 0x{pid:02X}"})
                result['pid'] = pid
                result['pid_name'] = pid_info['name']
                
                # Decode value if available
                if length >= 3:
                    value_data = data[3:3+length-2]
                    result['value'] = self.decode_pid_value(pid, value_data)
                    result['description'] = f"Response: {service_name} - {pid_info['name']}{result['value']}"
                else:
                    result['description'] = f"Response: {service_name} - {pid_info['name']}"
            else:
                result['description'] = f"Response: {service_name}"
        else:
            # Request
            service_name = self._get_service_name(service)
            result['type'] = 'request'
            result['service'] = service
            
            if service == 0x01 and length >= 2:
                pid = data[2]
                pid_info = OBD2_PIDS.get(pid, {"name": f"Unknown PID 0x{pid:02X}"})
                result['pid'] = pid
                result['pid_name'] = pid_info['name']
                result['description'] = f"Request: {service_name} - {pid_info['name']}"
            else:
                result['description'] = f"Request: {service_name}"
    
    def _decode_29bit(self, can_id: int, data: bytes, result: Dict):
        """Decode 29-bit OBD-II message"""
        # Extract addresses
        priority = (can_id >> 26) & 0x07
        target_addr = (can_id >> 8) & 0xFF
        source_addr = can_id & 0xFF
        
        result['type'] = '29bit'
        result['priority'] = priority
        result['target'] = target_addr
        result['source'] = source_addr
        result['description'] = f"29-bit: {source_addr:02X} → {target_addr:02X}"
    
    def _get_service_name(self, service: int) -> str:
        """Return OBD-II service name"""
        services = {
            0x01: "Show current data",
            0x02: "Show freeze frame data",
            0x03: "Show stored DTCs",
            0x04: "Clear DTCs",
            0x05: "Test results (O2 sensors)",
            0x06: "Test results (other)",
            0x07: "Show pending DTCs",
            0x09: "Request vehicle information",
            0x0A: "Permanent DTCs",
        }
        return services.get(service, f"Service 0x{service:02X}")
    
    def decode_pid_value(self, pid: int, data: bytes) -> str:
        """
        Decode PID value with full support for all types
        
        Args:
            pid: PID number
            data: Raw data bytes
        
        Returns:
            Formatted string with decoded value
        """
        if len(data) == 0:
            return ""
        
        pid_info = OBD2_PIDS.get(pid)
        if not pid_info:
            return ""
        
        try:
            pid_type = pid_info.get('type', 'direct')
            
            # Decoding types
            if pid_type == 'direct':
                value = data[0]
                return f" = {value} {pid_info['unit']}"
            
            elif pid_type == 'percent':
                value = data[0] * 100 / 255
                return f" = {value:.1f}%"
            
            elif pid_type == 'temp_offset':
                temp = data[0] - 40
                return f" = {temp}°C"
            
            elif pid_type == 'rpm':
                if len(data) >= 2:
                    rpm = ((data[0] << 8) | data[1]) / 4
                    return f" = {rpm:.0f} RPM"
            
            elif pid_type == 'uint16':
                if len(data) >= 2:
                    value = (data[0] << 8) | data[1]
                    return f" = {value} {pid_info['unit']}"
            
            elif pid_type == 'voltage':
                if len(data) >= 2:
                    voltage = ((data[0] << 8) | data[1]) / 1000
                    return f" = {voltage:.2f}V"
            
            elif pid_type == 'fuel_pressure':
                value = data[0] * 3
                return f" = {value} kPa"
            
            elif pid_type == 'fuel_rail_rel':
                if len(data) >= 2:
                    value = ((data[0] << 8) | data[1]) * 0.079
                    return f" = {value:.2f} kPa"
            
            elif pid_type == 'fuel_rail_abs':
                if len(data) >= 2:
                    value = ((data[0] << 8) | data[1]) * 10
                    return f" = {value} kPa"
            
            elif pid_type == 'maf':
                if len(data) >= 2:
                    value = ((data[0] << 8) | data[1]) / 100
                    return f" = {value:.2f} g/s"
            
            elif pid_type == 'fuel_rate':
                if len(data) >= 2:
                    value = ((data[0] << 8) | data[1]) / 20
                    return f" = {value:.2f} L/h"
            
            elif pid_type == 'timing':
                value = data[0] / 2 - 64
                return f" = {value:.1f}° before TDC"
            
            elif pid_type == 'fuel_trim':
                value = data[0] * 100 / 128 - 100
                return f" = {value:.1f}%"
            
            elif pid_type == 'o2_voltage':
                if len(data) >= 2:
                    voltage = data[0] / 200
                    trim = data[1] * 100 / 128 - 100 if data[1] != 0xFF else None
                    if trim is not None:
                        return f" = {voltage:.3f}V, STFT: {trim:.1f}%"
                    else:
                        return f" = {voltage:.3f}V"
            
            elif pid_type == 'o2_lambda':
                if len(data) >= 4:
                    lambda_val = ((data[0] << 8) | data[1]) * 2 / 65536
                    voltage = ((data[2] << 8) | data[3]) * 8 / 65536
                    return f" = λ:{lambda_val:.3f}, {voltage:.2f}V"
            
            elif pid_type == 'o2_lambda_current':
                if len(data) >= 4:
                    lambda_val = ((data[0] << 8) | data[1]) * 2 / 65536
                    current = ((data[2] << 8) | data[3]) / 256 - 128
                    return f" = λ:{lambda_val:.3f}, {current:.1f}mA"
            
            elif pid_type == 'commanded_lambda':
                if len(data) >= 2:
                    lambda_val = ((data[0] << 8) | data[1]) * 2 / 65536
                    return f" = λ:{lambda_val:.3f}"
            
            elif pid_type == 'absolute_load':
                if len(data) >= 2:
                    value = ((data[0] << 8) | data[1]) * 100 / 255
                    return f" = {value:.1f}%"
            
            elif pid_type == 'injection_timing':
                if len(data) >= 2:
                    value = ((data[0] << 8) | data[1]) / 128 - 210
                    return f" = {value:.2f}°"
            
            elif pid_type == 'torque':
                value = data[0] - 125
                return f" = {value}%"
            
            elif pid_type == 'fuel_type':
                fuel_types = {
                    0: "Not available", 1: "Gasoline", 2: "Methanol", 3: "Ethanol",
                    4: "Diesel", 5: "LPG", 6: "CNG", 7: "Propane", 8: "Electric",
                    9: "Bifuel Gasoline", 10: "Bifuel Methanol", 11: "Bifuel Ethanol",
                    12: "Bifuel LPG", 13: "Bifuel CNG", 14: "Bifuel Propane",
                    15: "Bifuel Electric", 16: "Bifuel Gas/Electric", 
                    17: "Hybrid Gasoline", 18: "Hybrid Ethanol",
                    19: "Hybrid Diesel", 20: "Hybrid Electric", 21: "Hybrid Mixed",
                    22: "Hybrid Regenerative"
                }
                return f" = {fuel_types.get(data[0], f'Unknown ({data[0]})')}"
            
            elif pid_type == 'bitfield':
                # PIDs supported (0x00, 0x20, 0x40, etc.)
                if len(data) >= 4:
                    supported_pids = self.decode_supported_pids(pid, data)
                    return f" = {len(supported_pids)} PIDs: {', '.join(f'0x{p:02X}' for p in supported_pids[:8])}{'...' if len(supported_pids) > 8 else ''}"
        
        except:
            pass
        
        return ""
    
    def decode_supported_pids(self, base_pid: int, data: bytes) -> List[int]:
        """
        Decode supported PIDs bitfield
        
        Args:
            base_pid: Base PID (0x00, 0x20, 0x40, etc.)
            data: 4 bytes of bitfield
        
        Returns:
            List of supported PIDs
        """
        if len(data) < 4:
            return []
        
        # Combine 4 bytes into 32-bit integer
        bits = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
        
        # Check each bit (MSB first)
        supported = []
        for i in range(1, 33):  # Bits 31-0 represent PIDs +1 to +32
            if bits & (1 << (32 - i)):
                supported.append(base_pid + i)
        
        return supported
    
    def get_supported_pids(self, pid_00_data: bytes = None, pid_20_data: bytes = None, 
                          pid_40_data: bytes = None, pid_60_data: bytes = None) -> List[int]:
        """
        Return list of all supported PIDs based on responses from 0x00, 0x20, 0x40, 0x60
        
        Args:
            pid_00_data: Response from PID 0x00 (4 bytes)
            pid_20_data: Response from PID 0x20 (4 bytes)
            pid_40_data: Response from PID 0x40 (4 bytes)
            pid_60_data: Response from PID 0x60 (4 bytes)
        
        Returns:
            Complete list of supported PIDs
        """
        all_supported = []
        
        if pid_00_data:
            all_supported.extend(self.decode_supported_pids(0x00, pid_00_data))
        
        if pid_20_data:
            all_supported.extend(self.decode_supported_pids(0x20, pid_20_data))
        
        if pid_40_data:
            all_supported.extend(self.decode_supported_pids(0x40, pid_40_data))
        
        if pid_60_data:
            all_supported.extend(self.decode_supported_pids(0x60, pid_60_data))
        
        return sorted(all_supported)
    
    @staticmethod
    def is_obd2_message(can_id: int, is_extended: bool) -> bool:
        """Check if message is OBD-II"""
        if is_extended:
            # OBD-II 29-bit (less common)
            # IDs start with 0x18DA or 0x18DB
            return (can_id & 0x1FFF0000) in [0x18DA0000, 0x18DB0000]
        else:
            # OBD-II 11-bit (most common)
            # Standard IDs: 0x7DF (broadcast), 0x7E0-0x7E7 (requests), 0x7E8-0x7EF (responses)
            return (can_id == 0x7DF or 
                   (0x7E0 <= can_id <= 0x7E7) or 
                   (0x7E8 <= can_id <= 0x7EF))
    
    @staticmethod
    def get_expected_baudrates() -> List[int]:
        """Return expected baudrates for OBD-II"""
        return [250000, 500000]  # 250 kbps or 500 kbps
