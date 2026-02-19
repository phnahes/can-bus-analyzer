# Changelog

All notable changes to the CAN Analyzer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

### Changed

### Fixed

---

## [1.2.0] - 2026-02-19

### Added
- **VAG BAP Protocol Decoder**: Complete support for Volkswagen/Audi BAP (Bedien- und Anzeigeprotokoll)
  - Multi-frame reassembly with up to 4 parallel streams per CAN ID
  - BAP header parsing (opcode/lsg/fct) for both 11-bit and 29-bit CAN IDs
  - Conservative (multi-frame only) and Aggressive (includes single-frame) detection modes
  - Stream timeout management (2.0s configurable)
  - Support for messages up to 4095 bytes
  
- **VAG BAP Analyzer Dialog** (Ctrl+3): Dedicated UI for BAP traffic analysis
  - Reassembled Messages tab: Complete payloads with header fields
  - Raw Frames tab: Individual CAN frames with progress indicators
  - Visual grouping: Link raw frames to their reassembled packets
  - Details panel: Complete payload view with frame linkage explanation
  - Filters: CAN ID, LSG, Source
  - Export/Import: Save/load captures as JSON
  - Replay: Resend captured packets with optional timing preservation
  - Background decoding: Worker thread prevents UI freezes
  - Performance metrics: Lag, inflight, dropped messages
  
- **Global Close Shortcut**: Ctrl+W (Cmd+W on macOS) closes active dialogs/secondary windows
- **BAP Documentation**: Comprehensive protocol documentation in `docs/decoders/BAP.md`
  - Complete protocol structure with multi-frame examples
  - Implementation architecture diagrams
  - Usage guide and troubleshooting
  - References to open-source projects (norly/revag-bap, tmbinc/kisim, MIGINC/BAP_RE, e-golf-comfort-can)

---

## [1.1.2] - 2026-02-17

### Fixed
- Diff Mode: restore bold highlighting (no `[XX]` formatting in Data column)
- CI workflow: upload only the distributable `CAN-Analyzer-*.zip` (avoid artifact containing both `dist/**` and the zip)
- Logs/messages: remaining Portuguese strings standardized to English

---

## [1.1.1] - 2026-02-17

### Added
- **Diff Mode (Monitor)**: filter repeats and/or highlight deltas (cansniffer-like workflow)
- **OBD-II Monitor**: Detect VIN (Service 09 PID 02, ISO-TP) and show it prominently in the header
- **OBD-II Monitor**: Clear DTCs button (Service 04)
- **TX table**: Delete/Backspace key removes selected rows
- **Gateway docs**: bench test how-to using Arduino sketches (lab setup)
- **Release tooling**: `extras/release.py` + `extras/release.sh` (version bump + commit + tag)
- **CI/Release automation**: GitHub Actions workflows for macOS and Linux builds

### Changed
- Diff highlighting in the Data column uses bold rendering (no `[XX]` wrapping)
- Diff settings persist automatically in `config.json` (Diff always starts OFF on startup)
- Gateway notifications are consolidated in the bottom-right notification area
- Verbose RX/TX queue/send logs moved to DEBUG
- Arduino OBD-II ECU simulator:
  - Service 03 DTC replies now use ISO-TP FF/FC/CF (real-vehicle style)
  - Service 04 Clear DTC now replies with an ACK-like 0x44 response

### Fixed
- Multi-CAN partial connect: one failing bus no longer disconnects the working bus
- OBD-II:
  - Raw Messages now show ECU responses consistently (not only requests)
  - DTC parsing no longer mixes with live polling responses
  - VIN logging no longer duplicates "VIN detected" in statistics
  - ISO-TP Flow Control is sent to the correct physical ECU request ID (0x7E0..0x7E7)
- UI translations: missing OBD-II button keys added (VIN / Clear DTCs)
- Various logs standardized to English for terminal output

## [1.0.0] - 2026-02-06

### 🎉 First Stable Release

This is the first stable release of CAN Analyzer, marking a significant milestone with comprehensive protocol decoder support and professional documentation.

### Added

#### Protocol Decoders
- **FTCAN 2.0 Protocol Decoder**: Complete support for FuelTech's proprietary CAN protocol
  - Automatic decoding of 100+ measures (Lambda, RPM, TPS, MAP, temperatures, pressures, injection, ignition)
  - Support for WB-O2 Nano, FT500/FT600 ECUs, and other FuelTech devices
  - 29-bit Extended ID parsing (ProductID, DataFieldID, MessageID)
  - Big-endian signed 16-bit values with multipliers
  - Segmented packet support for large data streams
  - 1 Mbps fixed bitrate
  
