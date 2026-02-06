#!/usr/bin/env python3
"""
FTCAN 2.0 Message Simulator
Gera mensagens FTCAN de teste para validação do decoder
"""

import sys
import os
import struct
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.decoders.ftcan_decoder import FTCANDecoder, ProductType, DataFieldID


def create_ftcan_id(product_type_id: int, unique_id: int, data_field_id: int, message_id: int) -> int:
    """Cria um ID CAN FTCAN de 29 bits"""
    product_id = (product_type_id << 5) | (unique_id & 0x1F)
    can_id = (product_id << 14) | ((data_field_id & 0x07) << 11) | (message_id & 0x7FF)
    return can_id


def create_measure_data(data_id: int, value: int, is_status: bool = False) -> bytes:
    """Cria dados de uma medida (4 bytes)"""
    measure_id = (data_id << 1) | (1 if is_status else 0)
    return struct.pack('>Hh', measure_id, value)


def create_single_packet(measures: list) -> bytes:
    """Create a single FTCAN packet (0xFF + payload)"""
    payload = b''.join(measures)
    return bytes([0xFF]) + payload


def simulate_wbo2_nano():
    """Simula mensagens do WB-O2 Nano"""
    print("=" * 80)
    print("FTCAN 2.0 Simulator - WB-O2 Nano")
    print("=" * 80)
    print()
    
    decoder = FTCANDecoder()
    
    # WB-O2 Nano #1
    product_type_id = ProductType.WBO2_NANO
    unique_id = 0  # Primeiro dispositivo
    data_field_id = DataFieldID.FTCAN_2_0
    message_id = 0x1FF  # High priority broadcast
    
    can_id = create_ftcan_id(product_type_id, unique_id, data_field_id, message_id)
    
    print(f"Device: WB-O2 Nano #{unique_id}")
    print(f"CAN ID: 0x{can_id:08X}")
    print()
    
    # Simula leitura de lambda
    lambda_values = [
        (0.85, "Rich - Max Power"),
        (0.90, "Slightly Rich"),
        (1.00, "Stoichiometric"),
        (1.05, "Slightly Lean - Economy"),
        (0.82, "Very Rich - High Boost"),
    ]
    
    for lambda_val, description in lambda_values:
        # Converte lambda para valor raw (multiplicador 0.001)
        raw_value = int(lambda_val * 1000)
        
        # Cria medida: Cylinder 1 O2 (DataID 0x0013)
        measure = create_measure_data(0x0013, raw_value)
        
        # Cria pacote
        data = create_single_packet([measure])
        
        # Decodifica
        result = decoder.decode_message(can_id, data)
        
        print(f"Lambda: {lambda_val:.3f} - {description}")
        print(f"  Raw Data: {data.hex().upper()}")
        
        if result['measures']:
            for m in result['measures']:
                print(f"  Decoded: {m['formatted']}")
        
        print()
        time.sleep(0.1)


def simulate_ft600_ecu():
    """Simula mensagens da ECU FT600"""
    print("=" * 80)
    print("FTCAN 2.0 Simulator - FT600 ECU")
    print("=" * 80)
    print()
    
    decoder = FTCANDecoder()
    
    # FT600 ECU #0
    product_type_id = ProductType.FT600_ECU
    unique_id = 0
    data_field_id = DataFieldID.FTCAN_2_0
    message_id = 0x1FF  # High priority broadcast
    
    can_id = create_ftcan_id(product_type_id, unique_id, data_field_id, message_id)
    
    print(f"Device: FT600 ECU #{unique_id}")
    print(f"CAN ID: 0x{can_id:08X}")
    print()
    
    # Simulate multiple measures in one packet
    measures = [
        (0x0042, 3500, "RPM"),           # RPM: 3500
        (0x0001, 850, "TPS"),            # TPS: 85.0% (850 * 0.1)
        (0x0002, 1500, "MAP"),           # MAP: 1.5 Bar (1500 * 0.001)
        (0x0004, 850, "Engine Temp"),    # Temp: 85.0°C (850 * 0.1)
    ]
    
    measure_data = []
    for data_id, raw_value, name in measures:
        measure_data.append(create_measure_data(data_id, raw_value))
    
    # Create packet with multiple measures
    data = create_single_packet(measure_data)
    
    # Decodifica
    result = decoder.decode_message(can_id, data)
    
    print(f"Multi-measure packet:")
    print(f"  Raw Data: {data.hex().upper()}")
    print(f"  Measures: {len(result['measures'])}")
    print()
    
    if result['measures']:
        for m in result['measures']:
            print(f"  • {m['formatted']}")
    
    print()


