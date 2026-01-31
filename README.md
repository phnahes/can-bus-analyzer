# CAN Analyzer

Professional CAN bus analyzer with CANHacker-like functionality. Built with Python and PyQt6. **Runs on macOS and Linux.**

## Multi-Language Support

The application supports 5 languages:
- English
- Português  
- Español
- Deutsch
- Français

**Change language:** Settings → Language → Select your language → Restart application

---

## Quick Start

**macOS / Linux:**
```bash
./run.sh
```

Or run manually:
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python can_analyzer_qt.py
```

---

## Supported Operating Systems

| OS        | Status   | Notes |
|----------|----------|--------|
| **macOS**  | ✅ Supported | Use `/dev/cu.usbserial*` or `/dev/cu.usbmodem*`. Packaged with **py2app**. |
| **Linux**  | ✅ Supported | Use `/dev/ttyUSB*`, `/dev/ttyACM*`, or SocketCAN (`can0`, `vcan0`). Packaged with **PyInstaller**. |

- **PyQt6**, **python-can**, and **pyserial** are cross-platform.
- Device detection uses `pyserial` list_ports on all platforms.
- Serial (SLCAN) and SocketCAN interfaces are auto-detected from the channel name.

---

## Requirements

### Runtime Dependencies (included in packaged app)
- **Python 3.9+**
- **python-can** >= 4.3.1
- **pyserial** >= 3.5
- **PyQt6** >= 6.6.0

### Development Dependencies (only for building)
- **py2app** >= 0.28.8 (macOS)
- **PyInstaller** >= 6.0.0 (Linux)
- **Pillow** >= 10.0.0 (for icon generation)

### System Requirements
- **macOS**: 10.14+ (for running from source) or any recent version (for .app bundle)
- **Linux**: Modern distribution with Python 3.9+ and Qt/GUI support

---

## Packaging (Build standalone executable)

You can build a standalone package so users don't need Python installed.

### Requirements

- **py2app** for macOS (included in `requirements.txt`)
- **PyInstaller** for Linux (included in `requirements.txt`)
- Same OS as the target: build on macOS for macOS, on Linux for Linux

### Quick build

**macOS / Linux:**
```bash
# Activate venv (optional)
source venv/bin/activate

# Install dependencies (runtime + build tools)
pip install -r requirements-dev.txt

