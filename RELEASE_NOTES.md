# CAN Analyzer v0.1.0 - Release Notes

## Initial Release

### What's New

First public release of CAN Analyzer - a professional CAN bus analysis tool with cross-platform support.

---

## Key Features

### Core Functionality
- **Real-time CAN Bus Analysis** - Monitor and analyze CAN messages in real-time
- **Dual View Modes**:
  - **Monitor Mode**: Groups messages by ID, shows latest value
  - **Tracer Mode**: Chronological list of all messages
- **Message Transmission** - Send individual or batch CAN messages
- **Periodic Transmission** - Auto-send messages at configurable intervals
- **Playback System** - Record and replay CAN message sequences

### Advanced Analysis Tools
- **Bit Field Viewer** - Detailed bit-level analysis with custom labels
- **Software Filters**:
  - ID-based filtering (supports ranges: 0x300-0x310)
  - Data content filtering with masks
  - Whitelist/Blacklist modes
- **Message Statistics** - Real-time counters and period calculation
- **Listen-Only Mode** - Monitor without transmitting

### File Operations
- **Multiple Format Support**:
  - JSON (native format with metadata)
  - CSV (Excel-compatible)
  - TRC (Vector format)
- **Save/Load**:
  - Receive logs (all captured messages)
  - Transmit lists (predefined messages)
  - Filter configurations
  - Bit field labels

### Multi-Language Support
- **5 Languages**: English, Português, Español, Deutsch, Français
- **Dynamic switching** - Change language without restart
- **Fully translated** - All UI elements, menus, and dialogs

### Cross-Platform
- **macOS** - Native .app bundle with py2app
- **Linux** - Standalone executable with PyInstaller
- **Universal Binary** - Supports both Intel and Apple Silicon (macOS)

### Modern UI/UX
- **Clean Interface** - Intuitive layout with organized menus
- **Keyboard Shortcuts** - Quick access to all functions
- **Status Bar Feedback** - Non-intrusive notifications
- **USB Device Detection** - Auto-scan for CAN adapters
- **Dark Mode Support** - Respects system theme

---

## Architecture

### Modular Design
```
src/
 main_window.py       # Main application window (3,366 lines)
 dialogs_new.py       # All dialogs (Settings, Filters, Bit Viewer)
 models.py            # Data models (CANMessage, CANConfig, etc.)
 file_operations.py   # Save/Load operations (JSON, CSV, TRC)
 can_interface.py     # CAN bus communication layer
 usb_device_monitor.py # USB device detection
 config_manager.py    # Configuration management
 i18n.py              # Internationalization system
 logger.py            # Logging system
 utils.py             # Utility functions
```

**Total**: ~6,500 lines of Python code

### Key Technologies
- **PyQt6** - Modern GUI framework
- **python-can** - CAN bus interface (supports 20+ adapters)
- **pyserial** - Serial communication (SLCAN protocol)
- **py2app** - macOS packaging
- **PyInstaller** - Linux packaging

---

## Supported Hardware

### CAN Adapters
- **USBtin** - USB-CAN adapter (Lawicel protocol)
- **CANable** - Open-source USB-CAN adapter
- **PCAN-USB** - Peak System adapters
- **Kvaser** - Professional CAN interfaces
- **SocketCAN** - Linux native CAN (can0, vcan0)
- **Arduino + MCP2515** - DIY CAN interface (with CanHacker firmware)

### Protocols
- **SLCAN** (Serial Line CAN) - via /dev/tty* or COM ports
- **SocketCAN** - Linux kernel CAN interface
- **CanHacker/Lawicel** - Serial protocol for USBtin-like devices

---

## Use Cases

1. **Automotive Development** - Reverse engineer vehicle CAN networks
2. **IoT/Industrial** - Monitor and debug CAN-based systems
3. **Education** - Learn CAN bus communication
4. **Testing** - Simulate CAN devices and test ECUs
5. **Diagnostics** - Troubleshoot CAN network issues

---

## Packaging & Distribution

### Build System
- **Separate Dependencies**:
  - `requirements.txt` - Runtime deps (included in app)
  - `requirements-dev.txt` - Build tools (NOT included)
- **Custom Icon Support** - Easy icon generation with `create_icon.sh`
- **Automated Build** - Single command: `./build.sh`

### Output
- **macOS**: `CAN Analyzer.app` (~246 MB)
- **Linux**: `CAN Analyzer/` directory with executable

---

## Installation

### From Source
```bash
# Clone repository
git clone <repo-url>
cd CAN-Macos-Analyser

# Install dependencies
pip install -r requirements.txt

# Run
./run.sh
```

### Packaged App (macOS)
```bash
# Download CAN Analyzer.app
# Double-click to run
open "CAN Analyzer.app"
```

### Packaged App (Linux)
```bash
# Download and extract
./CAN\ Analyzer/CAN\ Analyzer
```

---

## Configuration

### Settings Dialog
- **Device Path** - Serial port or SocketCAN interface
- **Bitrate** - 125k, 250k, 500k, 1000k bps
- **Bus Type** - Auto-detected (SLCAN/SocketCAN)
- **Listen Only** - Monitor without ACK
- **Language** - 5 languages available

### Keyboard Shortcuts
- `Ctrl+O` - Connect
- `Ctrl+S` - Save Receive Log
- `Ctrl+L` - Load Receive Log
- `Ctrl+Shift+S` - Save TX List
- `Ctrl+Shift+L` - Load TX List
- `Ctrl+T` - Toggle Tracer Mode
- `Ctrl+K` - Clear Receive
- `Ctrl+F` - Open Filters
- `Ctrl+,` - Settings
- `Ctrl+Q` - Exit

---

## Quality & Stability

-  Comprehensive error handling and logging
-  Modular architecture (~6,500 lines of clean code)
-  Professional packaging system
-  Multi-language support (5 languages)
-  Improved performance and stability
-  Extensive documentation (README, DEPENDENCIES, ICONS)
-  Custom icon support
-  Automated build process

---

## Documentation

- **README.md** - Main documentation
- **DEPENDENCIES.md** - Dependency management guide
- **ICONS.md** - Icon creation guide
- **examples/README.md** - Arduino examples and protocol docs

---

## Credits

### Inspired by
- **CANHacker** - Original Windows CAN analysis tool
- **python-can** - Excellent CAN library
- **PyQt6** - Powerful GUI framework

### Hardware Support
- **autowp/arduino-canhacker** - Arduino CanHacker firmware
- **USBtin** - USB-CAN adapter reference

---

## Future Plans

### High Priority
- [ ] Hardware Filters (28 filters)
- [ ] CAN Bomber (message injection tool)
- [ ] Trigger-based Transmission
- [ ] Windows support (PyInstaller)

### Medium Priority
- [ ] Gateway Mode (2 CAN channels)
- [ ] Advanced Statistics
- [ ] DBC File Support
- [ ] Export to other formats (BLF, ASC)

### Low Priority
- [ ] Channel Splitter
- [ ] Real-time Plotting
- [ ] Custom Themes
- [ ] Plugin system

---

## License

[Add your license here]

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

Version 0.1.0 - January 31, 2026
