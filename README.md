# CAN Analyzer

Professional CAN bus analyzer with real-time monitoring, message transmission, and advanced filtering. Built with Python and PyQt6 for macOS and Linux.

## Features

- **Dual View Modes**: Monitor (grouped by ID) and Tracer (chronological)
- **Message Transmission**: Single, batch, and periodic transmission with trigger support
- **Advanced Filtering**: Software filters by ID range and data content
- **Bit Field Viewer**: Byte-by-byte visualization with custom labels
- **Multi-Format Support**: Save/load in JSON, CSV, and TRC formats
- **Multi-Language**: English, Portuguese, Spanish, German, French
- **Cross-Platform**: Native packaging for macOS (py2app) and Linux (PyInstaller)
- **Hardware Support**: USBtin, CANable, PCAN-USB, Kvaser, SocketCAN, Arduino+MCP2515

## Quick Start

### Run from Source

```bash
./run.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python can_analyzer_qt.py
```

### Build Standalone Package

```bash
pip install -r requirements-dev.txt
./build.sh
```

**Output:**
- macOS: `dist/CAN Analyzer.app`
- Linux: `dist/CAN Analyzer/CAN Analyzer`

## Requirements

**Runtime:**
- Python 3.9+
- python-can >= 4.3.1
- pyserial >= 3.5
- PyQt6 >= 6.6.0

**Build (optional):**
- py2app >= 0.28.8 (macOS)
- PyInstaller >= 6.0.0 (Linux)
- Pillow >= 10.0.0 (icon generation)

## Supported Platforms

| Platform | Status | Device Paths | Packaging |
|----------|--------|--------------|-----------|
| macOS | Supported | `/dev/cu.usbserial*`, `/dev/cu.usbmodem*` | py2app |
| Linux | Supported | `/dev/ttyUSB*`, `/dev/ttyACM*`, `can0`, `vcan0` | PyInstaller |

## Hardware Setup

### Supported Adapters

- USB-CAN adapters (SLCAN protocol)
- SocketCAN interfaces (Linux)
- Virtual CAN (testing)
- Arduino + MCP2515 (CanHacker firmware)

### Connection

1. Open Settings (Ctrl+,)
2. Click **Scan Devices** to detect adapters
3. Select device and configure baudrates:
   - COM Baudrate: 115200 bps (serial)
   - CAN Baudrate: 500K (bus speed)
4. Click **OK** and **Connect**

### Simulation Mode

Test without hardware by enabling **Simulation Mode** in Settings. Generates realistic CAN traffic for development and testing.

## Usage

### Basic Workflow

1. **Connect**: Configure device in Settings, click Connect
2. **Monitor**: View messages in Monitor (grouped) or Tracer (chronological) mode
3. **Filter**: Use software filters (Ctrl+F) to focus on specific IDs
4. **Transmit**: Configure messages in TX panel, send single or periodic
5. **Save**: Export logs in JSON/CSV/TRC format (Ctrl+S)

### Advanced Features

**Bit Field Viewer**: Right-click message → Bit Field Viewer for detailed bit analysis

**Triggers**: Tools → Triggers (Ctrl+G) for automatic response transmission

**Playback**: Load trace file and replay with original timing

## Configuration

Settings auto-save to `config.json`:

```json
{
  "language": "en",
  "baudrate": 500000,
  "channel": "can0",
  "listen_only": false,
  "com_baudrate": "115200 bit/s"
}
```

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Connect | Ctrl+O |
| Settings | Ctrl+, |
| Filters | Ctrl+F |
| Triggers | Ctrl+G |
| Save Log | Ctrl+S |
| Load Log | Ctrl+L |
| Clear | Ctrl+K |
| Tracer Mode | Ctrl+T |

## Internationalization

Change language in Settings → Language. Supported languages:

- English (en)
- Português (pt)
- Español (es)
- Deutsch (de)
- Français (fr)

To add new languages, edit `src/i18n.py` and submit a PR.

## Examples

The `examples/` folder includes:

**Python:**
- `send_can_message.py`: Direct SLCAN communication script

**Arduino:**
- `arduino_msg_generator.ino`: Configurable message generator
- `arduino_msg_receiver.ino`: Message receiver with filtering

### Arduino as CAN Interface

Use Arduino + MCP2515 as a low-cost adapter:

1. Install **CanHacker** library in Arduino IDE
2. Upload example: File → Examples → CanHacker → usb_cdc
3. Connect Arduino via USB
4. In CAN Analyzer Settings:
   - Device: `/dev/tty.usbmodemXXXXXX`
   - COM Baudrate: 115200 bps
   - CAN Baudrate: 500K

See `examples/README.md` for wiring diagrams and configuration.

## Project Structure

```
CAN-Macos-Analyser/
├── can_analyzer_qt.py       # Entry point
├── src/
│   ├── main_window.py       # Main GUI
│   ├── models.py            # Data models
│   ├── dialogs_new.py       # Settings/Filters dialogs
│   ├── file_operations.py   # Save/load
│   ├── can_interface.py     # CAN communication
│   ├── i18n.py              # Translations
│   └── logger.py            # Logging system
├── examples/                # Arduino/Python examples
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Build dependencies
├── build.sh                 # Build script
└── setup.py                 # py2app config
```

## Packaging

### Custom Icon

```bash
./create_icon.sh my_icon.png
./build.sh
```

Generates `icon.icns` (macOS) and `icon.ico` (Linux).

### Build Files

- `setup.py`: py2app configuration (macOS)
- `can_analyzer.spec`: PyInstaller spec (Linux)
- `requirements.txt`: Runtime dependencies (included in package)
- `requirements-dev.txt`: Build tools (not included)

## Logging

Logs saved to `logs/can_analyzer_YYYYMMDD.log`:

```bash
# View real-time logs
tail -f logs/can_analyzer_$(date +%Y%m%d).log

# Search errors
grep ERROR logs/*.log
```

**Rotation**: 10MB max, 5 backups

## Troubleshooting

**App won't start:**
```bash
python3 --version  # Check 3.9+
rm -rf venv && python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Device not detected:**
- Check connection: `ls /dev/tty.*` or `ls /dev/ttyUSB*`
- Verify permissions: `sudo chmod 666 /dev/ttyUSB0`
- Try Simulation Mode

**Messages not appearing:**
- Verify connection status
- Check CAN baudrate matches network
- Disable software filters

## Contributing

Contributions welcome! Please:

1. Fork repository
2. Create feature branch
3. Test thoroughly
4. Submit pull request

**Adding translations:** Edit `src/i18n.py` with new language code and translations.

**Reporting bugs:** Include logs, OS version, and steps to reproduce.

## License

GNU General Public License v3.0 (GPL-3.0)

- Free to use, study, modify, and distribute
- Modifications must be GPL-3.0 licensed
- Source code must be available
- No warranty

Full text: [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html)

## Acknowledgments

- [CANHacker](http://www.mictronics.de/projects/usb-can-bus/) - Original inspiration
- [python-can](https://github.com/hardbyte/python-can) - CAN library
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework

## Related Projects

- [BUSMASTER](https://rbei-etas.github.io/busmaster/) - Open-source CAN tool
- [arduino-canhacker](https://github.com/autowp/arduino-canhacker) - Arduino CanHacker library
- [python-can](https://github.com/hardbyte/python-can) - Python CAN library

---

**Version**: 0.1.0  
**Status**: Active Development  
**Last Updated**: January 2026

