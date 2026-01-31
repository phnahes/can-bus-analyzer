# CAN Testing Tools

Practical examples for testing and using the CAN Analyzer with different devices and protocols.

## Contents

- [Python Script](#python-script)
- [Arduino Examples](#arduino-examples)
- [Arduino as CAN Interface](#arduino-as-can-interface)
- [Protocol Reference](#protocol-reference)

---

## Python Script

### send_can_message.py

Python script for direct serial communication with CanHacker/Lawicel protocol devices.

**Features:**
- Direct serial communication (no external dependencies except pyserial)
- Native protocol implementation
- Automatic message cycling through 7 test messages
- Listen-only mode for receive-only operation
- Message reception monitoring between transmissions
- Multiple CAN bitrate support

**Requirements:**
```bash
pip install pyserial
```

**Usage:**

```bash
# Identify serial port
ls /dev/tty.usbmodem*  # macOS
ls /dev/ttyACM*        # Linux

# Cycle through messages automatically
python3 send_can_message.py

# Listen-only mode (receive only)
python3 send_can_message.py --listen

# Debug mode
python3 send_can_message.py --debug
```

**Configuration:**

Edit the script to change the serial port:
```python
PORT = "/dev/tty.usbmodemA021E7C81"  # Your port here
```

**Example Output:**

```
Connected to /dev/tty.usbmodemA021E7C81
Bitrate configured: 500000 bps
CAN channel opened (active mode)

============================================================
Starting automatic message cycling...
Press Ctrl+C to stop
============================================================

[Message 1/7]
Message sent: ID=333, Data=[0x01, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

Listening for messages (1.0 seconds)...
RX: ID=0x280, DLC=8, Data=[0xBB, 0x8E, 0x00, 0x00, 0x29, 0xFA, 0x29, 0x29]

[Message 2/7]
Message sent: ID=0x333, Data=[0x02, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
...
```

**Troubleshooting:**

If you see "Failed to configure bitrate":

1. Enable debug mode: `python3 send_can_message.py --debug`
2. Check device response in debug output
3. Common issues:
   - Wrong port (verify with `ls /dev/tty.*`)
   - Device already open (close other programs)
   - Wrong baudrate (try 9600 or 19200)
   - Arduino not programmed with CanHacker firmware

4. Test device manually:
   ```bash
   screen /dev/cu.usbserial-110 115200
   V       # Should return version (e.g., V1013)
   S6      # Configure 500 Kbps
   O       # Open channel
   C       # Close channel
   # Exit: Ctrl+A then K then Y
   ```

---

## Arduino Tools

### arduino_msg_generator.ino

Configurable CAN message generator for testing reception.

**Features:**
- Standard (11-bit) or Extended (29-bit) IDs
- Fixed or random IDs within a range
- Configurable data length (0-8 bytes or random)
- Configurable period (fixed or random)
- Custom or random data content
- Predefined message groups (simulate multiple ECUs)
- Remote Frame support
- Individual period control per message

**Hardware:**
- Arduino (Uno, Mega, etc.)
- MCP2515 CAN module
- Connections: CS=Pin 10, INT=Pin 2

**Installation:**

1. Install libraries in Arduino IDE:
   - **Seeed CAN-BUS Shield Library**: Library Manager → Search "CAN-BUS Shield"

2. Configure shield type:
   ```cpp
   #define CAN_2515    // For MCP2515
   // #define CAN_2518FD  // For MCP2518FD
   ```

3. Upload to Arduino

**Configuration Examples:**

**Example 1: Fixed periodic message with custom data**
```cpp
#define USE_STANDARD_ID    true
#define USE_SPECIFIC_ID    true
#define SPECIFIC_ID        0x123
#define DATA_LENGTH        8
#define USE_RANDOM_PERIOD  false
#define DELAY_MS           100
#define USE_CUSTOM_DATA    true
#define CUSTOM_DATA        {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88}
```

**Example 2: Message group (simulate ECU)**
```cpp
#define USE_MESSAGE_GROUP      true
#define USE_INDIVIDUAL_PERIODS true

CANMessage messageGroup[] = {
    // ID,    Ext,   Rem,  Len, Period, {Data bytes}
    {0x100, false, false,  2,   10,    {0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // RPM - 10ms
    {0x200, false, false,  2,   20,    {0x00, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Speed - 20ms
    {0x300, false, false,  1,   100,   {0x5A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Temp - 100ms
};
```

### arduino_msg_receiver.ino

CAN message receiver for testing transmission.

**Features:**
- Receives all CAN messages (Standard and Extended)
- Displays complete details (ID, type, length, data)
- Real-time statistics (count, message rate)
- Optional ID filtering
- Timestamp for each message
- Remote Frame detection

**Configuration:**
```cpp
#define SHOW_TIMESTAMP     true    // Show timestamp
#define SHOW_STATISTICS    true    // Show periodic stats
#define STATS_INTERVAL     5000    // Stats interval (ms)

// Optional filtering
#define USE_FILTER         false   // Enable ID filtering
#define FILTER_ID          0x100   // Filter ID
#define FILTER_MASK        0x7FF   // Filter mask
```

**Output Format:**
```
[    123456] RX: [00000123](00) 11 22 33 44 55 66 77 88
```

Where:
- `[123456]` = Timestamp (ms)
- `[00000123]` = Message ID (hex)
- `(00)` = Message type:
  - `0x00` = Standard Data Frame
  - `0x02` = Extended Data Frame
  - `0x30` = Standard Remote Frame
  - `0x32` = Extended Remote Frame
- `11 22 33...` = Data (hex)

---

## Arduino as CAN Interface

Transform your **Arduino + MCP2515** into a professional CAN interface compatible with the **CanHacker/Lawicel SLCAN** protocol.

### Advantages

- **Low cost**: Arduino + MCP2515 costs ~$10 (vs $50-100 for commercial adapters)
- **Standard protocol**: Compatible with CanHacker, python-can, and other tools
- **Open-source**: Fully customizable code
- **No proprietary drivers**: Uses standard serial communication
- **Full functionality**: Supports all Lawicel protocol features

### Hardware Required

| Component | Specification | Approx. Price |
|-----------|---------------|---------------|
| Arduino Uno/Nano/Mega | Any model | $5-15 |
| MCP2515 Module | CAN controller + transceiver | $3-8 |
| Jumper Wires | For connections | $1-2 |
| 120Ω Terminators | 2x resistors | $0.50 |

**Total: ~$10-25** (vs $50-100 for commercial adapters)

### Wiring

**MCP2515 → Arduino:**

| MCP2515 | Arduino Uno/Nano | Arduino Mega |
|---------|------------------|--------------|
| VCC | 5V | 5V |
| GND | GND | GND |
| CS | Pin 10 | Pin 10 |
| SO (MISO) | Pin 12 | Pin 50 |
| SI (MOSI) | Pin 11 | Pin 51 |
| SCK | Pin 13 | Pin 52 |
| INT | Pin 2 | Pin 2 |

**CAN Bus Connection:**

| MCP2515 | CAN Bus |
|---------|---------|
| CANH | CAN-H |
| CANL | CAN-L |

**Important:** Add 120Ω termination resistors between CAN-H and CAN-L at **both ends** of the CAN bus.

### Library Installation

**Method 1: Arduino Library Manager (Recommended)**

1. Open Arduino IDE
2. Go to **Sketch** → **Include Library** → **Manage Libraries...**
3. Search for **"CanHacker"**
4. Install **"CanHacker by autowp"**
5. Also install **"MCP2515 by autowp"** (dependency)

**Method 2: Manual**

```bash
cd ~/Documents/Arduino/libraries/
git clone https://github.com/autowp/arduino-mcp2515.git
git clone https://github.com/autowp/arduino-canhacker.git
```

### Arduino Code

**Use the official example from arduino-canhacker library:**

1. **Open example in Arduino IDE:**
   - **File** → **Examples** → **CanHacker** → **usb_cdc**

2. **Or access directly:**
   - **Repository**: [arduino-canhacker](https://github.com/autowp/arduino-canhacker)
   - **Example**: [usb_cdc.ino](https://github.com/autowp/arduino-canhacker/blob/master/examples/usb_cdc/usb_cdc/usb_cdc.ino)

3. **Default pin configuration:**
   - CS = Pin 10
   - INT = Pin 2
   - MOSI, MISO, SCK = Arduino's default SPI pins

### Usage

**1. Upload Code**

1. Connect Arduino to computer via USB
2. Open sketch in Arduino IDE
3. Select board: **Tools** → **Board** → **Arduino Uno**
4. Select port: **Tools** → **Port** → `/dev/tty.usbmodemXXXXXX`
5. Click **Upload** (Ctrl+U)

**2. Verify Connection**

Open Serial Monitor (Ctrl+Shift+M):
- **Baud rate**: 115200
- **Line ending**: Carriage return

Type `V` and press Enter. You should see:
```
V1013
```
(Hardware and firmware version)

**3. Configure in CAN Analyzer**

1. Open **CAN Analyzer**
2. Go to **Settings** (Ctrl+,)
3. Configure:
   - **CAN Device**: `/dev/tty.usbmodemXXXXXX` (your Arduino port)
   - **COM Baudrate**: `115200 bit/s`
   - **CAN Baudrate**: `500K` (or your bus speed)
   - **Simulation Mode**: Uncheck
4. Click **OK**
5. Click **Connect**

Done! Your Arduino now works as a professional CAN interface!

### Testing

**Test 1: Verify Serial Communication**

```bash
# macOS/Linux
screen /dev/tty.usbmodemXXXXXX 115200

# Type commands:
V       # View version
S6      # Configure 500 Kbps
O       # Open channel
C       # Close channel
```

**Test 2: Send CAN Message**

In Serial Monitor:
```
S6              # Configure 500 Kbps
O               # Open channel
t1234567890A    # Send: ID=0x123, DLC=4, Data=0x56 0x78 0x90 0xA0
```

**Test 3: Receive Messages**

With channel open (`O`), received messages appear automatically:
```
t1234567890A
t2805BB8E000029FA2929
```

---

## Protocol Reference

### CanHacker/Lawicel SLCAN Protocol

The Arduino implements the **Lawicel SLCAN** protocol, used by CanHacker, USBtin, LAWICEL CANUSB, and other devices.

### Main Commands

| Command | Description | Example | Response |
|---------|-------------|---------|----------|
| `Sn` | Set bitrate | `S6` (500 Kbps) | `\r` (CR) |
| `O` | Open channel (normal mode) | `O` | `\r` |
| `L` | Open channel (listen-only) | `L` | `\r` |
| `C` | Close channel | `C` | `\r` |
| `V` | View hardware/firmware version | `V` | `Vhhff\r` |
| `N` | View serial number | `N` | `Nxxxx\r` |
| `Zv` | Toggle timestamp | `Z1` | `\r` |

### Sending Messages

**Standard Frame (11-bit ID):**
```
tIIILDDDDDDDDDDDDDDDD[CR]

Example:
t1234567890A    # ID=0x123, DLC=4, Data=0x56 0x78 0x90 0xA0
```

**Extended Frame (29-bit ID):**
```
TiiiiiiiiLDDDDDDDDDDDDDDDD[CR]

Example:
T000012345812345678    # ID=0x00001234, DLC=5, Data=0x12 0x34 0x56 0x78
```

**Remote Frame (Standard):**
```
rIIIL[CR]

Example:
r1234    # ID=0x123, DLC=4 (request 4 bytes)
```

**Remote Frame (Extended):**
```
RiiiiiiiiL[CR]

Example:
R000012345    # ID=0x00001234, DLC=5
```

### Receiving Messages

Received messages are sent automatically in the same format:

```
t1234567890A              # Standard frame received
T000012345812345678       # Extended frame received
r1234                     # Remote frame standard
R000012345                # Remote frame extended
```

With timestamp enabled (`Z1`):
```
t12345678901234           # Timestamp: 0x1234 (last 4 digits)
```

### Bitrate Codes

| Code | Bitrate | Common Use |
|------|---------|------------|
| `S0` | 10 Kbps | Slow industrial networks |
| `S1` | 20 Kbps | - |
| `S2` | 50 Kbps | - |
| `S3` | 100 Kbps | - |
| `S4` | 125 Kbps | Automotive (CAN Low Speed) |
| `S5` | 250 Kbps | Automotive, Industrial |
| `S6` | 500 Kbps | **Automotive (standard)** |
| `S7` | 800 Kbps | - |
| `S8` | 1 Mbps | Automotive (CAN High Speed) |

### Acceptance Filters

```
Mxxxxxxxx    # Set acceptance code (hex)
mxxxxxxxx    # Set acceptance mask (hex)

Example:
M00000000    # Accept all (default)
mFFFFFFFF    # Full mask
```

**How they work:**
- **Acceptance Code**: ID you want to accept
- **Acceptance Mask**: Bits that must match (1 = must match, 0 = ignore)

Example - accept only ID 0x123:
```
M00000123    # Code = 0x123
m000007FF    # Mask = 0x7FF (all standard ID bits)
```

---

## Troubleshooting

### Arduino Not Responding

1. Verify code uploaded correctly
2. Confirm baudrate 115200 in Serial Monitor
3. Test with `V` command - should return version
4. Check SPI connections (MOSI, MISO, SCK, CS)

### "CAN init fail" Error

1. Verify MCP2515 connections:
   - VCC → 5V
   - GND → GND
   - CS → Pin 10
   - INT → Pin 2
2. Confirm MCP2515 module is powered (LED on)
3. Check if MCP2515 crystal is 8MHz or 16MHz
4. Adjust frequency in code if needed

### No Messages Appearing

1. Verify bus termination (120Ω at each end)
2. Confirm CAN-H and CAN-L connected correctly
3. Test with `L` command (listen-only) to rule out ACK issues
4. Use multimeter: should read ~2.5V between CAN-H and CAN-L at rest

### Corrupted Messages

1. Check CAN cable quality
2. Reduce cable length (max 40m @ 1Mbps)
3. Add proper termination (120Ω)
4. Check electrical interference
5. Test with lower bitrate (S6 → S5 → S4)

### Device Not Appearing in CAN Analyzer

1. Check Arduino connected: `ls /dev/tty.*`
2. Confirm not open in another program (Serial Monitor, etc.)
3. Grant permissions: `sudo chmod 666 /dev/tty.usbmodem*`
4. Reset Arduino (reset button)

---

## Use Cases

### Case 1: Development and Testing

**Scenario:** Developing a CAN device and need to test communication.

**Setup:**
1. **Arduino 1** with CanHacker firmware → PC interface
2. **Arduino 2** with message generator → Simulate your device
3. **CAN Analyzer** on PC → Monitor and send messages

**Advantages:**
- Low cost (~$20 total)
- Easy to configure
- Fully customizable

### Case 2: Automotive Bus Analysis

**Scenario:** Analyze CAN messages from your car.

**Setup:**
1. Arduino with CanHacker firmware
2. Connect to vehicle's OBD-II (via OBD-CAN adapter)
3. CAN Analyzer on laptop

**Advantages:**
- Cheaper than professional adapters
- Open protocol
- Works with multiple software tools

### Case 3: Education and Learning

**Scenario:** Learning about CAN bus.

**Setup:**
1. 2x Arduino with MCP2515
2. One with CanHacker firmware (interface)
3. Other with message generator
4. CAN Analyzer to visualize

**Advantages:**
- Understand protocol in practice
- Open-source code to study
- Low cost for experimentation

---

## Comparison: Arduino vs Commercial Adapters

| Feature | Arduino + MCP2515 | USBtin | PEAK PCAN-USB | Vector CANcase |
|---------|-------------------|--------|---------------|----------------|
| **Price** | ~$10 | ~$50 | ~$100 | ~$500+ |
| **Protocol** | CanHacker/Lawicel | CanHacker/Lawicel | Proprietary | Proprietary |
| **Open-source** | Yes | No | No | No |
| **Customizable** | Yes | No | No | No |
| **Max Bitrate** | 1 Mbps | 1 Mbps | 1 Mbps | 1 Mbps |
| **Drivers** | Not needed | Not needed | Required | Required |
| **SW Support** | Broad (Lawicel) | Broad (Lawicel) | Specific | Specific |

**Conclusion:** For general use and learning, Arduino is an excellent choice!

---

## References

### Official Documentation

- **CanHacker Protocol**: https://github.com/autowp/arduino-canhacker/blob/master/docs/en/protocol.md
- **Arduino Library**: https://github.com/autowp/arduino-canhacker
- **MCP2515 Library**: https://github.com/autowp/arduino-mcp2515

### Original Lawicel Protocol

- **LAWICEL CANUSB**: http://www.can232.com/docs/canusb_manual.pdf
- **CanHacker for Windows**: http://www.mictronics.de/projects/usb-can-bus/


