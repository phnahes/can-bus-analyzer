# FTCAN 2.0 Protocol Documentation

Complete technical documentation for FuelTech's FTCAN 2.0 protocol support in CAN Bus Analyzer.

---

## Contents

- [Protocol Overview](#protocol-overview)
- [Technical Specifications](#technical-specifications)
- [Identification Structure](#identification-structure)
- [Data Field Layouts](#data-field-layouts)
- [Message Types](#message-types)
- [Measure IDs](#measure-ids)
- [Supported Devices](#supported-devices)
- [Implementation](#implementation)
- [Usage Guide](#usage-guide)
- [Official Documentation](#official-documentation)

---

## Protocol Overview

**FTCAN 2.0** is FuelTech's proprietary CAN protocol designed for communication between their ECUs, sensors, and accessories. It runs on top of the CAN 2.0B physical layer with extended 29-bit identifiers.

### Key Features

- **Physical Layer:** CAN 2.0B Extended (29-bit IDs)
- **Bitrate:** 1 Mbps (fixed)
- **Byte Order:** Big-endian (most significant byte first)
- **Data Segmentation:** Support for messages larger than 8 bytes
- **Priority System:** Multi-level priority for devices and messages
- **Device Identification:** Unique addressing for up to 32 devices per type

### Why FTCAN?

Standard CAN provides only 8 bytes per frame. FTCAN adds:
1. **Segmentation:** Send large data streams across multiple frames
2. **Device Identification:** Know exactly which device sent the message
3. **Priority Management:** Critical data (RPM, ignition) gets higher priority
4. **Standardized Measures:** Consistent format for sensor readings

---

## Technical Specifications

### Physical Layer

- **Protocol:** CAN 2.0B Extended
- **Bitrate:** 1,000,000 bps (1 Mbps) - **FIXED**
- **Frame Type:** Extended (29-bit identifier)
- **Data Length:** 0-8 bytes per frame
- **Byte Order:** Big-endian
- **Termination:** 120Ω resistors at both ends

### CAN Frame Structure

```
┌─────────────────────────────────────────────────┐
│              CAN 2.0B Extended Frame            │
├──────────────────────────┬──────────────────────┤
│    IDENTIFICATION        │     DATA FIELD       │
│      (29 bits)           │     (0-8 bytes)      │
└──────────────────────────┴──────────────────────┘
```

---

## Identification Structure

The 29-bit identifier is divided into three fields that provide device identification, data type, and message classification.

### Bit Layout

```
┌─────────────────────────────────────────────────────────────┐
│                    29-bit Identifier                        │
├─────────────────────┬──────────────┬─────────────────────────┤
│   Bits 28-14        │  Bits 13-11  │      Bits 10-0          │
│   (15 bits)         │  (3 bits)    │      (11 bits)          │
│   ProductID         │  DataFieldID │      MessageID          │
└─────────────────────┴──────────────┴─────────────────────────┘
```

### 1. ProductID (Bits 28-14, 15 bits)

Identifies which device sent the message. Lower ProductID = higher CAN priority.

**Sub-division:**

```
┌─────────────────────────────────────────────────┐
│              ProductID (15 bits)                │
├──────────────────────────┬──────────────────────┤
│   Bits 14-5              │   Bits 4-0           │
│   (10 bits)              │   (5 bits)           │
│   ProductTypeID          │   UniqueID           │
│   (Device Type)          │   (Instance Number)  │
└──────────────────────────┴──────────────────────┘
```

- **ProductTypeID (10 bits):** Type of device (WB-O2 Nano, FT600 ECU, etc.)
- **UniqueID (5 bits):** Instance number (0-31) for multiple devices of same type

**Example:**
```
WB-O2 Nano #0:
  ProductTypeID = 0x0240 (WBO2_NANO)
  UniqueID      = 0x00 (first device)
  ProductID     = (0x0240 << 5) | 0x00 = 0x4800
```

**Priority Ranges:**

| Priority | ProductID Range | Use Case |
|----------|----------------|----------|
| Critical | 0x0000-0x1FFF | Emergency signals |
| High | 0x2000-0x3FFF | Gear controllers, knock meters |
| Medium | 0x4000-0x5FFF | Sensors, ECUs |
| Low | 0x6000-0x7FFF | Accessories |

### 2. DataFieldID (Bits 13-11, 3 bits)

Identifies the data layout in the DATA FIELD.

| Value | Name | Description |
|-------|------|-------------|
| 0x00 | Standard CAN | Direct payload (no segmentation) |
| 0x01 | Standard CAN Bridge | From/to bus converter |
| 0x02 | FTCAN 2.0 | FTCAN format with segmentation |
| 0x03 | FTCAN 2.0 Bridge | FTCAN from/to bus converter |

### 3. MessageID (Bits 10-0, 11 bits)

Identifies the message type and priority. Lower MessageID = higher priority.

**Structure:**

```
┌─────────────────────────────────────────────────┐
│              MessageID (11 bits)                │
├──────────────────────────┬──────────────────────┤
│   Bit 10                 │   Bits 9-0           │
│   (1 bit)                │   (10 bits)          │
│   IsResponse             │   Message Code       │
└──────────────────────────┴──────────────────────┘
```

- **Bit 10:** Response flag (0=Request, 1=Response)
- **Bits 9-0:** Message function/priority

**Priority Ranges:**

| Range | Priority | Typical Use |
|-------|----------|-------------|
| 0x000-0x0FF | Critical | Ignition cut, emergency |
| 0x100-0x1FF | High | RPM, TPS, MAP, timing |
| 0x200-0x2FF | Medium | Temperatures, pressures |
| 0x300-0x3FF | Low | General data |

**Common MessageIDs:**

| MessageID | Priority | Description |
|-----------|----------|-------------|
| 0x0FF | Critical | Critical broadcast |
| 0x1FF | High | High priority broadcast |
| 0x2FF | Medium | Medium priority broadcast |
| 0x3FF | Low | Low priority broadcast |
| 0x600-0x608 | Special | Simplified broadcast packets |

---

## Data Field Layouts

### DataFieldID 0x00: Standard CAN

All 8 bytes are payload. No segmentation support.

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA FIELD (0-8 bytes)                   │
├─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────────────────┤
│  0  │  1  │  2  │  3  │  4  │  5  │  6  │  7              │
│                    PAYLOAD                                  │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────────────────┘
```

**Use Case:** Simple messages that fit in 8 bytes.

---

### DataFieldID 0x02: FTCAN 2.0

Supports both single packets and segmented packets for large data.

#### Single Packet (Most Common)

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA FIELD (1-8 bytes)                   │
├─────┬───────────────────────────────────────────────────────┤
│  0  │  1  │  2  │  3  │  4  │  5  │  6  │  7              │
│ 0xFF│              PAYLOAD (0-7 bytes)                      │
└─────┴───────────────────────────────────────────────────────┘
```

- **Byte 0:** `0xFF` (single packet marker)
- **Bytes 1-7:** Payload (up to 7 bytes)

**Example - WB-O2 Nano Lambda Reading:**
```
Data: FF 00 27 03 52 00 00 00
  0xFF         = Single packet
  00 27        = MeasureID 0x0027 (DataID 0x0013 = Cylinder 1 O2, Status=1)
  03 52        = Value 0x0352 (850 decimal)
  Real value   = 850 * 0.001 = 0.850λ
```

#### Segmented Packet (Large Data)

For data larger than 7 bytes, FTCAN splits it across multiple frames.

**First Frame (Segment 0x00):**

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA FIELD (8 bytes)                     │
├─────┬─────┬─────┬─────────────────────────────────────────┤
│  0  │  1  │  2  │  3  │  4  │  5  │  6  │  7              │
│ 0x00│ SEGMENTATION│         PAYLOAD (5 bytes)              │
│     │   DATA      │                                        │
└─────┴─────┴─────┴─────────────────────────────────────────┘
```

- **Byte 0:** `0x00` (first frame marker)
- **Bytes 1-2:** Segmentation data (total payload length)
- **Bytes 3-7:** Payload start (5 bytes)

**Segmentation Data (2 bytes, big-endian):**

```
┌─────────────────────────────────────────────────────────────┐
│              Segmentation Data (16 bits)                    │
├─────────────────────────────┬───────────────────────────────┤
│   Bits 15-11 (5 bits)       │   Bits 10-0 (11 bits)         │
│   Reserved (RFU)            │   Total Payload Length        │
└─────────────────────────────┴───────────────────────────────┘
```

**Continuation Frames (Segments 0x01-0xFE):**

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA FIELD (1-8 bytes)                   │
├─────┬───────────────────────────────────────────────────────┤
│  0  │  1  │  2  │  3  │  4  │  5  │  6  │  7              │
│ 0x01│              PAYLOAD (7 bytes)                        │
└─────┴───────────────────────────────────────────────────────┘
```

- **Byte 0:** Sequence number (0x01, 0x02, ..., 0xFE)
- **Bytes 1-7:** Payload continuation (7 bytes)

**Maximum Payload:**
```
First frame:  5 bytes
+ 254 continuation frames: 254 × 7 = 1,778 bytes
Total: 1,783 bytes maximum
```

---

## Message Types

### Broadcast Messages (0x0FF, 0x1FF, 0x2FF, 0x3FF)

Real-time sensor readings broadcast periodically by devices.

**Format:**
```
Each measure = 4 bytes:
┌─────────────────┬─────────────────┐
│  MeasureID      │  Value          │
│  (2 bytes)      │  (2 bytes)      │
│  Big-endian     │  Signed 16-bit  │
└─────────────────┴─────────────────┘
```

**Multiple measures in one packet:**
```
Payload: [Measure1][Measure2][Measure3]...
         4 bytes   4 bytes   4 bytes
```

### Simplified Broadcast (0x600-0x608)

Fixed-format packets with predefined measure positions (ECU only).

**Example - 0x600:**
```
Bytes 0-1: TPS
Bytes 2-3: MAP
Bytes 4-5: Air Temperature
Bytes 6-7: Engine Temperature
```

---

## Measure IDs

Each measure consists of 4 bytes with identifier and value.

### MeasureID Structure (2 bytes, big-endian)

```
┌─────────────────────────────────────────────────┐
│              MeasureID (16 bits)                │
├─────────────────────────────┬───────────────────┤
│   Bits 15-1 (15 bits)       │   Bit 0 (1 bit)   │
│   DataID                    │   IsStatus        │
│   (Sensor Type)             │   (0=Value, 1=Status) │
└─────────────────────────────┴───────────────────┘
```

### Value (2 bytes, signed 16-bit, big-endian)

Raw value that must be multiplied to get real value.

**Example:**
```
MeasureID: 0x0027
  DataID   = 0x0027 >> 1 = 0x0013 (Cylinder 1 O2)
  IsStatus = 0x0027 & 0x01 = 1 (status)

Value: 0x0352 (850 decimal)
  Multiplier = 0.001 (from DataID 0x0013)
  Real value = 850 × 0.001 = 0.850λ
```

### Common DataIDs

| DataID | Name | Unit | Multiplier | Source |
|--------|------|------|------------|--------|
| 0x0001 | TPS (Throttle Position) | % | 0.1 | ECU |
| 0x0002 | MAP (Manifold Pressure) | Bar | 0.001 | ECU |
| 0x0003 | Air Temperature | °C | 0.1 | ECU |
| 0x0004 | Engine Temperature | °C | 0.1 | ECU |
| 0x0005 | Oil Pressure | Bar | 0.001 | ECU |
| 0x0006 | Fuel Pressure | Bar | 0.001 | ECU |
| 0x0009 | Battery Voltage | V | 0.01 | ECU |
| 0x0011 | Gear | - | 1 | ECU/Gear Controller |
| 0x0012 | Disabled O2 | λ | 0.001 | WB-O2 Sensors |
| 0x0013 | Cylinder 1 O2 | λ | 0.001 | WB-O2/ECU |
| 0x0014 | Cylinder 2 O2 | λ | 0.001 | WB-O2/ECU |
| 0x0015-0x0021 | Cylinders 3-16 O2 | λ | 0.001 | WB-O2/ECU |
| 0x0025 | Left Bank O2 | λ | 0.001 | WB-O2/ECU |
| 0x0026 | Right Bank O2 | λ | 0.001 | WB-O2/ECU |
| 0x0027 | Exhaust O2 | λ | 0.001 | WB-O2/ECU |
| 0x0042 | Engine RPM | RPM | 1 | ECU |
| 0x0043 | Injection Bank A Time | ms | 0.01 | ECU |
| 0x0044 | Injection Bank B Time | ms | 0.01 | ECU |
| 0x0045 | Injection Bank A Duty | % | 0.1 | ECU |
| 0x0046 | Injection Bank B Duty | % | 0.1 | ECU |
| 0x0047 | Ignition Advance/Retard | ° | 0.1 | ECU |

**Full list:** See official documentation or `src/decoders/ftcan_decoder.py`

---

## Supported Devices

### Product Type IDs

| ProductTypeID | Device | ProductID Range | Priority |
|---------------|--------|----------------|----------|
| 0x0FFF | Device Searching | 0x1FFE0-0x1FFFF | Critical |
| 0x0140 | Gear Controller | 0x2800-0x281F | High |
| 0x0141 | Knock Meter | 0x2820-0x283F | High |
| 0x0142 | Boost Controller 2 | 0x2840-0x285F | High |
| 0x0150 | Injector Driver | 0x2A00-0x2A1F | High |
| 0x023F | Input Expander | 0x47E0-0x47FF | Medium |
| 0x0240 | **WB-O2 Nano** | 0x4800-0x481F | Medium |
| 0x0241 | WB-O2 Slim | 0x4820-0x483F | Medium |
| 0x0242 | Alcohol O2 | 0x4840-0x485F | Medium |
| 0x0243 | FTSpark A/B | 0x4860-0x4861 | Medium |
| 0x0244 | Switchpad (8/4/5/mini) | 0x4880-0x4887 | Medium |
| 0x0280 | **FT500 ECU** | 0x5000-0x501F | Medium |
| 0x0281 | **FT600 ECU** | 0x5020-0x503F | Medium |
| 0x0282-0x02E4 | Future ECUs (reserved) | 0x5040-0x5C9F | Medium |

**Note:** Up to 32 devices of the same type can coexist (UniqueID 0-31).

---

## Implementation

### Decoder Architecture

The FTCAN implementation follows a modular design:

```
┌─────────────────────────────────────────────────────────────┐
│                   ftcan_decoder.py                          │
│                   (Core Implementation)                     │
│                                                             │
│  • FTCANIdentification (29-bit ID parsing)                 │
│  • FTCANMeasure (4-byte measure decoding)                  │
│  • FTCANSegmentedPacket (segmentation handling)            │
│  • FTCANDecoder (main decoder class)                       │
│  • MEASURE_IDS (sensor database)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              ftcan_protocol_decoder.py                      │
│              (Protocol Adapter)                             │
│                                                             │
│  • FTCANProtocolDecoder (ProtocolDecoder interface)        │
│  • Wraps FTCANDecoder                                      │
│  • Returns DecodedData for app                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   dialogs_ftcan.py                          │
│                   (User Interface)                          │
│                                                             │
│  • FTCANDialog (PyQt6 GUI)                                 │
│  • Real-time message display                               │
│  • Live measures monitoring                                │
│  • Diagnostics and statistics                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Classes

**1. FTCANIdentification**
```python
@dataclass
class FTCANIdentification:
    product_id: int          # 15 bits
    data_field_id: int       # 3 bits
    message_id: int          # 11 bits
    product_type_id: int     # 10 bits (derived)
    unique_id: int           # 5 bits (derived)
    is_response: bool        # 1 bit (derived)
```

**2. FTCANMeasure**
```python
@dataclass
class FTCANMeasure:
    measure_id: int          # 16 bits
    value: int               # 16 bits signed
    data_id: int             # 15 bits (derived)
    is_status: bool          # 1 bit (derived)
```

**3. FTCANDecoder**
```python
class FTCANDecoder:
    def decode_message(self, can_id: int, data: bytes) -> Dict
    def is_ftcan_message(can_id: int) -> bool
    def get_expected_baudrate() -> int
    def clear_segmented_buffers()
```

---

## Usage Guide

### 1. Enable FTCAN Decoder

```
CAN Analyzer → Tools → Protocol Decoders → Enable "FTCAN 2.0"
```

### 2. Connect to CAN Bus

**Requirements:**
- Baudrate: **1 Mbps** (mandatory)
- Extended IDs: Enabled
- Termination: 120Ω at both ends

**Connection Settings:**
```
Settings (Ctrl+,):
  CAN Device: /dev/ttyACM0 (or your device)
  COM Baudrate: 115200 bps
  CAN Baudrate: 1M (1 Mbps)
```

### 3. Open FTCAN Analyzer

```
Tools → FTCAN 2.0 Analyzer... (Ctrl+Shift+F)
```

**Features:**
- **Decoded Messages:** All FTCAN messages with full decoding
- **Live Measures:** Real-time sensor values
- **Diagnostics:** Network statistics and device detection

### 4. Verify Communication

**Diagnostics Tab:**
- Check "Devices Detected"
- Should show: "WBO2_NANO #0" or "FT600_ECU #0"
- Verify message rate (should be ~10-100 Hz)

---

## WB-O2 Nano Wiring

### Connector Pinout

| Pin | Wire Color | Signal | Connection |
|-----|------------|--------|------------|
| 4 | Red | +12V | Battery positive |
| 6 | White/Red | CAN+ (CANH) | CAN-H |
| 10 | Black/White | GND Chassis | Chassis ground |
| 11 | Black | GND Battery | Battery negative |
| 12 | Yellow/Blue | CAN- (CANL) | CAN-L |

**Important:**
- **Termination:** Add 120Ω resistor between pins 6 and 12 at **both ends** of bus
- **Ground:** Connect both GND pins (10 and 11)
- **Power:** 12V nominal (9-16V range)

### Example CAN ID

**WB-O2 Nano #0 broadcasting lambda:**
```
ProductTypeID: 0x0240 (WBO2_NANO)
UniqueID:      0x00
DataFieldID:   0x02 (FTCAN_2_0)
MessageID:     0x1FF (High priority broadcast)

Calculation:
  ProductID = (0x0240 << 5) | 0x00 = 0x4800
  CAN ID = (0x4800 << 14) | (0x02 << 11) | 0x1FF
  CAN ID = 0x12001000 | 0x1000 | 0x1FF
  CAN ID = 0x1240A7FF
```

---

## Decoding Examples

### Example 1: Single Measure (Lambda)

**Raw CAN Message:**
```
ID:   0x1240A7FF (extended)
Data: FF 00 27 03 52 00 00 00
```

**Decoding:**
```
1. Parse Identification (0x1240A7FF):
   ProductID     = (0x1240A7FF >> 14) & 0x7FFF = 0x4800
   ProductTypeID = 0x4800 >> 5 = 0x0240 (WBO2_NANO)
   UniqueID      = 0x4800 & 0x1F = 0x00
   DataFieldID   = (0x1240A7FF >> 11) & 0x07 = 0x02 (FTCAN_2_0)
   MessageID     = 0x1240A7FF & 0x7FF = 0x1FF (High priority)

2. Parse Data Field:
   Byte 0 = 0xFF → Single packet
   
3. Parse Measure (bytes 1-4):
   MeasureID = 0x0027 (big-endian)
   DataID    = 0x0027 >> 1 = 0x0013 (Cylinder 1 O2)
   IsStatus  = 0x0027 & 0x01 = 1
   
   Value     = 0x0352 (850 decimal, signed)
   Multiplier = 0.001 (from DataID 0x0013)
   Real Value = 850 × 0.001 = 0.850λ

Result: "WBO2_NANO #0: Cylinder 1 O2 = 0.850λ"
```

### Example 2: Multiple Measures (ECU)

**Raw CAN Message:**
```
ID:   0x14028BFF (FT600 ECU #0)
Data: FF 00 84 0D AC 00 02 01
```

**Decoding:**
```
Byte 0 = 0xFF → Single packet

Measure 1 (bytes 1-4):
  MeasureID = 0x0084
  DataID    = 0x0084 >> 1 = 0x0042 (ECU RPM)
  Value     = 0x0DAC (3500 decimal)
  Real      = 3500 × 1 = 3500 RPM

Measure 2 (bytes 5-8):
  MeasureID = 0x0002
  DataID    = 0x0002 >> 1 = 0x0001 (TPS)
  Value     = 0x01F4 (500 decimal)
  Real      = 500 × 0.1 = 50.0%

Result: "FT600_ECU #0: RPM=3500, TPS=50.0%"
```

### Example 3: Segmented Packet

**Frame 1 (First):**
```
ID:   0x1240A7FF
Data: 00 00 14 [5 bytes payload]
      │  └──┘
      │   └─ Total length = 0x0014 (20 bytes)
      └─ First frame marker
```

**Frame 2 (Continuation):**
```
ID:   0x1240A7FF
Data: 01 [7 bytes payload]
      └─ Sequence #1
```

**Frame 3 (Continuation):**
```
ID:   0x1240A7FF
Data: 02 [7 bytes payload]
      └─ Sequence #2
```

**Reassembly:**
```
Total payload = 5 + 7 + 7 = 19 bytes
(matches declared length of 20, with 1 byte padding)
```

---

## Troubleshooting

### No Messages Detected

**Check:**
1. ✅ Baudrate is exactly **1 Mbps** (not 500k or 250k)
2. ✅ Extended ID (29-bit) support enabled
3. ✅ CAN-H and CAN-L connected correctly
4. ✅ 120Ω termination at both ends
5. ✅ Device is powered (12V)

**Test:**
```bash
# Linux - monitor raw CAN traffic
candump can0

# Should see extended IDs starting with 0x12...
```

### Messages Not Decoded

**Check:**
1. ✅ FTCAN decoder is enabled
2. ✅ ProductTypeID is recognized (see Supported Devices)
3. ✅ Open FTCAN Analyzer dialog
4. ✅ Check "Diagnostics" tab for errors

**Debug:**
```
Diagnostics Tab:
  - Unknown ProductIDs: Lists unrecognized devices
  - Decoding Errors: Shows parsing failures
  - Message Statistics: Verify traffic rate
```

### Incorrect Values

**Check:**
1. ✅ Byte order is big-endian
2. ✅ Correct multiplier applied
3. ✅ Value is signed 16-bit
4. ✅ MeasureID bit 0 (IsStatus) handled correctly

**Example Issue:**
```
Wrong: value = data[0] | (data[1] << 8)  # Little-endian
Right: value = (data[0] << 8) | data[1]  # Big-endian
```

### Segmented Packets Not Reassembling

**Check:**
1. ✅ All frames have same CAN ID
2. ✅ Sequence is complete (0x00, 0x01, 0x02, ...)
3. ✅ Total length matches actual payload
4. ✅ No frames lost (check CAN bus load)

---

## Official Documentation

### Primary Reference

**FTCAN 2.0 Protocol Specification (Public Release R026)**
- **URL:** https://files.fueltech.net/manuals/Protocol_FTCAN20_Public_R026.pdf
- **Publisher:** FuelTech
- **Release:** R026 (August 24, 2022)
- **Language:** English
- **Pages:** 30

**Document Contents:**
- Physical layer specifications
- Complete identification structure
- Data field layouts (0x00-0x03)
- Segmentation protocol
- Complete MeasureID list (0x0000-0x01B8)
- Simplified broadcast packets
- ProductID list
- Connector pinouts
- Detailed examples

### Additional Resources

**FuelTech Official:**
- **Website (Brazil):** https://www.fueltech.com.br/
- **Website (International):** https://www.fueltech.net/
- **Support:** +55 (51) 3019-0500 (Brazil), +1 (670) 493-3835 (International)

**WB-O2 Nano Manual:**
- Available at FuelTech website
- Includes wiring diagrams, specifications, and configuration

### Related Standards

- **CAN 2.0B Specification:** ISO 11898-1
- **Extended Frame Format:** 29-bit identifiers
- **Physical Layer:** ISO 11898-2 (High-speed CAN)

---

## Implementation Files

### Source Code

| File | Purpose | Lines |
|------|---------|-------|
| `src/decoders/ftcan_decoder.py` | Core decoder logic | ~394 |
| `src/decoders/ftcan_protocol_decoder.py` | Protocol adapter | ~85 |
| `src/dialogs_ftcan.py` | User interface | ~569 |

### Tools

| File | Purpose |
|------|---------|
| `tools/ftcan/ftcan_simulator.py` | Message simulator for testing |
| `tools/ftcan/ftcan_config_capture.py` | Configuration capture tool |

---

## Quick Reference

### Calculate CAN ID

```python
def create_ftcan_id(product_type_id, unique_id, data_field_id, message_id):
    product_id = (product_type_id << 5) | (unique_id & 0x1F)
    can_id = (product_id << 14) | ((data_field_id & 0x07) << 11) | (message_id & 0x7FF)
    return can_id

# Example: WB-O2 Nano #0, high priority broadcast
can_id = create_ftcan_id(0x0240, 0x00, 0x02, 0x1FF)
# Result: 0x1240A7FF
```

### Parse CAN ID

```python
def parse_ftcan_id(can_id):
    product_id = (can_id >> 14) & 0x7FFF
    product_type_id = (product_id >> 5) & 0x3FF
    unique_id = product_id & 0x1F
    data_field_id = (can_id >> 11) & 0x07
    message_id = can_id & 0x7FF
    is_response = bool((message_id >> 10) & 0x01)
    
    return {
        'product_type_id': product_type_id,
        'unique_id': unique_id,
        'data_field_id': data_field_id,
        'message_id': message_id,
        'is_response': is_response
    }
```

### Decode Measure

```python
def decode_measure(data, offset=0):
    # Big-endian
    measure_id = (data[offset] << 8) | data[offset+1]
    value = struct.unpack('>h', data[offset+2:offset+4])[0]  # Signed
    
    data_id = (measure_id >> 1) & 0x7FFF
    is_status = bool(measure_id & 0x01)
    
    # Apply multiplier
    multiplier = MEASURE_IDS[data_id]['multiplier']
    real_value = value * multiplier
    
    return {
        'data_id': data_id,
        'name': MEASURE_IDS[data_id]['name'],
        'value': real_value,
        'unit': MEASURE_IDS[data_id]['unit'],
        'is_status': is_status
    }
```

---

## Testing

### Using Simulator

```bash
cd tools/ftcan
python3 ftcan_simulator.py

# Menu:
1. WB-O2 Nano (Lambda readings)
2. FT600 ECU (Multiple measures)
3. Standard CAN (Non-FTCAN)
4. Segmented Packet
5. Run all simulations
```

### Expected Output

```
FTCAN 2.0 Simulator - WB-O2 Nano
Device: WB-O2 Nano #0
CAN ID: 0x1240A7FF

Lambda: 0.850 - Rich - Max Power
  Raw Data: FF002703520000000000
  Decoded: Cylinder 1 O2: 0.850 λ
```

### Verify in CAN Analyzer

1. Run simulator
2. Open FTCAN Analyzer
3. Check "Decoded Messages" tab
4. Should see: "WBO2_NANO #0: Cylinder 1 O2 = 0.850λ"

---

## Performance Notes

### Broadcast Rates

| Data Type | Rate | Example |
|-----------|------|---------|
| Critical | 1000 Hz | Ignition cut, 2-step |
| High | 100 Hz | RPM, TPS, MAP, lambda |
| Medium | 10 Hz | Temperatures, pressures |
| Low | 0.5-1 Hz | Configuration data |

**Note:** ECU broadcast rate may vary under high RPM conditions.

### Bus Load

**Typical scenario (FT600 ECU + 2× WB-O2 Nano):**
- ECU: ~50 messages/sec (various priorities)
- Each Nano: ~10 messages/sec (lambda readings)
- **Total:** ~70 messages/sec
- **Bus load:** ~5-10% @ 1 Mbps

**Maximum theoretical:**
- 1 Mbps = 1,000,000 bits/sec
- CAN frame ≈ 130 bits (extended, 8 bytes)
- Max frames ≈ 7,700 frames/sec
- FTCAN typical usage: < 1% of maximum

---

## License

**CAN Bus Analyzer:** Open-source (see main repository)

**FTCAN 2.0 Protocol:** © FuelTech - Public specification document provided by manufacturer for integration purposes.

---

## Changelog

### v1.0.0 (2026-02-06)
- ✅ Complete protocol documentation
- ✅ Technical specifications
- ✅ Identification structure explained
- ✅ Data field layouts documented
- ✅ Measure ID reference
- ✅ Decoding examples
- ✅ Implementation guide
- ✅ Official documentation reference

---

## Contributing

To improve this documentation:

1. **Found an error?** Open an issue with details
2. **Have a suggestion?** Create a pull request
3. **Discovered new DataIDs?** Share your findings
4. **Tested with new devices?** Document your experience

---

## Related Documentation

- **Main README:** `../../README.md`
- **Tools Documentation:** `../../tools/ftcan/README.md`
- **General CAN Tools:** `../../tools/general/README.md`
- **Arduino Tools:** `../../tools/arduino/README.md`

---

## Support

- **GitHub Issues:** For bugs and feature requests
- **Documentation:** This directory
- **FuelTech Official:** https://www.fueltech.com.br/
- **Protocol Spec:** https://files.fueltech.net/manuals/Protocol_FTCAN20_Public_R026.pdf
