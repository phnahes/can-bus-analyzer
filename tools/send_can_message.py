#!/usr/bin/env python3
"""
CAN Message Sender - Direct serial communication with CanHacker/Lawicel protocol devices
No external dependencies required (only pyserial)

Usage:
    python3 send_can_message.py              # Cycle through messages automatically
    python3 send_can_message.py --listen     # Listen-only mode (receive only)
    python3 send_can_message.py -l           # Same as --listen
    python3 send_can_message.py --debug      # Enable debug mode (shows raw data)
    python3 send_can_message.py -l --debug   # Listen mode with debug
"""

import serial
import time
import sys

class CANInterface:
    """Direct serial communication with CanHacker/Lawicel protocol devices"""
    
    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
    
    def connect(self):
        """Connect to CAN device"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(0.1)  # Wait for stabilization
            
            # Clear buffers
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            print(f"✓ Connected to {self.port}")
            return True
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def disconnect(self, debug=False):
        """Disconnect from device"""
        if self.serial and self.serial.is_open:
            self.send_command("C", debug=debug)  # Close CAN channel
            self.serial.close()
            print("✓ Disconnected")
    
    def test_connection(self):
        """Test if device responds to commands"""
        print("\n🔍 Testing device connection...")
        
        # Try version command
        print("  Testing 'V' (version) command...")
        if self.send_command("V", debug=True):
            print("  ✓ Device responds to version command")
        else:
            print("  ✗ No response to version command")
        
        # Try serial number command
        print("  Testing 'N' (serial) command...")
        if self.send_command("N", debug=True):
            print("  ✓ Device responds to serial command")
        else:
            print("  ✗ No response to serial command")
        
        print()
    
    def send_command(self, command, debug=False, expect_data=False):
        """Send command to device"""
        if not self.serial or not self.serial.is_open:
            print("✗ Serial port not open")
            return False
        
        try:
            # Clear input buffer before sending command
            self.serial.reset_input_buffer()
            
            cmd = command + "\r"
            self.serial.write(cmd.encode('ascii'))
            time.sleep(0.1)  # Increased delay for processing
            
            # Read response
            response = self.serial.read(100).decode('ascii', errors='ignore')
            
            if debug:
                print(f"[DEBUG] Command: {repr(command)}, Response: {repr(response)}")
            
            # For 'O' command, device might start sending CAN messages immediately
            # Just check if we got a CR somewhere in the response
            if expect_data and '\r' in response:
                if debug:
                    print(f"[DEBUG] Command successful, device started sending data")
                return True
            
            # Check for success (CR) or error (BEL)
            if '\r' in response:
                return True
            elif '\x07' in response:  # BEL (bell) = error
                if debug:
                    print(f"[DEBUG] Device returned error (BEL) for command: {command}")
                # For 'C' command, BEL might mean channel was already closed (not an error)
                if command == 'C':
                    return True
                return False
            elif response:
                # Some response but not CR or BEL
                if debug:
                    print(f"[DEBUG] Unexpected response: {repr(response)}")
                return True  # Try to continue anyway
            else:
                if debug:
                    print(f"[DEBUG] No response from device")
                return False
        except Exception as e:
            print(f"✗ Command error: {e}")
            return False
    
    def open_can_channel(self, bitrate=500000, debug=False):
        """
        Open CAN channel with specified bitrate
        
        Bitrate codes (CanHacker/Lawicel protocol):
        S0 = 10 kbit/s
        S1 = 20 kbit/s
        S2 = 50 kbit/s
        S3 = 100 kbit/s
        S4 = 125 kbit/s
        S5 = 250 kbit/s
        S6 = 500 kbit/s
        S7 = 800 kbit/s
        S8 = 1 Mbit/s
        """
        bitrate_codes = {
            10000: "S0",
            20000: "S1",
            50000: "S2",
            100000: "S3",
            125000: "S4",
            250000: "S5",
            500000: "S6",
            800000: "S7",
            1000000: "S8"
        }
        
        code = bitrate_codes.get(bitrate, "S6")
        
        if debug:
            print(f"[DEBUG] Attempting to configure bitrate: {bitrate} bps (command: {code})")
        
        # First, try to close any open channel
        self.send_command("C", debug=debug)
        time.sleep(0.1)
        
        # Configure bitrate
        if not self.send_command(code, debug=debug):
            print(f"✗ Failed to configure bitrate {bitrate}")
            print(f"  Tip: Make sure device is in reset mode (not already open)")
            print(f"  Tip: Try power cycling the device")
            return False
        
        print(f"✓ Bitrate configured: {bitrate} bps")
        
        # Open channel in normal mode (active)
        # Note: Device may start sending CAN messages immediately after 'O' command
        if not self.send_command("O", debug=debug, expect_data=True):
            print("✗ Failed to open CAN channel")
            print(f"  Tip: Check CAN bus connections (CAN-H, CAN-L)")
            print(f"  Tip: Verify 120Ω termination resistors")
            return False
        
        print("✓ CAN channel opened (active mode)")
        
        # Give device a moment to stabilize
        time.sleep(0.2)
        
        return True
    
    def send_can_message(self, can_id, data):
        """
        Send CAN message
        
        CanHacker/Lawicel format: tIIILDDDDDDDDDDDDDDDD<CR>
        - t: transmit standard frame
        - III: CAN ID (3 hex digits)
        - L: DLC (1 digit)
        - DD...: Data bytes (2 hex digits each)
        """
        if len(data) > 8:
            print("✗ Data too long (max 8 bytes)")
            return False
        
        # Format message in CanHacker/Lawicel protocol
        dlc = len(data)
        data_hex = ''.join(f'{byte:02X}' for byte in data)
        message = f"t{can_id:03X}{dlc}{data_hex}"
        
        if self.send_command(message):
            print(f"✓ Message sent: ID=0x{can_id:03X}, Data=[{', '.join(f'0x{b:02X}' for b in data)}]")
            return True
        else:
            print(f"✗ Failed to send message")
            return False
    
    def read_messages(self, duration=5, debug=False, show_header=True):
        """Read CAN messages for specified duration"""
        if show_header:
            print(f"\n📡 Listening for messages...")
        
        start_time = time.time()
        message_count = 0
        
        while (time.time() - start_time) < duration:
            if self.serial.in_waiting > 0:
                try:
                    line = self.serial.readline().decode('ascii', errors='ignore').strip()
                    
                    # Debug: show raw data
                    if debug and line:
                        print(f"[DEBUG] Raw: {repr(line)}")
                    
                    if not line:
                        continue
                    
                    # Parse different message types
                    if line.startswith('t'):
                        # Standard data frame: tIIILDDDDDDDDDDDDDDDD
                        can_id = int(line[1:4], 16)
                        dlc = int(line[4])
                        data_hex = line[5:5+dlc*2]
                        data = [int(data_hex[i:i+2], 16) for i in range(0, len(data_hex), 2)]
                        print(f"📨 RX: ID=0x{can_id:03X}, DLC={dlc}, Data=[{', '.join(f'0x{b:02X}' for b in data)}]")
                        message_count += 1
                        
                    elif line.startswith('T'):
                        # Extended data frame: TiiiiiiiiLDDDDDDDDDDDDDDDD
                        can_id = int(line[1:9], 16)
                        dlc = int(line[9])
                        data_hex = line[10:10+dlc*2]
                        data = [int(data_hex[i:i+2], 16) for i in range(0, len(data_hex), 2)]
                        print(f"📨 RX: ID=0x{can_id:08X} (EXT), DLC={dlc}, Data=[{', '.join(f'0x{b:02X}' for b in data)}]")
                        message_count += 1
                        
                    elif line.startswith('r'):
                        # Standard remote frame: riiiL
                        can_id = int(line[1:4], 16)
                        dlc = int(line[4])
                        print(f"📨 RX: ID=0x{can_id:03X}, DLC={dlc} (RTR)")
                        message_count += 1
                        
                    elif line.startswith('R'):
                        # Extended remote frame: RiiiiiiiiL
                        can_id = int(line[1:9], 16)
                        dlc = int(line[9])
                        print(f"📨 RX: ID=0x{can_id:08X} (EXT), DLC={dlc} (RTR)")
                        message_count += 1
                        
                    elif line and not line.startswith('\r'):
                        # Unknown format - show it
                        if debug:
                            print(f"[DEBUG] Unknown format: {line}")
                        
                except Exception as e:
                    if debug:
                        print(f"[DEBUG] Parse error: {e}")
                    pass
            time.sleep(0.01)
        
        if show_header:
            if message_count == 0:
                print("⚠ No messages received in this interval")
            else:
                print(f"✓ Received {message_count} message(s) in this interval")


def main():
    """Main function - cycles through messages automatically or listens only"""
    
    # Check for listen mode
    listen_mode = "--listen" in sys.argv or "-l" in sys.argv
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    # Configuration
    #PORT = "/dev/cu.usbserial-110"  # Adjust as needed
    PORT = "/dev/cu.usbmodemA021E7C81"  # Adjust as needed
    BITRATE = 500000  # 500 kbit/s
    DELAY_BETWEEN_MESSAGES = 1.0  # seconds
    
    # CAN messages (ID 0x333)
    messages = [
        [0x01, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        [0x02, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        [0x03, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        [0x04, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        [0x05, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        [0x06, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        [0x07, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    ]
    
    # Create CAN interface
    can_interface = CANInterface(PORT)
    
    try:
        # Connect
        if not can_interface.connect():
            sys.exit(1)
        
        # Test connection if debug mode
        if debug_mode:
            can_interface.test_connection()
        
        # Open CAN channel
        if not can_interface.open_can_channel(BITRATE, debug=debug_mode):
            sys.exit(1)
        
        print()
        
        if listen_mode:
            # Listen-only mode
            print("=" * 60)
            print("Listen-only mode - receiving CAN messages")
            if debug_mode:
                print("DEBUG MODE ENABLED - showing raw data")
            print("Press Ctrl+C to stop")
            print("=" * 60)
            
            # Listen indefinitely (continuous mode)
            can_interface.read_messages(duration=999999, debug=debug_mode, show_header=True)
        else:
            # Automatic message cycling mode
            print("=" * 60)
            print("Starting automatic message cycling...")
            if debug_mode:
                print("DEBUG MODE ENABLED - showing raw data")
            print(f"Press Ctrl+C to stop")
            print("=" * 60)
            print()
            
            # Cycle through messages
            message_index = 0
            while True:
                # Get current message
                data = messages[message_index]
                
                # Send message
                print(f"[Message {message_index + 1}/7]")
                can_interface.send_can_message(0x333, data)
                
                # Wait for responses
                can_interface.read_messages(duration=DELAY_BETWEEN_MESSAGES, debug=debug_mode)
                
                # Move to next message
                message_index = (message_index + 1) % len(messages)
                
                print()  # Empty line for readability
    
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    
    finally:
        # Disconnect
        can_interface.disconnect(debug=debug_mode)


if __name__ == "__main__":
    main()
