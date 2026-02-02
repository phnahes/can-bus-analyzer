## Tools

The `tools/` folder contains ready-to-use code for testing and interfacing with CAN devices:

### Available Tools

#### **Python Tools**

**`send_can_message.py`** - Python CAN message sender
- Direct serial communication with Lawicel SLCAN devices
- No external dependencies (only pyserial)
- Automatically cycles through 7 test messages
- Listen-only mode available
- Monitors responses between messages
- Native protocol implementation

```bash
# Cycle through messages automatically
python3 tools/send_can_message.py

# Listen-only mode (receive only)
python3 tools/send_can_message.py --listen --debug
```

#### **Arduino Tools**

**`arduino_msg_generator.ino`** - Configurable CAN message generator
- Standard (11-bit) or Extended (29-bit) IDs
- Fixed or random IDs, data, and periods
- Group messaging mode (simulate multiple ECUs)
- Individual period control per message
- Perfect for testing reception

**`arduino_msg_receiver.ino`** - CAN message receiver (only)
- Receives and displays all CAN messages
- Shows ID, type, data, and statistics
- Optional ID filtering
- Perfect for testing transmission

### Using Arduino as CAN Interface

You can use an **Arduino with MCP2515** as a low-cost CAN interface using the **Lawicel SLCAN protocol**:

**Hardware Setup:**
- Arduino Uno/Nano/Mega
- MCP2515 CAN module
- Connections: CS=Pin 10 (or 9, it depends on board), INT=Pin 2

**Software Setup:**

1. **Install an Arduino library that implements Lawicel SLCAN:**
   - Arduino IDE → **Sketch** → **Include Library** → **Manage Libraries...**
   - Search for **"SLCAN"** or **"Lawicel"**
   - Install a library that implements the Lawicel SLCAN protocol (e.g. by autowp)
   - Also install **"MCP2515 by autowp"** (dependency)

2. **Use the official example:**
   - **Library Repository**: [arduino SLCAN library](https://github.com/autowp/arduino-canhacker/tree/master)
   - **Example Code**: [usb_cdc.ino](https://github.com/autowp/arduino-canhacker/blob/master/examples/usb_cdc/usb_cdc/usb_cdc.ino)
   - Open the example in Arduino IDE: **File** → **Examples** → **SLCAN** (or Lawicel) → **usb_cdc**

3. **Upload to Arduino:**
   - Select your board: **Tools** → **Board** → **Arduino Uno** (or your board)
   - Select the port: **Tools** → **Port** → `/dev/tty.usbmodemXXXXXX`
   - Click **Upload** (Ctrl+U)

**Usage in CAN Analyzer:**
1. Connect Arduino to computer via USB
2. Open CAN Analyzer Settings (Ctrl+,):
   - **Device**: `/dev/tty.usbmodemXXXXXX` (your Arduino port)
   - **COM Baudrate**: 115200 bps
   - **CAN Baudrate**: 500K (or your network speed)
3. Click **Connect** and use normally!

**Advantages:**
- **Low-cost** - Arduino + MCP2515 module (~$10 total)
- **Compatible** - Works with python-can and other SLCAN tools
- **Open-source** - Fully customizable and documented
- **No drivers** - Uses standard USB serial (CDC)


### Protocol Reference

The Arduino SLCAN implementation follows the **Lawicel SLCAN protocol**:

- **Protocol Documentation**: [Lawicel SLCAN Protocol](https://github.com/autowp/arduino-canhacker/blob/master/docs/en/protocol.md)
- **Library Repository**: [arduino SLCAN library](https://github.com/autowp/arduino-canhacker)

**Key Commands:**
- `Sn` - Set bitrate (S6 = 500 Kbps)
- `O` - Open channel (normal mode)
- `L` - Listen only mode
- `C` - Close channel
- `tIIILDD...` - Transmit standard frame
- `TiiiiiiiiLDD...` - Transmit extended frame

### Quick Test Setup

**Option 1: Arduino Generator + CAN Analyzer**
1. Upload `arduino_msg_generator.ino` to Arduino
2. Connect Arduino to CAN bus
3. Open CAN Analyzer and connect
4. Watch messages appear in real-time

**Option 2: CAN Analyzer TX + Arduino Receiver**
1. Upload `arduino_msg_receiver.ino` to Arduino
2. Connect Arduino to CAN bus
3. Send messages from CAN Analyzer
4. Watch Arduino Serial Monitor for received messages

**Option 3: Arduino as CAN Interface**
1. Upload the SLCAN (usb_cdc) example to Arduino
2. Use Arduino as your CAN adapter
3. No separate CAN adapter needed!

**See `tools/README.md` for detailed instructions, wiring diagrams, and configuration options.**
