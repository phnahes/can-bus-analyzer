# General CAN Tools

Python tools for working with CAN bus: sending messages, detecting baudrate, and polling OBD-II data.

---

## Contents

- [Scripts Overview](#scripts-overview)
- [Installation](#installation)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Advanced Examples](#advanced-examples)

---

## Scripts Overview

### `send_can_message.py`

Direct serial communication with Lawicel SLCAN protocol devices (Arduino, USBtin, etc.).

**Features:**
- Send message groups with individual CAN IDs and periods
- Sequential or individual period transmission modes
- Listen-only mode for receiving messages
- Debug mode for troubleshooting
- No external dependencies (only pyserial)

**Basic Usage:**
```bash
# Send predefined message group automatically
python3 send_can_message.py

# Listen-only mode (receive only)
python3 send_can_message.py --listen

# Enable debug mode
python3 send_can_message.py --debug

# Listen with debug
python3 send_can_message.py --listen --debug
```

**Configuration:**
Edit the `message_group` list in the script to define your messages:
```python
message_group = [
    {'id': 0x100, 'data': [0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], 'period_ms': 10},
    {'id': 0x200, 'data': [0x00, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], 'period_ms': 20},
    {'id': 0x300, 'data': [0x5A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], 'period_ms': 100},
]
```

**Port Configuration:**
Edit `PORT` variable in the script:
```python
PORT = "/dev/tty.usbmodemA021E7C81"  # macOS
# PORT = "/dev/ttyACM0"              # Linux
# PORT = "COM3"                      # Windows
```

**Output Example:**
```
✓ Connected to /dev/tty.usbmodemA021E7C81
✓ Bitrate configured: 500000 bps
✓ CAN channel opened (active mode)

============================================================
Starting automatic message cycling...
Press Ctrl+C to stop
============================================================

[Message 1/7]
Message sent: ID=0x333, Data=[0x01, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

Listening for messages (1.0 seconds)...
RX: ID=0x280, DLC=8, Data=[0xBB, 0x8E, 0x00, 0x00, 0x29, 0xFA, 0x29, 0x29]
```

---

### `baudrate_detect.py`

Automatic CAN bus baudrate detection tool.

**Features:**
- Tests common CAN baudrates (10k to 1M)
- Quick mode (3 most common baudrates)
- Full mode (7 standard baudrates)
- Progress callback with real-time feedback
- Confidence score based on message reception
- Works with SocketCAN and other interfaces

**Usage:**
```bash
# Full detection on can0
python3 baudrate_detect.py can0

# Quick detection (500k, 1M, 250k only)
python3 baudrate_detect.py can0 --quick

# Virtual CAN
python3 baudrate_detect.py vcan0

# Specify interface type
python3 baudrate_detect.py can0 --interface socketcan
```

**Output Example:**
```
============================================================
🚀 CAN Baudrate Auto-Detection Tool
============================================================

Channel:   can0
Interface: socketcan
Mode:      Full (7 baudrates)

Starting detection...

🔍 Testing   10000 bps... ❌
🔍 Testing   20000 bps... ❌
🔍 Testing   50000 bps... ❌
🔍 Testing  125000 bps... ❌
🔍 Testing  250000 bps... ❌
🔍 Testing  500000 bps... ✅ FOUND!

============================================================
DETECTION RESULT
============================================================
✅ Baudrate detected: 500,000 bps
   Confidence:        95.5%
   Messages received: 47
   Detection time:    2.34s

You can now use this baudrate to connect:
  can0 @ 500000 bps
```

**How it works:**
1. Tests each baudrate for 2-3 seconds
2. Counts received messages
3. Calculates confidence based on message rate
4. Returns first baudrate with sufficient traffic

---

### `obd2_poller.py`

Automatic OBD-II data poller and decoder.

**Features:**
- Polls multiple PIDs automatically
- Real-time decoding of OBD-II responses
- Supports Service 01 (current data)
- Configurable polling interval
- CSV export capability
- Statistics and monitoring

**Usage:**
```bash
# Poll default PIDs on can0
python3 obd2_poller.py

# Specify channel
python3 obd2_poller.py --channel can0

# Custom PIDs
python3 obd2_poller.py --pids 0x0C 0x0D 0x05 0x11

# Faster polling (500ms)
python3 obd2_poller.py --interval 0.5

# Save to CSV
python3 obd2_poller.py --output data.csv

# Limit number of polls
python3 obd2_poller.py --count 100
```

**Default PIDs:**
- `0x0C` - Engine RPM
- `0x0D` - Vehicle speed
- `0x05` - Engine coolant temperature
- `0x11` - Throttle position
- `0x04` - Engine load
- `0x0F` - Intake air temperature
- `0x2F` - Fuel level
- `0x42` - Control module voltage

**Output Example:**
```
============================================================
🚗 OBD-II Automatic Poller
============================================================

Channel:  can0
Bitrate:  500000 bps
PIDs:     0x0C, 0x0D, 0x05, 0x11, 0x04, 0x0F, 0x2F, 0x42
Interval: 1.0s

✅ Connected: can0 @ 500000 bps

Starting polling... (Press Ctrl+C to stop)

[2024-02-06 10:15:23]
  RPM:         2847 rpm
  Speed:       85 km/h
  Coolant:     89°C
  Throttle:    42.5%
  Load:        67.8%
  Intake Air:  28°C
  Fuel Level:  68.2%
  Battery:     14.2V

[2024-02-06 10:15:24]
  RPM:         2891 rpm
  Speed:       87 km/h
  ...
```

**CSV Export:**
```bash
python3 obd2_poller.py --output obd_data.csv --count 1000
```

Output file format:
```csv
timestamp,rpm,speed,coolant_temp,throttle_pos,engine_load,intake_temp,fuel_level,battery_voltage
2024-02-06 10:15:23,2847,85,89,42.5,67.8,28,68.2,14.2
2024-02-06 10:15:24,2891,87,90,43.1,68.2,28,68.1,14.3
```

---

## Installation

### Dependencies

**For `send_can_message.py`:**
```bash
pip install pyserial
```

**For `baudrate_detect.py` and `obd2_poller.py`:**
```bash
pip install python-can
```

**All at once:**
```bash
pip install pyserial python-can
```

### Supported Interfaces

**python-can** supports:
- `socketcan` (Linux)
- `slcan` (Serial CAN / Lawicel)
- `pcan` (PEAK-CAN)
- `ixxat` (IXXAT)
- `vector` (Vector)
- `kvaser` (Kvaser)
- `neovi` (Intrepid)
- `virtual` (Virtual CAN for testing)

---

## Usage Examples

### 1. Quick Communication Test

**Terminal 1 - Send messages:**
```bash
python3 send_can_message.py
```

**Terminal 2 - CAN Analyzer:**
Open CAN Analyzer and verify message reception.

---

### 2. Detect Unknown Bus Speed

```bash
# Quick check (3 common speeds)
python3 baudrate_detect.py can0 --quick

# Full scan (7 standard speeds)
python3 baudrate_detect.py can0
```

---

### 3. Monitor OBD-II Data

```bash
# Monitor default PIDs
python3 obd2_poller.py --channel can0

# Monitor specific PIDs with faster polling
python3 obd2_poller.py --pids 0x0C 0x0D --interval 0.5

# Log to CSV for analysis
python3 obd2_poller.py --output vehicle_data.csv --count 3600
```

---

### 4. Simulate ECU with SLCAN

```bash
# Edit send_can_message.py to define your ECU messages
# Then run:
python3 send_can_message.py
```

Example message group for ECU simulation:
```python
message_group = [
    # RPM: 3000 RPM (0x0BB8 / 4 = 3000)
    {'id': 0x200, 'data': [0x0B, 0xB8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], 'period_ms': 100},
    
    # TPS: 45% (0x2D * 100/255 = 45%)
    {'id': 0x201, 'data': [0x2D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], 'period_ms': 100},
    
    # Temperature: 85°C (0x55 + 40 = 125, 125-40 = 85)
    {'id': 0x202, 'data': [0x55, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], 'period_ms': 500},
]
```

---

### 5. Test OBD-II Request/Response

**Terminal 1 - Start OBD-II simulator (Arduino):**
```bash
# Upload arduino_obd2_ecu_simulator.ino to Arduino
# See ../arduino/README.md
```

**Terminal 2 - Poll data:**
```bash
python3 obd2_poller.py --channel can0
```

---

## Configuration

### Linux (SocketCAN)

**Setup CAN interface:**
```bash
# Configure bitrate and bring up
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0

# Verify
ip -details link show can0

# Monitor traffic
candump can0
```

**Virtual CAN (for testing):**
```bash
# Load module
sudo modprobe vcan

# Create virtual interface
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Test
python3 send_can_message.py  # (edit to use vcan0)
```

---

### macOS (SLCAN)

**Using Arduino or USB-CAN adapter:**
```bash
# Find device
ls /dev/tty.usbmodem* /dev/tty.usbserial*

# Use with send_can_message.py
# Edit PORT in script to match your device
```

---

### Windows

**Using PCAN or other adapter:**
```bash
# Install python-can with PCAN support
pip install python-can[pcan]

# Use with scripts
python3 obd2_poller.py --channel PCAN_USBBUS1 --interface pcan
```

---

## Troubleshooting

### Error: "Network is down"

**Linux:**
```bash
# Bring interface up
sudo ip link set up can0

# Check status
ip link show can0
```

---

### Error: "Permission denied"

**Linux:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Log out and log back in

# Or temporary fix
sudo chmod 666 /dev/ttyACM0
```

---

### Error: "No such device"

**Check available interfaces:**
```bash
# Linux
ip link show
ifconfig -a

# macOS
ls /dev/tty.*

# Windows
# Check Device Manager
```

---

### Error: "Failed to configure bitrate" (send_can_message.py)

1. Enable debug mode: `python3 send_can_message.py --debug`
2. Check device response in debug output
3. Common issues:
   - Wrong port (verify with `ls /dev/tty.*`)
   - Device already open (close other programs)
   - Wrong baudrate (try 9600 or 19200)
   - Arduino not programmed with SLCAN firmware

**Test device manually:**
```bash
screen /dev/tty.usbmodem* 115200
V       # Should return version (e.g., V1013)
S6      # Configure 500 Kbps
O       # Open channel
C       # Close channel
# Exit: Ctrl+A then K then Y
```

---

### No Messages in Baudrate Detection

1. Verify CAN bus has active traffic
2. Check termination resistors (120Ω at both ends)
3. Verify CAN-H and CAN-L connections
4. Try different interface (vcan0 for testing)
5. Use `candump can0` to verify traffic

---

### OBD-II Poller Not Receiving Responses

1. Verify ECU is connected and powered
2. Check baudrate (OBD-II typically 500 kbps)
3. Verify request ID (0x7DF) and response IDs (0x7E8-0x7EF)
4. Test with Arduino OBD-II simulator first
5. Enable debug in script to see raw messages

---

## Advanced Examples

### Automated Test Script

```bash
#!/bin/bash
# test_can_bus.sh

echo "🔍 CAN Bus Test Suite"
echo "====================="

# Test 1: Detect baudrate
echo "Test 1: Baudrate detection..."
python3 baudrate_detect.py can0 --quick
BAUDRATE=$?

# Test 2: Send test messages
echo "Test 2: Sending test messages..."
# (Configure send_can_message.py first)
timeout 5 python3 send_can_message.py &

# Test 3: Poll OBD-II data
echo "Test 3: OBD-II polling..."
timeout 10 python3 obd2_poller.py --count 10

echo "✅ Test suite completed!"
```

---

### Data Logging Script

```bash
#!/bin/bash
# log_obd_data.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT="obd_log_${TIMESTAMP}.csv"

echo "📊 Starting OBD-II data logging..."
echo "Output: $OUTPUT"
echo "Press Ctrl+C to stop"

python3 obd2_poller.py \
    --channel can0 \
    --interval 1.0 \
    --output "$OUTPUT"

echo "✅ Log saved to $OUTPUT"
```

---

### Multi-ECU Simulator

```bash
#!/bin/bash
# simulate_multi_ecu.sh

echo "🚗 Starting Multi-ECU Simulation"

# ECU 1: Engine (ID 0x100-0x1FF)
# Edit send_can_message.py with engine messages
python3 send_can_message.py &
PID1=$!

# ECU 2: Transmission (ID 0x200-0x2FF)
# Use second instance with different messages
# python3 send_can_message.py &
# PID2=$!

echo "Simulation running (PIDs: $PID1)"
echo "Press Ctrl+C to stop"

# Wait for Ctrl+C
trap "kill $PID1; exit" INT
wait
```

---

### Continuous Monitoring Dashboard

```python
#!/usr/bin/env python3
"""
Real-time OBD-II dashboard
Displays live data in terminal
"""

import curses
import time
from obd2_poller import OBD2Poller

def main(stdscr):
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Non-blocking input
    
    poller = OBD2Poller('can0')
    if not poller.connect():
        return
    
    try:
        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, "=== OBD-II Live Dashboard ===", curses.A_BOLD)
            
            # Poll and display data
            data = poller.poll_all()
            
            row = 2
            for key, value in data.items():
                stdscr.addstr(row, 2, f"{key}: {value}")
                row += 1
            
            stdscr.addstr(row + 2, 0, "Press 'q' to quit")
            stdscr.refresh()
            
            # Check for quit
            if stdscr.getch() == ord('q'):
                break
            
            time.sleep(1)
    
    finally:
        poller.disconnect()

if __name__ == '__main__':
    curses.wrapper(main)
```

---

## Related Tools

- **CAN Analyzer (Main App):** `../../README.md`
- **Arduino CAN Tools:** `../arduino/README.md`
- **FTCAN Tools:** `../ftcan/README.md`

---

## Resources

### Documentation
- **python-can:** https://python-can.readthedocs.io/
- **SocketCAN:** https://www.kernel.org/doc/html/latest/networking/can.html
- **OBD-II PIDs:** https://en.wikipedia.org/wiki/OBD-II_PIDs
- **Lawicel SLCAN:** http://www.can232.com/docs/canusb_manual.pdf

### Tutorials
- **CAN Bus Explained:** https://www.csselectronics.com/pages/can-bus-simple-intro-tutorial
- **SocketCAN Tutorial:** https://elinux.org/Bringing_CAN_interface_up
- **OBD-II Basics:** https://www.csselectronics.com/pages/obd2-explained-simple-intro

### Examples
- **python-can Examples:** https://github.com/hardbyte/python-can/tree/develop/examples
- **OBD-II Python:** https://python-obd.readthedocs.io/

---

## Contributing

Suggestions for improvements:
- Add more OBD-II services (02, 03, 04, etc.)
- Support for J1939 protocol
- GUI version of tools
- Real-time graphing
- CAN frame fuzzing/testing
- DBC file support
