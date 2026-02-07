#!/usr/bin/env python3
"""
Baudrate Auto-Detection Tool

Detecta automaticamente o baudrate de um CAN bus.

Usage:
    python3 baudrate_detect.py [channel] [--quick]

Examples:
    python3 baudrate_detect.py can0
    python3 baudrate_detect.py can0 --quick
    python3 baudrate_detect.py vcan0
"""

import sys
import argparse
sys.path.insert(0, '../../')

from src.baudrate_detector import BaudrateDetector


def progress_callback(baudrate, status):
    """Callback para mostrar progresso"""
    if status == 'testing':
        print(f"🔍 Testing {baudrate:7d} bps...", end='', flush=True)
    elif status == 'found':
        print(f" ✅ FOUND!")
    elif status == 'failed':
        print(f" ❌")


def main():
    parser = argparse.ArgumentParser(
        description='Auto-detect CAN bus baudrate',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s can0              # Full detection on can0
  %(prog)s can0 --quick      # Quick detection (3 common baudrates)
  %(prog)s vcan0             # Detection on virtual CAN
        """
    )
    
    parser.add_argument(
        'channel',
        nargs='?',
        default='can0',
        help='CAN channel (default: can0)'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick detection (test only 3 common baudrates)'
    )
    
    parser.add_argument(
        '--interface',
        default='socketcan',
        help='CAN interface type (default: socketcan)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 CAN Baudrate Auto-Detection Tool")
    print("=" * 60)
    print()
    print(f"Channel:   {args.channel}")
    print(f"Interface: {args.interface}")
    print(f"Mode:      {'Quick (3 baudrates)' if args.quick else 'Full (7 baudrates)'}")
    print()
    print("Starting detection...")
    print()
    
    detector = BaudrateDetector(args.channel, args.interface)
    
    if args.quick:
        result = detector.detect(
            baudrates=[500000, 1000000, 250000],
            timeout_per_baudrate=1.5,
            min_messages=3,
            callback=progress_callback
        )
    else:
        result = detector.detect(callback=progress_callback)
    
    print()
    print("=" * 60)
    print("DETECTION RESULT")
    print("=" * 60)
    
    if result.baudrate:
        print(f"✅ Baudrate detected: {result.baudrate:,} bps")
        print(f"   Confidence:        {result.confidence * 100:.1f}%")
        print(f"   Messages received: {result.messages_received}")
        print(f"   Detection time:    {result.detection_time:.2f}s")
        print()
        print("You can now use this baudrate to connect:")
        print(f"   {result.baudrate} bps")
        return 0
    else:
        print("❌ No baudrate detected")
        print(f"   Tested baudrates:  {', '.join(str(b) for b in result.tested_baudrates)}")
        print(f"   Detection time:    {result.detection_time:.2f}s")
        print()
        print("Possible reasons:")
        print("  • No traffic on the CAN bus")
        print("  • CAN bus is not active")
        print("  • Wrong interface or channel")
        print("  • Baudrate not in common list")
        return 1
    
    print("=" * 60)


if __name__ == '__main__':
    sys.exit(main())