# Build
./build.sh
```

**Note:** Use `requirements-dev.txt` for building (includes py2app/PyInstaller). Use `requirements.txt` only for running from source.

### Output

| OS      | Build tool | Output                           |
|---------|------------|----------------------------------|
| **macOS**  | py2app     | `dist/CAN Analyzer.app`          |
| **Linux**  | PyInstaller| `dist/CAN Analyzer/CAN Analyzer` |

### Files

- **`setup.py`** – py2app configuration for macOS
- **`can_analyzer.spec`** – PyInstaller spec for Linux
- **`build.sh`** – Build script (auto-detects platform)
- **`create_icon.sh`** – Icon generation script
- **`requirements.txt`** – Runtime dependencies (included in app)
- **`requirements-dev.txt`** – Build tools (NOT included in app)

### Config and logs when packaged

- **config.json** and **logs/** are created in the **current working directory** when you run the app.
- For a fixed location (e.g. user config dir), you can adapt the app to use a path based on `sys.executable` when running frozen.

### Changing the App Icon

To use a custom icon:

1. **Create or download a PNG** (recommended: 1024x1024 or larger)
   - Example: `my_custom_icon.png`

2. **Generate icon files**:
   ```bash
   ./create_icon.sh my_custom_icon.png
   ```
   This creates:
   - `icon.icns` (macOS)
   - `icon.ico` (Linux)

3. **Rebuild the app**:
   ```bash
   ./build.sh
   ```

The build script automatically detects and uses `icon.icns` (macOS) or `icon.ico` (Linux) if present.

**See `ICONS.md` for detailed instructions on creating icons, recommended tools, and design tips.**

### macOS: Single .app (not folder + .app)

The build script now generates **only** `CAN Analyzer.app` on macOS (the intermediate folder is automatically cleaned up). You'll get:
- ✅ `dist/CAN Analyzer.app` (ready to use)
- ❌ No extra `dist/CAN Analyzer/` folder

To run: `open "dist/CAN Analyzer.app"`

---

## Dependencies

- **PyQt6** - Modern native GUI framework
- **python-can** - CAN bus communication library
- **pyserial** - Serial communication with USB adapters

---

## Features

### Core Features

#### **Interface & Visualization**
- Native GUI with PyQt6 (no Tk/Tcl dependency)
- **Monitor Mode**: Groups messages by ID with counter
- **Tracer Mode**: Chronological list of all messages
- Modern and responsive interface
- Real-time mode switching (Monitor ↔ Tracer)

#### **Message Reception**
- Reception panel with: ID, DLC, Data, Period, Count, ASCII, Comment
- **Monitor Mode**: Groups by ID, shows Count (first column), Period (ms between messages)
- **Tracer Mode**: Chronological list with timestamps
- **Visual Feedback**:
  - Monitor Mode: Only Count cell highlighted in light blue when updated
  - Tracer Mode: No highlighting (messages flow naturally)
- Automatic scroll
- **Context menu (right-click)**:
  - Add to Transmit List
  - Copy ID
  - Copy Data
  - Bit Field Viewer
  - Supports multiple selection (Ctrl/Cmd + Click)

#### **Message Transmission**
- Complete CAN message configuration
- Support for 11 and 29-bit IDs
- RTR (Remote Transmission Request)
- Configurable transmission period
- TX Mode: off, on, trigger
- Trigger ID and Trigger Data for conditional transmission

#### **Controls & Settings**
- Controls: Connect, Disconnect, Reset, Record, Pause, Clear
- **Settings Dialog**:
  - **Language Selection** (5 languages)
  - CAN Device selection
  - COM Baudrate (9600 to 115200 bps)
  - CAN Baudrate (125K, 250K, 500K, 1000K)
  - RTS HS, Listen Only, Time Stamp
  - Baudrate Register (BRGCON/BTR)

#### **File Operations**
- **Save/Load Logs** (multiple formats):
  - JSON (with complete metadata)
  - CSV (Excel compatible)
  - TRC (Trace format, CANHacker compatible)
- **Save/Load Transmit List**:
  - Save TX configurations in JSON
  - Load pre-configured message lists
  - Option to merge or replace current list

#### **Advanced Features**
- **Bit Field Viewer**: Detailed bit-by-bit visualization
  - Color-coded bits (green=1, red=0)
  - Editable bit labels
  - Save/load label configurations
  - Byte-by-byte breakdown
- **Software Filters**: Message filtering by ID and data
  - Filter by single ID or ID range
  - Filter by data content with masks
  - Whitelist/blacklist modes
  - Enable/disable filters dynamically
- **Trigger-based TX**: Automatic transmission on received messages
  - Configure trigger ID and optional data
  - Automatic response transmission
  - Multiple triggers support
  - Enable/disable triggers dynamically
- **Playback**: Reproduce recorded traces
  - Play all messages
  - Play selected messages only
  - Stop playback
  - Maintains original timing

#### **Logging System**
- Comprehensive logging to file
- Automatic log rotation (10MB max, 5 backups)
- Logs all operations:
  - CAN messages (RX/TX)
  - Connection events
  - File operations
  - Filter actions
  - Trigger firings
  - Playback events
  - Exceptions with stack traces

#### **Status & Information**
- Real-time connection status
- Firmware information
- Filter status
- Message counter
- Mode indicator (Monitor/Tracer, Listen Only/Normal)

---

## Project Structure

```
CAN-Macos-Analyser/
├── can_analyzer_qt.py          # Application entry point
├── src/
│   ├── __init__.py
│   ├── main_window.py          # Main application window
│   ├── models.py               # Data models (CANMessage, etc.)
│   ├── dialogs_new.py          # Dialog windows (Settings, Filters, etc.)
│   ├── file_operations.py      # Save/load operations
│   ├── logger.py               # Logging system
│   ├── i18n.py                 # Internationalization (translations)
│   ├── utils.py                # Utility functions
│   └── can_interface.py        # CAN interface handling
├── logs/                       # Application logs
├── requirements.txt            # Python dependencies
├── run.sh                      # Quick start script
└── README.md                   # This file
```

---

## Internationalization (i18n)

### How It Works

The application uses a **lookup table system** for translations located in `src/i18n.py`.

### Supported Languages

| Language | Code | Status |
|----------|------|--------|
| English | `en` | Complete |
| Português | `pt` | Complete |
| Español | `es` | Complete |
| Deutsch | `de` | Complete |
| Français | `fr` | Complete |

### Changing Language

1. Open application
2. Go to **Settings** (Ctrl+,)
3. Select **Language** dropdown
4. Choose your preferred language
5. Click **OK**
6. **Interface updates immediately!**

**Note:** Most UI elements update instantly. Some dialogs may require reopening to see changes.

### Adding New Languages

Want to contribute a new language?

1. Edit `src/i18n.py`
2. Add your language code to `LANGUAGES` dict
3. Add translations for all keys in `TRANSLATIONS` dict
4. Test the application
5. Submit a pull request

**Example:**
```python
# In src/i18n.py
LANGUAGES = {
    'en': 'English',
    'pt': 'Português',
    'it': 'Italiano',  # New language
}