def simulate_standard_can():
    """Simulate Standard CAN messages (not FTCAN)"""
    print("=" * 80)
    print("Standard CAN Messages (Non-FTCAN)")
    print("=" * 80)
    print()
    
    decoder = FTCANDecoder()
    
    # Standard CAN messages (11-bit)
    standard_messages = [
        (0x100, bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])),
        (0x200, bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])),
        (0x7FF, bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])),
    ]
    
    for can_id, data in standard_messages:
        is_ftcan = FTCANDecoder.is_ftcan_message(can_id)
        print(f"CAN ID: 0x{can_id:03X}")
        print(f"  Data: {data.hex().upper()}")
        print(f"  Is FTCAN: {is_ftcan}")
        print()


def simulate_segmented_packet():
    """Simula pacote segmentado FTCAN"""
    print("=" * 80)
    print("FTCAN 2.0 Simulator - Segmented Packet")
    print("=" * 80)
    print()
    
    decoder = FTCANDecoder()
    
    # WB-O2 Nano
    product_type_id = ProductType.WBO2_NANO
    unique_id = 0
    data_field_id = DataFieldID.FTCAN_2_0
    message_id = 0x1FF
    
    can_id = create_ftcan_id(product_type_id, unique_id, data_field_id, message_id)
    
    # Cria payload grande (10 medidas = 40 bytes)
    measures = []
    for i in range(10):
        data_id = 0x0013 + i  # Cylinder 1-10 O2
        value = 850 + i * 10  # Lambda variando
        measures.append(create_measure_data(data_id, value))
    
    payload = b''.join(measures)
    total_length = len(payload)
    
    print(f"Total payload: {total_length} bytes")
    print()
    
    # First segment (0x00 + segmentation data + up to 5 bytes)
    segmentation_data = struct.pack('>H', total_length & 0x07FF)
    first_segment = bytes([0x00]) + segmentation_data + payload[:5]
    
    print("Segment 0 (First):")
    print(f"  Data: {first_segment.hex().upper()}")
    result = decoder.decode_message(can_id, first_segment)
    print(f"  Total Length: {result.get('total_length')} bytes")
    print(f"  Complete: {result.get('is_complete')}")
    print()
    
    # Subsequent segments (0x01, 0x02, ... + up to 7 bytes each)
    offset = 5
    segment_num = 1
    
    while offset < total_length:
        chunk_size = min(7, total_length - offset)
        segment_data = bytes([segment_num]) + payload[offset:offset+chunk_size]
        
        print(f"Segment {segment_num}:")
        print(f"  Data: {segment_data.hex().upper()}")
        result = decoder.decode_message(can_id, segment_data)
        print(f"  Complete: {result.get('is_complete')}")
        
        if result.get('is_complete'):
            print(f"  Measures decoded: {len(result.get('measures', []))}")
            for m in result.get('measures', [])[:3]:  # Mostra primeiras 3
                print(f"    • {m['formatted']}")
        
        print()
        
        offset += chunk_size
        segment_num += 1


def main():
    """Menu principal"""
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        FTCAN 2.0 Protocol Simulator & Tester              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print("Select simulation:")
    print("  1. WB-O2 Nano (Lambda readings)")
    print("  2. FT600 ECU (Multiple measures)")
    print("  3. Standard CAN (Non-FTCAN)")
    print("  4. Segmented Packet")
    print("  5. Run all simulations")
    print("  0. Exit")
    print()
    
    choice = input("Choice: ").strip()
    print()
    
    if choice == '1':
        simulate_wbo2_nano()
    elif choice == '2':
        simulate_ft600_ecu()
    elif choice == '3':
        simulate_standard_can()
    elif choice == '4':
        simulate_segmented_packet()
    elif choice == '5':
        simulate_wbo2_nano()
        simulate_ft600_ecu()
        simulate_standard_can()
        simulate_segmented_packet()
    elif choice == '0':
        print("Exiting...")
        return
    else:
        print("Invalid choice!")
        return
    
    print()
    print("=" * 80)
    print("Simulation complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
