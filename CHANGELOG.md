# Changelog

All notable changes to CAN Analyzer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-02-01

### Added - CAN Gateway & Split-Screen 🌉

#### CAN Gateway Features
- **Gateway Mode**: Bridge and filter messages between two CAN buses
- **Bidirectional Transmission Control**: 
  - Enable/disable CAN1→CAN2 transmission
  - Enable/disable CAN2→CAN1 transmission
  - Independent control for each direction
- **Static Blocking Rules**:
  - Block specific message IDs on specific channels
  - Enable/disable individual blocking rules
  - Multiple rules supported simultaneously
- **Dynamic Blocking**:
  - Automatically cycle through a range of IDs
  - Configurable period for each ID (milliseconds)
  - Useful for testing ECU responses to missing messages
- **Message Modification** (framework ready):
  - Modify message IDs as they pass through gateway
  - Modify data bytes with configurable masks
  - Apply transformations to messages in transit
- **Gateway Statistics**:
  - Track forwarded messages count
  - Track blocked messages count
  - Track modified messages count
  - Real-time statistics display
  - Reset statistics functionality
- **Gateway Configuration Dialog**:
  - Comprehensive UI for all gateway settings
  - Tables for managing blocking rules
  - Dynamic blocking configuration
  - Statistics monitoring
  - Keyboard shortcut: Ctrl+W

#### Split-Screen Monitor
- **Split-Screen Mode**: View messages from two channels simultaneously
- **Channel Selection**: Choose which channel displays in each panel (left/right)
- **Independent Filtering**: Messages automatically filtered by selected channel
- **Keyboard Shortcut**: Ctrl+D to toggle split-screen mode
- **Use Cases**:
  - Compare traffic between two networks
  - Monitor gateway operation in real-time
  - Analyze timing differences between channels
  - Simplify multi-network debugging

#### Data Models
- **GatewayConfig**: Complete gateway configuration management
- **GatewayBlockRule**: Static blocking rule definition
- **GatewayDynamicBlock**: Dynamic blocking with ID range and period
- **GatewayModifyRule**: Message modification rules (ID and data transformation)

#### Backend Enhancements
- **CANBusManager Gateway Integration**:
  - Gateway message processing in receive callback
  - Automatic message forwarding based on rules
  - Blocking and modification logic
  - Dynamic blocking thread management
  - Statistics tracking
- **Gateway Thread Management**:
  - Separate thread for dynamic blocking
  - Automatic ID cycling with configurable periods
  - Thread-safe operations

#### Internationalization
- Complete translations for Gateway features (EN, PT, ES, DE, FR)
- Complete translations for Split-Screen mode (EN, PT, ES, DE, FR)
- New translation keys:
  - `gateway_*`: All gateway-related strings
  - `split_screen_*`: All split-screen related strings

### Changed
- **Menu Structure**: Added Gateway option to Tools menu
- **Menu Structure**: Added Split-Screen Mode to View menu
- **CANBusManager**: Enhanced with gateway processing capabilities
- **Message Flow**: Messages now pass through gateway rules before display

### Documentation
- Added comprehensive CAN Gateway section to README
- Added Split-Screen Monitor documentation to README
- Updated keyboard shortcuts table
- Added use cases and examples for both features
- Reference to CAN-Hacker Gateway implementation

### Technical Notes
- Gateway implementation inspired by CAN-Hacker Gateway
- Framework ready for hardware filters (28 configurable)
- Extensible architecture for future gateway features
- Split-screen implementation provides foundation for advanced layouts

---

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

[0.3.0]: https://github.com/phnahes/can-bus-analyzer/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/phnahes/can-bus-analyzer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/phnahes/can-bus-analyzer/releases/tag/v0.1.0