'app_title': {
    'en': 'CAN Analyzer - macOS',
    'pt': 'CAN Analyzer - macOS',
    'it': 'Analizzatore CAN - macOS',  # New translation
},
```

---

## Hardware Support

### Supported CAN Adapters

- USB-CAN adapters (via python-can SLCAN)
- Serial CAN adapters (via pyserial)
- SocketCAN (Linux)
- Virtual CAN (vcan) for testing

### USB / Serial Device Detection (Cross-Platform)

The application includes **automatic device detection** on all supported OSes:

- **Scan Devices** in Settings: Opens device selection dialog
- **Auto-detection**: Monitors USB/serial connections in real-time
- **Hot-swap support**: Automatically disconnects if device is removed
- **Simulation Mode**: Test without hardware

**Device paths by OS:**

| OS      | Serial (SLCAN) examples      | SocketCAN |
|---------|------------------------------|-----------|
| **macOS**  | `/dev/cu.usbserial*`, `/dev/cu.usbmodem*` | — |
| **Linux**  | `/dev/ttyUSB0`, `/dev/ttyACM0`           | `can0`, `vcan0` |

### Connection Settings

Configure in **Settings** dialog (Ctrl+,):

**Device Configuration:**
- **CAN Device**: Select your adapter (e.g., `/dev/tty.usbserial`, `can0`)
  - Click **Scan Devices** button to browse available USB devices
  - Automatically detects connected adapters
- **COM Baudrate**: Serial communication speed (default: 115200 bps)
- **CAN Baudrate**: CAN bus speed (125K, 250K, 500K, 1000K)

**Operating Modes:**
- **Listen Only**: Receive-only mode (no ACK transmission)
- **Simulation Mode**: Use simulated data instead of real hardware
  - Perfect for testing and development
  - No physical adapter required
  - Generates sample CAN messages

**Quick device selection:**
1. Open **Settings** (Ctrl+,)
2. Click **Scan Devices** button next to CAN Device field
3. Select your USB device from the list
4. Click **Select** to configure
5. Uncheck **Simulation Mode** to use real hardware
6. Click **OK** to save
7. Click **Connect** to start monitoring

### Simulation Mode

The application includes a **built-in simulation mode**:

**How to Enable:**
1. Open **Settings** (Ctrl+,)
2. Check **"Simulation Mode"**
3. Click **OK**
4. Click **Connect**

**Features:**
- Generates realistic CAN messages for testing
- All features available (filters, triggers, playback, etc.)
- Perfect for development and learning
- No physical hardware required
- Safe testing environment

**Automatic Fallback:**
- If connection to real device fails, app offers to use simulation mode
- Useful when device is disconnected or unavailable

---

## Usage Examples

### Basic Workflow

#### Using Real Hardware

1. **Configure Device**
   - Open **Settings** (Ctrl+,)
   - Click **Scan Devices** button
   - Select your CAN adapter from the list
   - **Uncheck "Simulation Mode"**
   - Click **OK**

2. **Connect to CAN bus**
   - Click **Connect** or press `Ctrl+O`
   - Connection establishes with selected device
   - Status shows "Connected"

3. **Monitor messages**
   - View incoming messages in **Receive** panel
   - Switch between Monitor/Tracer modes
   - Use filters to focus on specific IDs

4. **Send messages**
   - Configure message in **Transmit** panel
   - Click **Send** to transmit once
   - Or enable periodic transmission

5. **Save session**
   - File → Save Receive Log
   - Choose format (JSON, CSV, TRC)
   - Load later with File → Load Receive Log

6. **Disconnect**
   - Click **Disconnect** when done
   - Device can be safely removed

#### Using Simulation Mode (No Hardware)

1. **Enable Simulation**
   - Open **Settings** (Ctrl+,)
   - **Check "Simulation Mode"**
   - Click **OK**

2. **Connect**
   - Click **Connect**
   - Application generates sample CAN messages
   - Perfect for testing and learning

3. **Test Features**
   - All features work in simulation mode
   - Filters, triggers, playback, etc.
   - No physical hardware needed

### Advanced Features

#### **Bit Field Viewer**
1. Right-click on a message in Receive panel
2. Select **Bit Field Viewer**
3. View bit-by-bit breakdown
4. Add labels to bits for documentation
5. Save/load label configurations

#### **Software Filters**
1. Click **Filters** button or press `Ctrl+F`
2. Add ID filters (single or range)
3. Add data filters with masks
4. Choose whitelist or blacklist mode
5. Enable filters

#### **Trigger-based TX**
1. Tools → Triggers or press `Ctrl+G`
2. Add trigger: specify trigger ID and optional data
3. Configure response: TX ID and data
4. Enable triggers
5. Automatic transmission when trigger is received

#### **Playback**
1. Load a trace file (File → Load Receive Log)
2. Select messages to replay (or none for all)
3. Click **Play All** or **Play Selected**
4. Original timing is preserved
5. Click **Stop** to pause

---

## Configuration

### Configuration File

Settings are **automatically saved** to `config.json` in the application directory and persist across sessions:

**Location:** `/Users/paulonahes/Documents/git/CAN-Macos-Analyser/config.json`

**Format:**
```json
{
  "language": "en",
  "baudrate": 500000,
  "interface": "socketcan",
  "channel": "can0",
  "listen_only": true,
  "timestamp": true,
  "com_baudrate": "115200 bit/s",
  "rts_hs": false,
  "baudrate_reg": "FFFFFF"
}
```

**How it works:**
- Configuration is **automatically saved** when you click OK in Settings
- Configuration is **automatically loaded** on application startup
- Language preference persists across restarts
- All CAN settings persist across restarts

**Manual editing:**
You can manually edit `config.json` if needed (application must be closed).

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Connect | `Ctrl+O` |
| Reset | `Ctrl+R` |
| Save Receive Log | `Ctrl+S` |
| Load Receive Log | `Ctrl+L` |
| Save Transmit List | `Ctrl+Shift+S` |
| Load Transmit List | `Ctrl+Shift+L` |
| Clear Receive | `Ctrl+K` |
| Tracer Mode | `Ctrl+T` |
| Filters | `Ctrl+F` |
| Triggers | `Ctrl+G` |
| Settings | `Ctrl+,` |
| Exit | `Ctrl+Q` |

---

## Logging

### Log Files

Logs are saved in `logs/` directory:
```
logs/
├── can_analyzer_20260122.log       # Today's log
├── can_analyzer_20260122.log.1     # Backup 1
├── can_analyzer_20260122.log.2     # Backup 2
└── ...
```

### Log Rotation

- **Max size**: 10MB per file
- **Backups**: 5 files kept
- **Format**: `YYYY-MM-DD HH:MM:SS | LEVEL | MODULE | FUNCTION:LINE | MESSAGE`

### View Logs

```bash
# View real-time logs
tail -f logs/can_analyzer_$(date +%Y%m%d).log

