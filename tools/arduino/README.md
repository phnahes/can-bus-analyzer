# Arduino CAN Tools

Arduino sketches for CAN message generation, reception, OBD-II simulation, and using the board as a Lawicel SLCAN interface.

---

## Contents

- [Sketches Overview](#sketches-overview)
- [Upload via Command Line](#upload-via-command-line)
- [Arduino as SLCAN Interface](#arduino-as-slcan-interface)
- [Hardware & Wiring](#hardware--wiring)
- [Libraries](#libraries)
- [Lawicel SLCAN Protocol Reference](#lawicel-slcan-protocol-reference)
- [Troubleshooting](#troubleshooting)
- [Use Cases & Comparison](#use-cases--comparison)

---

## Sketches Overview

### `arduino_msg_generator.ino`

Configurable CAN message generator for testing reception.

**Features:**
- Standard (11-bit) or Extended (29-bit) IDs
- Fixed or random IDs within a range
- Configurable data length (0–8 bytes or random)
- Configurable period (fixed or random)
- Custom or random data content
- Predefined message groups (simulate multiple ECUs)
- Remote Frame support
- Individual period control per message

**Hardware:** Arduino (Uno, Mega, etc.) + MCP2515. Connections: CS=Pin 10, INT=Pin 2.

**Configuration example (fixed periodic message):**
```cpp
#define USE_STANDARD_ID    true
#define USE_SPECIFIC_ID    true
#define SPECIFIC_ID        0x123
#define DATA_LENGTH        8
#define DELAY_MS           100
#define USE_CUSTOM_DATA    true
#define CUSTOM_DATA        {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88}
```

**Configuration example (message group - simulate ECU):**
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

**Library:** Seeed CAN-BUS Shield Library (Library Manager → "CAN-BUS Shield"). Use `#define CAN_2515` for MCP2515.

---

### `arduino_msg_receiver.ino`

CAN message receiver for testing transmission.

**Features:**
- Receives Standard and Extended CAN messages
- Displays ID, type, length, data
- Real-time statistics (count, message rate)
- Optional ID filtering
- Timestamp and Remote Frame detection

**Configuration:**
```cpp
#define SHOW_TIMESTAMP     true
#define SHOW_STATISTICS    true
#define STATS_INTERVAL     5000
#define USE_FILTER         false
#define FILTER_ID          0x100
#define FILTER_MASK        0x7FF
```

**Output format:**
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

### `arduino_obd2_ecu_simulator.ino`

OBD-II ECU simulator – responds to OBD-II requests with realistic simulated data.

**Hardware:** Arduino + MCP2515 (Seeed or compatible). **Library:** Seeed Arduino CAN (Manage Libraries → "Seeed Arduino CAN").

**Features:**
- Simulates full OBD-II ECU
- Service 01: standard PIDs (RPM, speed, temperatures, throttle, MAF, fuel level, etc.)
- Service 03: simulated DTCs (e.g. P0171, P0300, C0035, B1234)
- Animated, realistic values (RPM 800–3000, speed, temperatures, battery voltage)
- Serial debug output
- Compatible with CAN Analyzer OBD-II Monitor

**Supported PIDs (examples):** 0x00, 0x04, 0x05, 0x0C, 0x0D, 0x0F, 0x10, 0x11, 0x2F, 0x42, 0x46, 0x5C.

**Supported Services:**
- **Service 01 (Show current data):** Returns real-time sensor values
- **Service 03 (Show stored DTCs):** Returns 4 simulated DTCs:
  - P0171 - System Too Lean (Bank 1)
  - P0300 - Random/Multiple Cylinder Misfire Detected
  - C0035 - Left Front Wheel Speed Sensor Circuit
  - B1234 - Generic Body Code

**Usage:**
1. Install Seeed Arduino CAN, connect MCP2515, upload sketch.
2. Set CAN to 500 kbps; connect to bus.
3. In CAN Analyzer → OBD-II Monitor, select PIDs and start polling; use "Read DTCs" to test Service 03.

**Config:** `SPI_CS_PIN` (default 9), `DEBUG_MODE` for Serial output.

---

### `arduino_usb_cdc.ino`

Reference for USB CDC (serial) usage with SLCAN. Use the official SLCAN/Lawicel example from the library (e.g. **File → Examples → SLCAN → usb_cdc**). Default pins: CS=10, INT=2, standard SPI.

---

## Upload via Command Line

You can upload Arduino sketches without the IDE using **arduino-cli** (recommended) or **avrdude** directly.

### Method 1: arduino-cli (Recommended)

**Installation:**

**macOS:**
```bash
brew install arduino-cli
```

**Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
```

**Windows:**
Download from: https://arduino.github.io/arduino-cli/

**Initial Setup:**
```bash
# Initialize configuration
arduino-cli config init

# Update core index
arduino-cli core update-index

# Install Arduino AVR core (for Uno, Mega, Nano)
arduino-cli core install arduino:avr

# List connected boards
arduino-cli board list
```

**Install Required Libraries:**
```bash
# For message generator and receiver
arduino-cli lib install "CAN-BUS Shield"

# For OBD-II simulator
arduino-cli lib install "Arduino CAN"

# For SLCAN interface
arduino-cli lib install "MCP2515 by autowp"
```

**Upload Sketches:**

**1. Upload Message Generator:**
```bash
# Compile
arduino-cli compile --fqbn arduino:avr:uno arduino_msg_generator.ino

# Upload (replace /dev/ttyACM0 with your port)
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino_msg_generator.ino
```

**2. Upload Message Receiver:**
```bash
arduino-cli compile --fqbn arduino:avr:uno arduino_msg_receiver.ino
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino_msg_receiver.ino
```

**3. Upload OBD-II Simulator:**
```bash
arduino-cli compile --fqbn arduino:avr:uno arduino_obd2_ecu_simulator.ino
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino_obd2_ecu_simulator.ino
```

**Find Your Port:**
```bash
# macOS
ls /dev/tty.usbmodem* /dev/tty.usbserial*

# Linux
ls /dev/ttyACM* /dev/ttyUSB*

# Or use arduino-cli
arduino-cli board list
```

**Common Board FQBNs:**
- Arduino Uno: `arduino:avr:uno`
- Arduino Mega 2560: `arduino:avr:mega:cpu=atmega2560`
- Arduino Nano: `arduino:avr:nano:cpu=atmega328`
- Arduino Nano (Old Bootloader): `arduino:avr:nano:cpu=atmega328old`

**One-Line Compile + Upload:**
```bash
arduino-cli compile --fqbn arduino:avr:uno arduino_msg_generator.ino && \
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino_msg_generator.ino
```

**Monitor Serial Output:**
```bash
# Using arduino-cli
arduino-cli monitor -p /dev/ttyACM0 -c baudrate=115200

# Using screen (exit: Ctrl+A then K then Y)
screen /dev/ttyACM0 115200

# Using minicom
minicom -D /dev/ttyACM0 -b 115200
```

---

### Method 2: avrdude (Advanced)

**Installation:**
```bash
# macOS
brew install avrdude

# Linux (Debian/Ubuntu)
sudo apt install avrdude

# Linux (Fedora)
sudo dnf install avrdude
```

**Upload (Arduino Uno example):**
```bash
# First compile with arduino-cli or IDE to get .hex file
arduino-cli compile --fqbn arduino:avr:uno arduino_msg_generator.ino

# Upload with avrdude
avrdude -v -patmega328p -carduino -P/dev/ttyACM0 -b115200 -D \
  -Uflash:w:arduino_msg_generator.ino.hex:i
```

**Common avrdude parameters:**
- `-p`: MCU type (`atmega328p` for Uno, `atmega2560` for Mega)
- `-c`: Programmer type (`arduino` for Uno/Nano, `wiring` for Mega)
- `-P`: Serial port
- `-b`: Baudrate (`115200` for Uno, `57600` for Mega)
- `-D`: Disable auto-erase (faster)

---

### Troubleshooting Upload

**Permission Denied:**
```bash
# Linux - add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and log back in

# Or temporary fix
sudo chmod 666 /dev/ttyACM0
```

**Port Not Found:**
```bash
# Check if Arduino is connected
lsusb  # Linux
system_profiler SPUSBDataType  # macOS

# Reset Arduino (press reset button)
# Try different USB cable/port
```

**Upload Failed / Sync Error:**
```bash
# Press and hold reset button
# Start upload
# Release reset when "Uploading..." appears

# Or try different baudrate
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno:upload_speed=57600 sketch.ino
```

**Library Not Found:**
```bash
# Search for library
arduino-cli lib search "CAN"

# Install specific version
arduino-cli lib install "Arduino CAN@2.3.3"

# List installed libraries
arduino-cli lib list
```

---

## Arduino as SLCAN Interface

You can use **Arduino + MCP2515** as a Lawicel SLCAN-compatible interface for the CAN Analyzer and other tools (e.g. python-can).

### Advantages

- **Low cost**: Arduino + MCP2515 costs ~$10 (vs $50-100 for commercial adapters)
- **Standard protocol**: Compatible with python-can and other SLCAN tools
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

### Library Installation

**Method 1: Arduino Library Manager (Recommended)**

1. Open Arduino IDE
2. Go to **Sketch** → **Include Library** → **Manage Libraries...**
3. Search for **"SLCAN"** or **"Lawicel"**
4. Install a library that implements the Lawicel SLCAN protocol (e.g. by autowp)
5. Also install **"MCP2515 by autowp"** (dependency)

**Method 2: Manual**

```bash
cd ~/Documents/Arduino/libraries/
git clone https://github.com/autowp/arduino-mcp2515.git
git clone https://github.com/autowp/arduino-canhacker.git
```

**Method 3: arduino-cli**

```bash
arduino-cli lib install "MCP2515 by autowp"
# Note: SLCAN library may need manual installation from GitHub
```

### Arduino Code

**Use the official example from the SLCAN/Lawicel library:**

1. **Open example in Arduino IDE:**
   - **File** → **Examples** → **SLCAN** (or Lawicel) → **usb_cdc**

2. **Or access directly:**
   - **Repository**: [arduino-canhacker](https://github.com/autowp/arduino-canhacker)
   - **Example**: [usb_cdc.ino](https://github.com/autowp/arduino-canhacker/blob/master/examples/usb_cdc/usb_cdc/usb_cdc.ino)

3. **Default pin configuration:**
   - CS = Pin 10
   - INT = Pin 2
   - MOSI, MISO, SCK = Arduino's default SPI pins

### Usage

**1. Upload Code**

**Via Arduino IDE:**
1. Connect Arduino to computer via USB
2. Open sketch in Arduino IDE
3. Select board: **Tools** → **Board** → **Arduino Uno**
4. Select port: **Tools** → **Port** → `/dev/tty.usbmodemXXXXXX`
5. Click **Upload** (Ctrl+U)

**Via arduino-cli:**
```bash
arduino-cli compile --fqbn arduino:avr:uno usb_cdc.ino
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno usb_cdc.ino
```

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

## Hardware & Wiring

### MCP2515 → Arduino

| MCP2515 | Arduino Uno/Nano | Arduino Mega |
|---------|------------------|--------------|
| VCC     | 5V               | 5V           |
| GND     | GND              | GND          |
| CS      | Pin 10           | Pin 10 (or 53) |
| SO (MISO) | Pin 12        | Pin 50       |
| SI (MOSI) | Pin 11        | Pin 51       |
| SCK     | Pin 13           | Pin 52       |
| INT     | Pin 2            | Pin 2        |

### CAN Bus Connection

| MCP2515 | CAN Bus |
|---------|---------|
| CANH    | CAN-H   |
| CANL    | CAN-L   |

**Important:** Add 120Ω termination resistors between CAN-H and CAN-L at **both ends** of the CAN bus.

---

## Libraries

### For Message Generator, Receiver

**Seeed CAN-BUS Shield Library**
- Arduino IDE: **Manage Libraries** → Search **"CAN-BUS Shield"**
- GitHub: https://github.com/Seeed-Studio/CAN_BUS_Shield
- Configure shield type: `#define CAN_2515` for MCP2515

### For OBD-II Simulator

**Seeed Arduino CAN**
- Arduino IDE: **Manage Libraries** → Search **"Seeed Arduino CAN"**
- GitHub: https://github.com/Seeed-Studio/Seeed_Arduino_CAN
- PlatformIO: `lib_deps = seeed-studio/Seeed Arduino CAN@^2.3.3`

### For SLCAN Interface

**arduino-canhacker + arduino-mcp2515**
- GitHub: https://github.com/autowp/arduino-canhacker
- GitHub: https://github.com/autowp/arduino-mcp2515
- Manual installation or via Library Manager

---

## Lawicel SLCAN Protocol Reference

The Arduino implements the **Lawicel SLCAN** protocol, used by USBtin, LAWICEL CANUSB, and other devices.

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
5. Try different USB cable/port
6. Reset Arduino (press reset button)

### "CAN init fail" Error

1. Verify MCP2515 connections:
   - VCC → 5V
   - GND → GND
   - CS → Pin 10
   - INT → Pin 2
2. Confirm MCP2515 module is powered (LED on)
3. Check if MCP2515 crystal is 8MHz or 16MHz
4. Adjust frequency in code if needed:
   ```cpp
   CAN.begin(CAN_500KBPS, MCP_8MHz);  // or MCP_16MHz
   ```

### No Messages Appearing

1. Verify bus termination (120Ω at each end)
2. Confirm CAN-H and CAN-L connected correctly
3. Test with `L` command (listen-only) to rule out ACK issues
4. Use multimeter: should read ~2.5V between CAN-H and CAN-L at rest
5. Check if other device on bus is transmitting
6. Verify correct baudrate on all devices

### Corrupted Messages

1. Check CAN cable quality
2. Reduce cable length (max 40m @ 1Mbps)
3. Add proper termination (120Ω at both ends)
4. Check electrical interference
5. Test with lower bitrate (S6 → S5 → S4)
6. Ensure good ground connection

### Device Not Appearing in CAN Analyzer

1. Check Arduino connected: `ls /dev/tty.*` (macOS) or `ls /dev/ttyACM*` (Linux)
2. Confirm not open in another program (Serial Monitor, etc.)
3. Grant permissions: `sudo chmod 666 /dev/tty.usbmodem*`
4. Reset Arduino (reset button)
5. Try different USB port
6. Check USB cable (some are power-only)

### OBD-II Simulator Not Responding

1. Verify CAN bus speed is 500 kbps (OBD-II standard)
2. Check CS pin configuration in sketch (default: Pin 9)
3. Enable DEBUG_MODE and check Serial Monitor at 115200 baud
4. Verify MCP2515 initialization successful
5. Test with simple message generator first
6. Check termination resistors

### Upload Errors (arduino-cli)

**"Error opening serial port":**
```bash
# Linux - add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and log back in
```

**"Board not found":**
```bash
# Update board list
arduino-cli board list

# Install core if missing
arduino-cli core install arduino:avr
```

**"Library not found":**
```bash
# Search for library
arduino-cli lib search "library name"

# Install library
arduino-cli lib install "Library Name"
```

---

## Use Cases & Comparison

### Use Case 1: Development and Testing

**Scenario:** Developing a CAN device and need to test communication.

**Setup:**
1. **Arduino 1** with SLCAN firmware → PC interface
2. **Arduino 2** with message generator → Simulate your device
3. **CAN Analyzer** on PC → Monitor and send messages

**Advantages:**
- Low cost (~$20 total)
- Easy to configure
- Fully customizable

### Use Case 2: Automotive Bus Analysis

**Scenario:** Analyze CAN messages from your car.

**Setup:**
1. Arduino with SLCAN firmware
2. Connect to vehicle's OBD-II (via OBD-CAN adapter)
3. CAN Analyzer on laptop

**Advantages:**
- Cheaper than professional adapters
- Open protocol
- Works with multiple software tools

### Use Case 3: Education and Learning

**Scenario:** Learning about CAN bus.

**Setup:**
1. 2x Arduino with MCP2515
2. One with SLCAN firmware (interface)
3. Other with message generator
4. CAN Analyzer to visualize

**Advantages:**
- Understand protocol in practice
- Open-source code to study
- Low cost for experimentation

### Use Case 4: OBD-II Development

**Scenario:** Developing OBD-II diagnostic tools.

**Setup:**
1. Arduino with OBD-II simulator
2. Arduino with SLCAN firmware
3. CAN Analyzer with OBD-II Monitor

**Advantages:**
- No need for real vehicle
- Controlled test environment
- Simulate various scenarios and DTCs

---

## Comparison: Arduino vs Commercial Adapters

| Feature | Arduino + MCP2515 | USBtin | PEAK PCAN-USB | Vector CANcase |
|---------|-------------------|--------|---------------|----------------|
| **Price** | ~$10 | ~$50 | ~$100 | ~$500+ |
| **Protocol** | Lawicel SLCAN | Lawicel SLCAN | Proprietary | Proprietary |
| **Open-source** | Yes | No | No | No |
| **Customizable** | Yes | No | No | No |
| **Max Bitrate** | 1 Mbps | 1 Mbps | 1 Mbps | 1 Mbps |
| **Drivers** | Not needed | Not needed | Required | Required |
| **SW Support** | Broad (Lawicel) | Broad (Lawicel) | Specific | Specific |

**Conclusion:** For general use, learning, and development, Arduino is an excellent choice!

---

## References

### Official Documentation

- **Lawicel SLCAN Protocol**: https://github.com/autowp/arduino-canhacker/blob/master/docs/en/protocol.md
- **Arduino SLCAN Library**: https://github.com/autowp/arduino-canhacker
- **MCP2515 Library**: https://github.com/autowp/arduino-mcp2515
- **Seeed Arduino CAN**: https://github.com/Seeed-Studio/Seeed_Arduino_CAN
- **arduino-cli**: https://arduino.github.io/arduino-cli/

### Original Lawicel Protocol

- **LAWICEL CANUSB**: http://www.can232.com/docs/canusb_manual.pdf

### Related

- **CAN Analyzer**: `../../README.md`
- **General tools (send_can_message.py, etc.)**: `../general/README.md`
- **FTCAN tools**: `../ftcan/README.md`
- **MCP2515 datasheet**: https://www.microchip.com/en-us/product/MCP2515
