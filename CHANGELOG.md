# Changelog

All notable changes to CAN Analyzer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-01

### Added - Multi-CAN Support 🎉

#### Core Multi-CAN Features
- **Multiple CAN Bus Support**: Connect to multiple CAN buses simultaneously
- **CANBusManager**: New backend architecture for managing multiple CAN interfaces
- **Channel Column**: Added to Monitor, Tracer, and TX tables to identify CAN bus source
- **Per-Channel Configuration**: Individual settings for each CAN bus (name, device, baudrate, listen_only, etc.)
- **Auto-Interface Detection**: Automatically detects SocketCAN vs SLCAN based on device name
- **Multi-CAN Settings UI**: Comprehensive configuration interface with add/remove/scan devices

#### UI/UX Improvements
- **Column Reordering**: Channel placed after Count/Time for better visibility
  - Monitor: ID, Count, **Channel**, PID, DLC, Data, Period, ASCII, Comment
  - Tracer: ID, Time, **Channel**, PID, DLC, Data, ASCII, Comment
- **Enhanced Status Bar**: Shows detailed status for each channel
  - Real mode: `CAN1: ✓ 500k | CAN2: ✓ 250k` (✓=connected, ✗=failed)
  - Simulation mode: `CAN1: SIM 500k | CAN2: SIM 250k`
  - Device mapping: `CAN1→/dev/ttyUSB0 | CAN2→can0`
- **TX Channel Selection**: Dropdown to select target CAN bus for transmission
- **Terminology Alignment**: Aligned with CAN-Hacker industry standards
  - "Source" → "Channel" (CAN bus identifier)
  - "Channel" → "Device" (physical interface)

#### Advanced Features
- **Channel-Specific Filters**: Filter IDs independently per channel
  - Filter by ID on specific channel (e.g., 0x100-0x200 on CAN1 only)
  - "ALL" channel filter applies to all buses
  - Whitelist/Blacklist mode per channel
- **Message Grouping**: Monitor groups by (ID, Channel) tuple
  - Same ID on different channels shown separately
  - Independent counters and period tracking per (ID, Channel)
- **Save/Load with Channel**: CSV and TRC formats now include channel information
  - Backward compatible with old format (defaults to CAN1)

### Changed

#### Behavior Changes
- **Send All Logic**: Now respects TX Mode setting
  - TX Mode = "off": Ignored (not sent)
  - TX Mode = "on": Sent periodically with configured period
  - TX Mode = "trigger": Ignored (only sent when trigger fires)
- **Receive Threads**: Multi-CAN uses CANBusManager's own threads (no legacy receive_loop)
- **Monitor/Tracer Toggle**: Messages now preserved when switching modes
  - Properly regroups by (ID, Channel) when switching to Monitor
  - Maintains all messages when switching to Tracer

#### Configuration Format
- **New config.json structure** for multi-CAN:
  ```json
  {
    "can_buses": [
      {
        "name": "CAN1",
        "channel": "/dev/ttyUSB0",
        "baudrate": 500000,
        "interface": "slcan",
        "listen_only": false,
        "com_baudrate": "115200 bit/s",
        "rts_hs": false
      }
    ]
  }
  ```
- Legacy single-CAN format still supported

### Fixed
- Column index errors after reordering (add to TX, copy functions, filters)
- Message sending type detection (can.Message vs CANMessage)
- TX source dropdown not updating with connected buses
- Save/Load TX not preserving channel information
- Monitor grouping not considering channel
- Filter dialog parent reference error
- Apply filters reading wrong column indices

### Documentation
- Added comprehensive Multi-CAN Support section to README
- Configuration examples for single and multi-CAN setups
- Use cases and best practices
- Interface auto-detection documentation

---

## [0.1.0] - 2025-12-XX

### Initial Release
- Basic CAN bus analyzer functionality
- Monitor and Tracer modes
- Message transmission with periodic sending
- Filters and triggers
- Multi-language support (EN, PT, ES, DE, FR)
- Theme support (Light, Dark, System)
- Save/Load logs and transmit lists
- Bit field viewer
- USB device monitoring

---

[0.2.0]: https://github.com/phnahes/can-bus-analyzer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/phnahes/can-bus-analyzer/releases/tag/v0.1.0