# Search for errors
grep ERROR logs/*.log

# Search for CAN messages
grep "CAN RX\|CAN TX" logs/*.log
```

---

## Troubleshooting

### Application won't start

```bash
# Check Python version
python3 --version  # Should be 3.9+

# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### CAN adapter not detected

1. Check device connection: `ls /dev/tty.*`
2. Verify permissions: `sudo chmod 666 /dev/tty.usbserial*`
3. Try simulation mode (no hardware needed)

### Language not changing

1. Ensure you selected language in Settings
2. **Restart the application** (required for full effect)
3. Check logs for errors: `grep "language\|idioma" logs/*.log`

### Messages not appearing

1. Check connection status (should show "Connected")
2. Verify CAN baudrate matches your network
3. Check software filters (disable if enabled)
4. Try clearing and reconnecting

---

## Contributing

Contributions are welcome! Here's how you can help:

### Adding Translations

1. Edit `src/i18n.py`
2. Add your language to `LANGUAGES`
3. Translate all keys in `TRANSLATIONS`
4. Test thoroughly
5. Submit PR

### Reporting Bugs

1. Check existing issues
2. Provide detailed description
3. Include log files (`logs/`)
4. Specify macOS version and Python version

### Feature Requests

1. Open an issue
2. Describe the feature
3. Explain use case
4. Reference CANHacker if applicable

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

### What this means:

- **Freedom to use**: You can use this software for any purpose
- **Freedom to study**: You can study how the program works and modify it
- **Freedom to share**: You can redistribute copies of the software
- **Freedom to improve**: You can distribute modified versions

### Key terms:

- If you distribute this software, you must make the source code available
- Any modifications must also be licensed under GPL-3.0
- You must include the original copyright notice and license text
- There is NO WARRANTY for this software

**Full license text**: [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html)

---

## Acknowledgments

- **CANHacker** - Original inspiration and reference
- **python-can** - Excellent CAN library
- **PyQt6** - Modern GUI framework


---

## Related Projects

- [python-can](https://github.com/hardbyte/python-can) - Python CAN library
- [CANHacker](http://www.mictronics.de/projects/usb-can-bus/) - Original Windows tool
- [BUSMASTER](https://rbei-etas.github.io/busmaster/) - Open-source CAN tool

---

## Project Status

**Version**: 1.0.0  
**Status**: Active Development  
**Last Updated**: January 2026

### Implemented Features
- Monitor & Tracer modes
- Message transmission
- File operations (save/load)
- Bit field viewer
- Software filters
- Trigger-based TX
- Playback functionality
- Multi-language support (5 languages)
- Comprehensive logging
- USB device auto-detection
- Hot-swap device support

### Planned Features
- Hardware filters (28 configurable)
- CAN Bomber (spoofing tool)
- Gateway mode (bridge two channels)
- Statistics & analytics
- DBC file support
- Real-time plotting

---

## Examples & Testing

The `examples/` folder contains ready-to-use code for testing and interfacing with CAN devices:

### Available Examples

#### **Python Examples**

**`send_can_message.py`** - Python CAN message sender
- Direct serial communication with CanHacker/Lawicel devices
- No external dependencies (only pyserial)
- Automatically cycles through 7 test messages
- Listen-only mode available
- Monitors responses between messages
- Native protocol implementation

```bash
# Cycle through messages automatically
python3 examples/send_can_message.py

# Listen-only mode (receive only)
python3 examples/send_can_message.py --listen
```

#### **Arduino Examples**

**`arduino_msg_generator.ino`** - Configurable CAN message generator
- Standard (11-bit) or Extended (29-bit) IDs
- Fixed or random IDs, data, and periods
- Group messaging mode (simulate multiple ECUs)
- Individual period control per message
- Perfect for testing reception

**`arduino_msg_receiver.ino`** - CAN message receiver
- Receives and displays all CAN messages
- Shows ID, type, data, and statistics
- Optional ID filtering
- Perfect for testing transmission

### Using Arduino as CAN Interface

You can use an **Arduino with MCP2515** as a low-cost CAN interface using the **CanHacker protocol**:

**Hardware Setup:**
- Arduino Uno/Nano/Mega
- MCP2515 CAN module
- Connections: CS=Pin 10 (or 9, it depends), INT=Pin 2

**Software Setup:**

1. **Install the arduino-canhacker library:**
   - Arduino IDE → **Sketch** → **Include Library** → **Manage Libraries...**
   - Search for **"CanHacker"**
   - Install **"CanHacker by autowp"**
   - Also install **"MCP2515 by autowp"** (dependency)

2. **Use the official example:**
   - **Library Repository**: [arduino-canhacker](https://github.com/autowp/arduino-canhacker/tree/master)
   - **Example Code**: [usb_cdc.ino](https://github.com/autowp/arduino-canhacker/blob/master/examples/usb_cdc/usb_cdc/usb_cdc.ino)
   - Open the example in Arduino IDE: **File** → **Examples** → **CanHacker** → **usb_cdc**

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
- **Compatible** - Works with CanHacker, python-can, and other tools
- **Open-source** - Fully customizable and documented
- **No drivers** - Uses standard USB serial (CDC)
- **Professional protocol** - Implements Lawicel SLCAN standard

### Protocol Reference

The Arduino CanHacker implementation follows the **Lawicel SLCAN protocol**:

- **Protocol Documentation**: [CanHacker Protocol](https://github.com/autowp/arduino-canhacker/blob/master/docs/en/protocol.md)
- **Library Repository**: [arduino-canhacker](https://github.com/autowp/arduino-canhacker)

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
1. Upload `arduino_canhacker.ino` to Arduino
2. Use Arduino as your CAN adapter
3. No separate CAN adapter needed!

**See `examples/README.md` for detailed instructions, wiring diagrams, and configuration options.**

---

## Technical Notes

### CAN Protocol Implementation

The application uses `python-can` library which abstracts the CANHacker/Lawicel SLCAN protocol:

**Supported Interfaces:**
- **SLCAN** (Serial CAN): For USB-serial adapters implementing Lawicel protocol
- **SocketCAN**: Native Linux/macOS CAN interface
- **Virtual CAN**: For testing without hardware

**Why python-can?**
- Handles protocol complexity automatically
- Supports multiple CAN interfaces
- Cross-platform compatibility
- Active development and community support
- No need to implement low-level SLCAN commands manually

The application automatically detects the interface type based on the device path:
- `/dev/tty.*` or `/dev/cu.*` → SLCAN
- `can*` or `vcan*` → SocketCAN

---