- **OBD-II Protocol Decoder**: Universal automotive diagnostics support (ISO 15765-4)
  - 60+ Parameter IDs (PIDs) with automatic decoding
  - Support for all 10 OBD-II services (0x01-0x0A)
  - Diagnostic Trouble Code (DTC) reading and decoding
  - Multi-frame message support (ISO-TP)
  - Request/response polling model
  - 500 kbps / 250 kbps bitrate support
  - Compatible with all vehicles 1996+ (US/EU/Japan)

#### User Interfaces
- **FTCAN Analyzer** (Ctrl+Shift+F): Dedicated UI for FTCAN protocol
  - Decoded Messages tab: Full message decoding with device identification
  - Live Measures tab: Real-time sensor values grouped by device
  - Diagnostics tab: Network statistics, device detection, error tracking
  - Multi-device support with automatic ProductID recognition
  
- **OBD-II Monitor** (Ctrl+Shift+O): Interactive diagnostics interface
  - PID Selection: Choose from 60+ parameters with category filtering
  - Quick Presets: Basic, Extended, Lambda, Fuel system presets
  - Automatic Polling: Configurable interval (100ms-10s)
  - Live Values: Real-time data display with last update timestamps
  - DTC Reading: Read and decode diagnostic trouble codes
  - Raw Messages: Request/response logging with color coding
  - Statistics: Success rate, response time, error tracking
  - Check Available PIDs: Query ECU for supported parameters
  - Single Shot: One-time read without continuous polling
  - Save Results: Export data to CSV format

- **Protocol Decoder Manager** (Ctrl+Shift+D): Centralized decoder management
  - Enable/disable decoders independently
  - View decoding statistics (decoded/failed messages)
  - Configure decoder priority
  - Reset statistics

#### Documentation
- **Complete Technical Specifications**:
  - [FTCAN 2.0 Protocol](docs/ftcan/README.md): 30+ pages of technical documentation
  - [OBD-II Protocol](docs/decoders/OBD2.md): 40+ pages covering all aspects
  - [FTCAN Decoder](docs/decoders/FTCAN.md): Implementation details
  
- **Comprehensive Tool Documentation**:
  - [General Tools](tools/general/README.md): CAN utilities documentation
  - [Arduino Tools](tools/arduino/README.md): Hardware examples and simulators
  - [FTCAN Tools](tools/ftcan/README.md): FTCAN-specific utilities

#### Testing & Development Tools
- **Arduino OBD-II ECU Simulator** (`tools/arduino/arduino_obd2_ecu_simulator.ino`)
  - Simulates OBD-II ECU responses
  - Supports Service 0x01 (8 PIDs with animated data)
  - Supports Service 0x03 (4 DTCs: P0171, P0300, C0035, B1234)
  - Multi-frame DTC responses
  - Support PIDs (0x00, 0x20, 0x40, 0x60)
  
- **FTCAN Simulator** (`tools/ftcan/ftcan_simulator.py`)
  - Simulate WB-O2 Nano lambda readings
  - Simulate FT600 ECU with multiple measures
  - Standard CAN and segmented packet examples
  
- **OBD-II Poller** (`tools/general/obd2_poller.py`)
  - CLI tool for OBD-II polling
  - Interactive PID selection
  - Configurable polling interval
  - Automatic decoding and display
  
- **Baudrate Detector** (`tools/general/baudrate_detect.py`)
  - Auto-detect CAN baudrate via trial and error
  - Tests common rates (125k, 250k, 500k, 1M)
  - Validates message reception

#### Architecture Improvements
- **Modular Decoder System**:
  - Core decoder (`*_decoder.py`): Pure decoding logic
  - Protocol adapter (`*_protocol_decoder.py`): App integration
  - Base class (`protocol_decoder.py`): Abstract interface
  - Clean separation of concerns
  - Easy to extend with new protocols
  
- **Project Reorganization**:
  - Created `src/decoders/` directory for all protocol decoders
  - Organized tools into subdirectories: `general/`, `arduino/`, `ftcan/`
  - Renamed `dialogs_new.py` to `dialogs.py`
  - Created dedicated dialog files: `dialogs_ftcan.py`, `dialogs_obd2.py`
  - Improved import structure and package organization

#### File Management
- Renamed main entry point: `can_analyzer_qt.py` → `can_analyzer.py`
- Updated all references in `setup.py`, `can_analyzer.spec`, `run.sh`
- Created comprehensive `CHANGELOG.md`

### Changed
- **README.md**: Complete rewrite with 800+ lines
  - Added Protocol Decoders section
  - Expanded documentation links
  - Updated project structure
  - Added keyboard shortcuts for new features
  - Comprehensive troubleshooting for protocol decoders
  - Updated to version 1.0.0
  
- **Status**: Changed from "Active" to "Stable"
- **Build identifier**: Updated to 2026.02

### Fixed
- Thread safety issues in OBD-II Monitor using PyQt signals
- Multi-frame DTC processing (ISO-TP) now correctly handles all frames
- Connection status updates now work reliably
- Polling timer management improved
- Error handling for serial communication noise

### Technical Details

#### FTCAN 2.0 Implementation
- **Identification parsing**: 29-bit ID → ProductID (15 bits) + DataFieldID (3 bits) + MessageID (11 bits)
- **Measure decoding**: MeasureID (16 bits) → DataID (15 bits) + IsStatus (1 bit)
- **Value calculation**: Signed 16-bit big-endian × multiplier
- **Segmentation**: Support for payloads up to 1,783 bytes
- **Device database**: 20+ ProductTypeIDs with priority ranges

#### OBD-II Implementation
- **Request format**: [Length, Service, PID, Parameters...]
- **Response format**: [Length, Service+0x40, PID, Data...]
- **PID formulas**: 60+ formulas for data conversion
- **DTC encoding**: 2 bytes per code (Type + System + Code)
- **ISO-TP support**: First Frame, Consecutive Frame, Flow Control
- **Support PID parsing**: 32-bit bitmaps for PID availability

---

## [0.4.0] - 2026-02-05

### Added
- Initial protocol decoder implementation
- FTCAN 2.0 basic support
- OBD-II basic support
- Protocol documentation structure

---

## [0.3.0] - 2026-01-XX

### Added
- **CAN Gateway**: Bridge and filter messages between two CAN buses
  - Bidirectional transmission control
  - Static blocking by message ID
  - Dynamic blocking with automatic ID cycling
  - Message modification capabilities
  - Real-time statistics (forwarded, blocked, modified)
  
- **Split-Screen Monitor**: View messages from different channels side-by-side
  - Dual panel layout
  - Independent channel selection
  - Synchronized scrolling option
  - Per-panel filtering

- **Complete Internationalization**: Full i18n support
  - English (en)
  - Portuguese (pt)
  - Spanish (es)
  - German (de)
  - French (fr)

### Changed
- Improved multi-CAN terminology (Channel vs Device)
- Enhanced status bar with per-channel information
- Better error handling and logging

---

## [0.2.0] - 2025-XX-XX

### Added
- **Multi-CAN Support**: Multiple CAN buses simultaneously
  - Configure multiple CAN interfaces
  - Per-channel message filtering
  - Independent baudrate per bus
  - Channel column in message tables
  
- **USB Device Auto-detection**: Real-time device monitoring
  - Automatic device scanning
  - Hot-swap support
  - Device removal detection

### Changed
- Refactored CAN bus management
- Improved configuration system
- Enhanced device selection dialog

---

## [0.1.0] - 2025-XX-XX

### Added
- Initial release
- **Monitor Mode**: Group messages by ID with counters
- **Tracer Mode**: Chronological message list
- **Message Transmission**: Full CAN message configuration
- **Bit Field Viewer**: Byte-by-byte and bit-by-bit inspection
- **Software Filters**: ID and data-based filtering
- **Trigger-based TX**: Automatic transmission on received messages
- **Playback**: Reproduce recorded traces
- **File Operations**: Save/load logs and transmit lists (JSON, CSV, TRC)
- **Cross-platform**: macOS and Linux support
- **SLCAN Support**: USB-CAN adapters via python-can
- **SocketCAN Support**: Native Linux CAN interface
- **Simulation Mode**: Test without hardware

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| **1.0.0** | 2026-02-06 | 🎉 **First Stable Release** - Protocol Decoders (FTCAN, OBD-II) |
| 0.4.0 | 2026-02-05 | Protocol decoder foundation |
| 0.3.0 | 2026-01-XX | CAN Gateway & Split-Screen |
| 0.2.0 | 2025-XX-XX | Multi-CAN Support |
| 0.1.0 | 2025-XX-XX | Initial Release |

---

## Upgrade Notes

### From 0.3.0 to 1.0.0

**New Features:**
- Protocol decoders are disabled by default. Enable them in Tools → Protocol Decoders → Manage Decoders
- New keyboard shortcuts: Ctrl+Shift+F (FTCAN), Ctrl+Shift+O (OBD-II), Ctrl+Shift+D (Decoders)
- Main file renamed: `can_analyzer_qt.py` → `can_analyzer.py` (update your scripts if needed)

**Configuration:**
- No changes to `config.json` format
- Backward compatible with previous versions

**Dependencies:**
- No new runtime dependencies
- Same Python 3.9+ requirement

---

## Future Roadmap

### Planned for v1.1.0
- Hardware filters (28 configurable)
- Additional protocol decoders (J1939, CANopen)
- DBC file support
- Real-time plotting

### Planned for v1.2.0
- CAN Bomber (spoofing tool)
- Statistics & analytics dashboard
- Advanced signal processing

### Planned for v2.0.0
- Plugin system for custom decoders
- Cloud data logging
- Mobile companion app

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).
See [LICENSE](LICENSE) for details.
