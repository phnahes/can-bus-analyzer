# OBD-II Protocol Documentation

Complete technical documentation for OBD-II (On-Board Diagnostics II) protocol support in CAN Bus Analyzer.

---

## Contents

- [Protocol Overview](#protocol-overview)
- [Technical Specifications](#technical-specifications)
- [Request/Response Model](#requestresponse-model)
- [Message Structure](#message-structure)
- [Services (Modes)](#services-modes)
- [Parameter IDs (PIDs)](#parameter-ids-pids)
- [Diagnostic Trouble Codes (DTCs)](#diagnostic-trouble-codes-dtcs)
- [Multi-Frame Messages (ISO-TP)](#multi-frame-messages-iso-tp)
- [Implementation](#implementation)
- [Usage Guide](#usage-guide)
- [Troubleshooting](#troubleshooting)
- [Official Standards](#official-standards)

---

## Protocol Overview

**OBD-II (On-Board Diagnostics II)** is a standardized automotive diagnostic protocol mandated in the United States since 1996 for all vehicles. It provides access to vehicle diagnostic data, emission-related information, and real-time parameters.

### Key Features

- **Physical Layer:** ISO 15765-4 (CAN)
- **Bitrate:** 500 kbps (most common) or 250 kbps
- **Communication Model:** Request/Response (polling required)
- **ID Format:** CAN 2.0A Standard (11-bit IDs)
- **Byte Order:** Big-endian (most significant byte first)
- **Standardization:** ISO 15765, SAE J1979, ISO 9141

### Why OBD-II?

1. **Universal Standard:** Works with virtually all vehicles manufactured after 1996
2. **Diagnostic Access:** Read and clear fault codes (DTCs)
3. **Real-Time Data:** Monitor engine parameters, sensors, and emissions
4. **Emission Compliance:** Required for emission testing and certification
5. **Aftermarket Support:** Enables third-party diagnostic tools and apps

### OBD-II vs Proprietary Protocols

| Aspect | OBD-II | Proprietary (e.g., FTCAN) |
|--------|--------|---------------------------|
| **Standardization** | ✅ ISO/SAE standard | ❌ Manufacturer-specific |
| **Compatibility** | ✅ Universal (1996+) | ❌ Limited to brand |
| **Data Access** | Request/Response | Broadcast |
| **Latency** | ~100ms per request | ~10ms continuous |
| **Bandwidth Usage** | Low (on-demand) | High (continuous) |
| **Diagnostic Codes** | ✅ DTCs included | ❌ Usually not included |

---

## Technical Specifications

### Physical Layer

- **Protocol:** ISO 15765-4 (CAN for OBD)
- **Bitrate:** 500,000 bps (500 kbps) - most common
  - Alternative: 250,000 bps (250 kbps) - some vehicles
- **Frame Type:** Standard (11-bit identifier)
- **Data Length:** 0-8 bytes per frame
- **Byte Order:** Big-endian
- **Termination:** 120Ω resistors at both ends

### CAN Frame Structure

```
┌─────────────────────────────────────────────────┐
│            CAN 2.0A Standard Frame              │
├──────────────────────────┬──────────────────────┤
│    IDENTIFICATION        │     DATA FIELD       │
│      (11 bits)           │     (0-8 bytes)      │
└──────────────────────────┴──────────────────────┘
```

### CAN IDs for OBD-II

| ID Range | Direction | Description |
|----------|-----------|-------------|
| **0x7DF** | Request | Broadcast (all ECUs) |
| **0x7E0-0x7E7** | Request | Physical addressing (specific ECU) |
| **0x7E8-0x7EF** | Response | ECU responses (8 ECUs max) |

**Mapping:**
- Request to ECU #1: `0x7E0` → Response from ECU #1: `0x7E8`
- Request to ECU #2: `0x7E1` → Response from ECU #2: `0x7E9`
- ...
- Broadcast: `0x7DF` → Any ECU can respond

### Communication Model

**OBD-II is NOT a broadcast protocol!** It requires active polling:

```
┌─────────────┐                          ┌─────────────┐
│  Diagnostic │                          │   Vehicle   │
│    Tool     │                          │     ECU     │
└──────┬──────┘                          └──────┬──────┘
       │                                        │
       │  1. Send Request (0x7DF)              │
       │  [Service] [PID] [Parameters...]      │
       ├──────────────────────────────────────>│
       │                                        │
       │                                        │ 2. Process
       │                                        │    Request
       │                                        │
       │  3. Send Response (0x7E8-0x7EF)       │
       │  [Service+0x40] [PID] [Data...]       │
       │<──────────────────────────────────────┤
       │                                        │
       │  4. Decode Response                   │
       │                                        │
```

**Important:** You must send a request for each parameter you want to read. There is no automatic broadcast like FTCAN.

---

## Request/Response Model

### Request Format

**CAN ID:** `0x7DF` (broadcast) or `0x7E0-0x7E7` (specific ECU)

**Data Field (8 bytes):**

```
┌─────┬─────────┬─────┬──────────────────────────┐
│  0  │    1    │  2  │  3  │  4  │  5  │  6  │  7  │
├─────┼─────────┼─────┼─────┼─────┼─────┼─────┼─────┤
│ Len │ Service │ PID │ Param (optional)         │
│     │  Mode   │     │ or Padding (0x00/0xCC)   │
└─────┴─────────┴─────┴──────────────────────────┘
```

**Fields:**
- **Byte 0 (Length):** Number of following data bytes (1-7)
- **Byte 1 (Service):** OBD service/mode (0x01-0x0A)
- **Byte 2 (PID):** Parameter ID (0x00-0xFF)
- **Bytes 3-7:** Additional parameters or padding

### Response Format

**CAN ID:** `0x7E8-0x7EF` (ECU response)

**Data Field (8 bytes):**

```
┌─────┬─────────┬─────┬──────────────────────────┐
│  0  │    1    │  2  │  3  │  4  │  5  │  6  │  7  │
├─────┼─────────┼─────┼─────┼─────┼─────┼─────┼─────┤
│ Len │Service+0│ PID │ Data Bytes               │
│     │   0x40  │     │ (PID-specific format)    │
└─────┴─────────┴─────┴──────────────────────────┘
```

**Fields:**
- **Byte 0 (Length):** Number of following data bytes
- **Byte 1 (Service):** Original service + 0x40 (e.g., 0x01 → 0x41)
- **Byte 2 (PID):** Echo of requested PID
- **Bytes 3-7:** PID data (format varies by PID)

### Example: Reading Engine RPM

**Request:**
```
CAN ID:  0x7DF (broadcast)
Data:    02 01 0C 00 00 00 00 00
         │  │  │  └──────────────── Padding
         │  │  └─────────────────── PID 0x0C (Engine RPM)
         │  └────────────────────── Service 0x01 (Current Data)
         └───────────────────────── Length = 2 bytes
```

**Response:**
```
CAN ID:  0x7E8 (ECU #1)
Data:    04 41 0C 1A F8 00 00 00
         │  │  │  └──┴──┴──────────── Padding
         │  │  │  └──┴──────────────── Value = 0x1AF8
         │  │  └─────────────────────── PID 0x0C (echo)
         │  └────────────────────────── Service 0x41 (0x01 + 0x40)
         └───────────────────────────── Length = 4 bytes

Calculation:
  RPM = (0x1AF8) / 4
  RPM = 6904 / 4
  RPM = 1726 RPM
```

---

## Message Structure

### Single Frame (Most Common)

For data that fits in one CAN frame (up to 7 bytes of payload):

```
┌──────────────────────────────────────────────────┐
│              Single Frame Format                 │
├─────┬────────┬─────┬───────────────────────────┤
│  0  │   1    │  2  │  3-7                      │
├─────┼────────┼─────┼───────────────────────────┤
│ Len │Service │ PID │ Data (up to 5 bytes)      │
│     │ +0x40  │     │                           │
└─────┴────────┴─────┴───────────────────────────┘
```

**Example - Coolant Temperature:**
```
Data: 03 41 05 50 00 00 00 00
      │  │  │  │  └──────────── Padding
      │  │  │  └─────────────── Value = 0x50 (80 decimal)
      │  │  └────────────────── PID 0x05
      │  └───────────────────── Service 0x41
      └──────────────────────── Length = 3

Temperature = 80 - 40 = 40°C
```

### Multi-Frame (ISO-TP)

For data larger than 7 bytes (e.g., DTCs, VIN), ISO 15765-2 (ISO-TP) is used:

#### First Frame

```
┌──────────────────────────────────────────────────┐
│               First Frame Format                 │
├─────┬────────┬──────────────────────────────────┤
│  0  │   1    │  2-7                             │
├─────┼────────┼──────────────────────────────────┤
│ 1N  │ NN     │ Data (first 6 bytes)             │
│ │   │ └────── Total length (lower byte)         │
│ └──────────── Frame type (1) + length (upper 4 bits)
└─────┴────────┴──────────────────────────────────┘
```

**Byte 0:**
- Bits 7-4: `0x1` (First Frame indicator)
- Bits 3-0: Total length (upper 4 bits)

**Byte 1:** Total length (lower 8 bits)

**Example:**
```
Data: 10 14 49 02 01 31 47 31
      │  │  └──┴──┴──┴──┴──────── First 6 bytes of payload
      │  └─────────────────────── Total length = 0x14 (20 bytes)
      └────────────────────────── First Frame (0x1) + length upper bits (0x0)
```

#### Consecutive Frames

```
┌──────────────────────────────────────────────────┐
│            Consecutive Frame Format              │
├─────┬────────────────────────────────────────────┤
│  0  │  1-7                                       │
├─────┼────────────────────────────────────────────┤
│ 2N  │ Data (7 bytes)                             │
│ │   │                                            │
│ └──── Frame type (2) + sequence number (0-F)    │
└─────┴────────────────────────────────────────────┘
```

**Byte 0:**
- Bits 7-4: `0x2` (Consecutive Frame indicator)
- Bits 3-0: Sequence number (0x0-0xF, wraps around)

**Example:**
```
Frame 1: 21 4A 4A 4D 31 45 4A 38
         │  └──┴──┴──┴──┴──┴──────── Next 7 bytes
         └─────────────────────────── Consecutive Frame, sequence 1

Frame 2: 22 41 30 30 31 32 33 34
         │  └──┴──┴──┴──┴──┴──┴──────── Next 7 bytes
         └─────────────────────────── Consecutive Frame, sequence 2
```

#### Flow Control (Optional)

The diagnostic tool can send flow control to manage data flow:

```
┌──────────────────────────────────────────────────┐
│             Flow Control Format                  │
├─────┬─────┬─────┬────────────────────────────────┤
│  0  │  1  │  2  │  3-7                           │
├─────┼─────┼─────┼────────────────────────────────┤
│ 30  │ BS  │ ST  │ Padding                        │
│     │     │     │                                │
└─────┴─────┴─────┴────────────────────────────────┘
```

- **Byte 0:** `0x30` (Continue to Send)
- **Byte 1:** Block Size (number of frames before next FC)
- **Byte 2:** Separation Time (minimum delay between frames)

---

## Services (Modes)

OBD-II defines 10 standard services (modes) for different types of data access.

### Service 0x01: Show Current Data

**Description:** Read real-time sensor data and calculated values.

**Request:**
```
[0x02, 0x01, PID, 0x00, ...]
```

**Response:**
```
[Length, 0x41, PID, Data...]
```

**Common PIDs:**
- 0x00: Supported PIDs (01-20)
- 0x0C: Engine RPM
- 0x0D: Vehicle Speed
- 0x05: Coolant Temperature
- 0x11: Throttle Position

**Use Case:** Real-time monitoring, dashboards, telemetry

---

### Service 0x02: Show Freeze Frame Data

**Description:** Read snapshot of data when a DTC was set.

**Request:**
```
[0x03, 0x02, PID, Frame#, 0x00, ...]
```

**Response:**
```
[Length, 0x42, PID, Frame#, Data...]
```

**Use Case:** Diagnose conditions that triggered a fault code

---

### Service 0x03: Show Stored DTCs

**Description:** Read all stored Diagnostic Trouble Codes.

**Request:**
```
[0x01, 0x03, 0x00, 0x00, ...]
```

**Response (Multi-frame):**
```
First Frame:  [0x10, Length, 0x43, Count, DTC1_H, DTC1_L, ...]
Consecutive:  [0x21, DTC2_H, DTC2_L, DTC3_H, DTC3_L, ...]
```

**DTC Format:** 2 bytes per code
- Byte 1: Type + first character
- Byte 2: Last 3 digits (hex)

**Example:**
```
DTC: P0171 (System Too Lean - Bank 1)
  Byte 1: 0x01 (P = Powertrain, 0 = SAE)
  Byte 2: 0x71 (171 in hex)
  Encoded: 0x0171
```

**Use Case:** Check engine light diagnostics

---

### Service 0x04: Clear DTCs

**Description:** Clear all stored DTCs and freeze frame data.

**Request:**
```
[0x01, 0x04, 0x00, 0x00, ...]
```

**Response:**
```
[0x01, 0x44, 0x00, 0x00, ...]
```

**Warning:** This will turn off the check engine light and reset readiness monitors!

**Use Case:** After repairs, emission testing

---

### Service 0x05: O2 Sensor Monitoring

**Description:** Read O2 sensor test results (non-CAN vehicles).

**Request:**
```
[0x02, 0x05, TID, 0x00, ...]
```

**Response:**
```
[Length, 0x45, TID, Data...]
```

**Use Case:** Emission testing, O2 sensor diagnostics

---

### Service 0x06: On-Board Monitoring

**Description:** Read test results for specific monitored systems.

**Request:**
```
[0x02, 0x06, TID, 0x00, ...]
```

**Response:**
```
[Length, 0x46, TID, Data...]
```

**Use Case:** Emission testing, catalyst efficiency

---

### Service 0x07: Show Pending DTCs

**Description:** Read DTCs detected but not yet confirmed.

**Request:**
```
[0x01, 0x07, 0x00, 0x00, ...]
```

**Response:**
```
[Length, 0x47, Count, DTC1_H, DTC1_L, ...]
```

**Use Case:** Early fault detection, intermittent issues

---

### Service 0x08: Control On-Board Systems

**Description:** Control certain vehicle systems (test mode).

**Request:**
```
[0x02, 0x08, TID, 0x00, ...]
```

**Response:**
```
[Length, 0x48, TID, Data...]
```

**Use Case:** Actuator tests, EVAP purge valve

---

### Service 0x09: Vehicle Information

**Description:** Read vehicle identification and calibration data.

**Request:**
```
[0x02, 0x09, InfoType, 0x00, ...]
```

**Response (Usually Multi-frame):**
```
[0x10, Length, 0x49, InfoType, Data...]
```

**Common Info Types:**
- 0x02: VIN (Vehicle Identification Number)
- 0x04: Calibration ID
- 0x06: CVN (Calibration Verification Number)
- 0x0A: ECU Name

**Example - VIN:**
```
Request:  [0x02, 0x09, 0x02, 0x00, ...]
Response: [0x10, 0x14, 0x49, 0x02, 0x01, '1', 'G', '1', ...]
          (Multi-frame: "1G1JC5444R7252367")
```

**Use Case:** Vehicle identification, calibration verification

---

### Service 0x0A: Permanent DTCs

**Description:** Read permanent DTCs (cannot be cleared by Service 0x04).

**Request:**
```
[0x01, 0x0A, 0x00, 0x00, ...]
```

**Response:**
```
[Length, 0x4A, Count, DTC1_H, DTC1_L, ...]
```

**Note:** Permanent DTCs clear automatically after successful drive cycles.

**Use Case:** Emission testing compliance

---

## Parameter IDs (PIDs)

### PID Structure

Each PID represents a specific parameter. PIDs are organized in groups of 32, with "support PIDs" indicating which PIDs are available.

### Support PIDs

| PID | Description |
|-----|-------------|
| 0x00 | PIDs supported (01-20) |
| 0x20 | PIDs supported (21-40) |
| 0x40 | PIDs supported (41-60) |
| 0x60 | PIDs supported (61-80) |
| 0x80 | PIDs supported (81-A0) |
| 0xA0 | PIDs supported (A1-C0) |
| 0xC0 | PIDs supported (C1-E0) |
| 0xE0 | PIDs supported (E1-FF) |

**Format:** 4 bytes (32 bits), each bit represents one PID.

**Example:**
```
Request:  [0x02, 0x01, 0x00, 0x00, ...]
Response: [0x06, 0x41, 0x00, 0xBF, 0xBF, 0xA8, 0x91, 0x00]
                              └──┴──┴──┴──┴──── 32-bit bitmap

Bitmap: 0xBFBFA891
  Bit 0 (PID 0x01): 1 = Supported
  Bit 1 (PID 0x02): 0 = Not supported
  Bit 2 (PID 0x03): 0 = Not supported
  Bit 3 (PID 0x04): 1 = Supported
  ...
```

### PID Categories

#### Engine Basic

| PID | Name | Bytes | Formula | Unit | Range |
|-----|------|-------|---------|------|-------|
| 0x04 | Calculated Engine Load | 1 | A × 100/255 | % | 0-100 |
| 0x05 | Coolant Temperature | 1 | A - 40 | °C | -40 to 215 |
| 0x0C | Engine RPM | 2 | ((A×256)+B)/4 | RPM | 0-16,383 |
| 0x0D | Vehicle Speed | 1 | A | km/h | 0-255 |
| 0x0F | Intake Air Temperature | 1 | A - 40 | °C | -40 to 215 |
| 0x11 | Throttle Position | 1 | A × 100/255 | % | 0-100 |
| 0x21 | Distance with MIL On | 2 | (A×256)+B | km | 0-65,535 |
| 0x2F | Fuel Tank Level | 1 | A × 100/255 | % | 0-100 |
| 0x31 | Distance Since Codes Cleared | 2 | (A×256)+B | km | 0-65,535 |
| 0x46 | Ambient Air Temperature | 1 | A - 40 | °C | -40 to 215 |

#### Fuel System

| PID | Name | Bytes | Formula | Unit | Range |
|-----|------|-------|---------|------|-------|
| 0x03 | Fuel System Status | 2 | Bit-encoded | - | See spec |
| 0x06 | Short Term Fuel Trim Bank 1 | 1 | (A-128) × 100/128 | % | -100 to 99.2 |
| 0x07 | Long Term Fuel Trim Bank 1 | 1 | (A-128) × 100/128 | % | -100 to 99.2 |
| 0x08 | Short Term Fuel Trim Bank 2 | 1 | (A-128) × 100/128 | % | -100 to 99.2 |
| 0x09 | Long Term Fuel Trim Bank 2 | 1 | (A-128) × 100/128 | % | -100 to 99.2 |
| 0x0A | Fuel Pressure | 1 | A × 3 | kPa | 0-765 |
| 0x22 | Fuel Rail Pressure (Gauge) | 2 | ((A×256)+B) × 0.079 | kPa | 0-5,177 |
| 0x23 | Fuel Rail Pressure (Diesel) | 2 | ((A×256)+B) × 10 | kPa | 0-655,350 |
| 0x51 | Fuel Type | 1 | Lookup table | - | See spec |
| 0x52 | Ethanol Fuel % | 1 | A × 100/255 | % | 0-100 |
| 0x5E | Engine Fuel Rate | 2 | ((A×256)+B) × 0.05 | L/h | 0-3,212 |

#### Air Intake

| PID | Name | Bytes | Formula | Unit | Range |
|-----|------|-------|---------|------|-------|
| 0x0B | Intake Manifold Pressure | 1 | A | kPa | 0-255 |
| 0x10 | MAF Air Flow Rate | 2 | ((A×256)+B) / 100 | g/s | 0-655.35 |
| 0x1F | Run Time Since Engine Start | 2 | (A×256)+B | s | 0-65,535 |
| 0x33 | Barometric Pressure | 1 | A | kPa | 0-255 |
| 0x4F | Maximum MAF | 1 | A × 10 | g/s | 0-2,550 |

#### Lambda / O2 Sensors

| PID | Name | Bytes | Formula | Unit | Range |
|-----|------|-------|---------|------|-------|
| 0x14 | O2 Sensor 1 Bank 1 | 2 | A/200, (B-128)×100/128 | V, % | 0-1.275V, -100 to 99.2% |
| 0x15 | O2 Sensor 2 Bank 1 | 2 | A/200, (B-128)×100/128 | V, % | 0-1.275V, -100 to 99.2% |
| 0x16 | O2 Sensor 3 Bank 1 | 2 | A/200, (B-128)×100/128 | V, % | 0-1.275V, -100 to 99.2% |
| 0x17 | O2 Sensor 4 Bank 1 | 2 | A/200, (B-128)×100/128 | V, % | 0-1.275V, -100 to 99.2% |
| 0x18 | O2 Sensor 1 Bank 2 | 2 | A/200, (B-128)×100/128 | V, % | 0-1.275V, -100 to 99.2% |
| 0x19 | O2 Sensor 2 Bank 2 | 2 | A/200, (B-128)×100/128 | V, % | 0-1.275V, -100 to 99.2% |
| 0x1A | O2 Sensor 3 Bank 2 | 2 | A/200, (B-128)×100/128 | V, % | 0-1.275V, -100 to 99.2% |
| 0x1B | O2 Sensor 4 Bank 2 | 2 | A/200, (B-128)×100/128 | V, % | 0-1.275V, -100 to 99.2% |
| 0x24 | O2 Sensor 1 Lambda | 4 | ((A×256)+B)/32768, ((C×256)+D)/8192 | λ, V | 0-2, 0-8V |
| 0x25 | O2 Sensor 2 Lambda | 4 | ((A×256)+B)/32768, ((C×256)+D)/8192 | λ, V | 0-2, 0-8V |
| 0x26 | O2 Sensor 3 Lambda | 4 | ((A×256)+B)/32768, ((C×256)+D)/8192 | λ, V | 0-2, 0-8V |
| 0x27 | O2 Sensor 4 Lambda | 4 | ((A×256)+B)/32768, ((C×256)+D)/8192 | λ, V | 0-2, 0-8V |
| 0x28 | O2 Sensor 5 Lambda | 4 | ((A×256)+B)/32768, ((C×256)+D)/8192 | λ, V | 0-2, 0-8V |
| 0x29 | O2 Sensor 6 Lambda | 4 | ((A×256)+B)/32768, ((C×256)+D)/8192 | λ, V | 0-2, 0-8V |
| 0x2A | O2 Sensor 7 Lambda | 4 | ((A×256)+B)/32768, ((C×256)+D)/8192 | λ, V | 0-2, 0-8V |
| 0x2B | O2 Sensor 8 Lambda | 4 | ((A×256)+B)/32768, ((C×256)+D)/8192 | λ, V | 0-2, 0-8V |
| 0x34 | O2 Sensor 1 Lambda (Current) | 4 | ((A×256)+B)/32768, ((C×256)+D)/256-128 | λ, mA | 0-2, -128 to 128mA |
| 0x35 | O2 Sensor 2 Lambda (Current) | 4 | ((A×256)+B)/32768, ((C×256)+D)/256-128 | λ, mA | 0-2, -128 to 128mA |
| 0x36 | O2 Sensor 3 Lambda (Current) | 4 | ((A×256)+B)/32768, ((C×256)+D)/256-128 | λ, mA | 0-2, -128 to 128mA |
| 0x37 | O2 Sensor 4 Lambda (Current) | 4 | ((A×256)+B)/32768, ((C×256)+D)/256-128 | λ, mA | 0-2, -128 to 128mA |
| 0x38 | O2 Sensor 5 Lambda (Current) | 4 | ((A×256)+B)/32768, ((C×256)+D)/256-128 | λ, mA | 0-2, -128 to 128mA |
| 0x39 | O2 Sensor 6 Lambda (Current) | 4 | ((A×256)+B)/32768, ((C×256)+D)/256-128 | λ, mA | 0-2, -128 to 128mA |
| 0x3A | O2 Sensor 7 Lambda (Current) | 4 | ((A×256)+B)/32768, ((C×256)+D)/256-128 | λ, mA | 0-2, -128 to 128mA |
| 0x3B | O2 Sensor 8 Lambda (Current) | 4 | ((A×256)+B)/32768, ((C×256)+D)/256-128 | λ, mA | 0-2, -128 to 128mA |
| 0x44 | Commanded Equivalence Ratio | 2 | ((A×256)+B)/32768 | λ | 0-2 |

#### Advanced / Performance

| PID | Name | Bytes | Formula | Unit | Range |
|-----|------|-------|---------|------|-------|
| 0x42 | Control Module Voltage | 2 | ((A×256)+B)/1000 | V | 0-65.535 |
| 0x43 | Absolute Load Value | 2 | ((A×256)+B) × 100/255 | % | 0-25,700 |
| 0x45 | Relative Throttle Position | 1 | A × 100/255 | % | 0-100 |
| 0x47 | Absolute Throttle Position B | 1 | A × 100/255 | % | 0-100 |
| 0x48 | Absolute Throttle Position C | 1 | A × 100/255 | % | 0-100 |
| 0x49 | Accelerator Pedal Position D | 1 | A × 100/255 | % | 0-100 |
| 0x4A | Accelerator Pedal Position E | 1 | A × 100/255 | % | 0-100 |
| 0x4B | Accelerator Pedal Position F | 1 | A × 100/255 | % | 0-100 |
| 0x4C | Commanded Throttle Actuator | 1 | A × 100/255 | % | 0-100 |
| 0x5C | Engine Oil Temperature | 1 | A - 40 | °C | -40 to 210 |
| 0x5D | Fuel Injection Timing | 2 | (((A×256)+B)-26,880)/128 | ° | -210 to 301.99 |
| 0x61 | Driver's Demand Torque | 1 | A - 125 | % | -125 to 130 |
| 0x62 | Actual Engine Torque | 1 | A - 125 | % | -125 to 130 |
| 0x63 | Engine Reference Torque | 2 | (A×256)+B | Nm | 0-65,535 |

**Total Supported:** 60+ PIDs in CAN Analyzer implementation

---

## Diagnostic Trouble Codes (DTCs)

### DTC Format

DTCs are 5-character alphanumeric codes: **P0171**

**Structure:**
```
┌───┬───┬───┬───┬───┐
│ P │ 0 │ 1 │ 7 │ 1 │
└─┬─┴─┬─┴───┴───┴───┘
  │   │   └─────────── Specific fault (000-999)
  │   └─────────────── System (0-3)
  └─────────────────── Type (P, C, B, U)
```

### DTC Types

| Prefix | Type | Description |
|--------|------|-------------|
| **P** | Powertrain | Engine, transmission |
| **C** | Chassis | ABS, suspension, steering |
| **B** | Body | Airbags, climate control |
| **U** | Network | CAN bus communication |

### System Codes (Second Character)

| Code | Standard | Description |
|------|----------|-------------|
| **P0xxx** | SAE | Generic (all manufacturers) |
| **P1xxx** | Manufacturer | Manufacturer-specific |
| **P2xxx** | SAE | Generic (fuel/air) |
| **P3xxx** | SAE/Mfr | Mixed |

### Encoding in CAN

DTCs are encoded as 2 bytes:

```
┌─────────────────────────────────────────────────┐
│              DTC Encoding (2 bytes)             │
├──────────┬──────────────────────────────────────┤
│  Byte 1  │  Byte 2                              │
├──────────┼──────────────────────────────────────┤
│  TT SS   │  NN NN                               │
│  │  │    │  └──┴─── Last 2 digits (hex)        │
│  │  └────┴───────── System (0-3)                │
│  └────────────────── Type (00=P, 01=C, 10=B, 11=U)
└──────────┴──────────────────────────────────────┘
```

**Example: P0171**
```
Type:   P (Powertrain) = 00
System: 0 (SAE)        = 00
Code:   171 (hex)      = 0x71

Byte 1: 00 00 00 00 = 0x01
        ││ └┴─────── System (00)
        └┴─────────── Type (00 = P)

Byte 2: 0x71

Encoded: 0x0171
```

**Example: C0035**
```
Type:   C (Chassis) = 01
System: 0 (SAE)     = 00
Code:   035 (hex)   = 0x35

Byte 1: 01 00 00 00 = 0x40
        ││ └┴─────── System (00)
        └┴─────────── Type (01 = C)

Byte 2: 0x35

Encoded: 0x4035
```

### Common DTCs

#### Powertrain (P0xxx)

| Code | Description |
|------|-------------|
| P0171 | System Too Lean (Bank 1) |
| P0172 | System Too Rich (Bank 1) |
| P0174 | System Too Lean (Bank 2) |
| P0175 | System Too Rich (Bank 2) |
| P0300 | Random/Multiple Cylinder Misfire |
| P0301-P0312 | Cylinder 1-12 Misfire |
| P0420 | Catalyst System Efficiency Below Threshold (Bank 1) |
| P0430 | Catalyst System Efficiency Below Threshold (Bank 2) |
| P0440 | EVAP System Malfunction |
| P0442 | EVAP System Leak Detected (Small) |
| P0455 | EVAP System Leak Detected (Large) |

#### Chassis (C0xxx)

| Code | Description |
|------|-------------|
| C0035 | Left Front Wheel Speed Sensor Circuit |
| C0040 | Right Front Wheel Speed Sensor Circuit |
| C0045 | Left Rear Wheel Speed Sensor Circuit |
| C0050 | Right Rear Wheel Speed Sensor Circuit |

#### Body (B1xxx)

| Code | Description |
|------|-------------|
| B1234 | Example Body Code (varies by manufacturer) |

### Reading DTCs

**Request (Service 0x03):**
```
CAN ID:  0x7DF
Data:    01 03 00 00 00 00 00 00
         │  │  └──────────────────── Padding
         │  └─────────────────────── Service 0x03
         └────────────────────────── Length = 1
```

**Response (Multi-frame if >2 DTCs):**
```
First Frame:
CAN ID:  0x7E8
Data:    10 0A 43 04 01 71 03 00
         │  │  │  │  └──┴──────────── DTC 1: 0x0171 (P0171)
         │  │  │  └─────────────────── Count = 4 DTCs
         │  │  └────────────────────── Service 0x43
         │  └───────────────────────── Total length = 10 bytes
         └──────────────────────────── First Frame

Consecutive Frame:
CAN ID:  0x7E8
Data:    21 40 35 B1 23 4A 00 00
         │  └──┴──┴──┴──┴──────────── DTCs 2-4
         └─────────────────────────── Sequence 1

DTCs:
  1. 0x0171 = P0171 (System Too Lean)
  2. 0x0300 = P0300 (Random Misfire)
  3. 0x4035 = C0035 (Wheel Speed Sensor)
  4. 0xB123 = B1123 (Body code)
```

---

## Multi-Frame Messages (ISO-TP)

### ISO 15765-2 (ISO-TP)

For messages larger than 7 bytes, ISO-TP (Transport Protocol) is used.

### Frame Types

| Type | Byte 0 | Description |
|------|--------|-------------|
| Single Frame | 0x0N | N = length (0-7 bytes) |
| First Frame | 0x1N NN | N = length upper bits, NN = length lower byte |
| Consecutive Frame | 0x2N | N = sequence (0-F) |
| Flow Control | 0x30 | Continue to send |

### Example: VIN (17 characters)

**Request:**
```
CAN ID:  0x7DF
Data:    02 09 02 00 00 00 00 00
         │  │  │  └──────────────────── Padding
         │  │  └─────────────────────── InfoType 0x02 (VIN)
         │  └────────────────────────── Service 0x09
         └───────────────────────────── Length = 2
```

**Response:**

**First Frame:**
```
CAN ID:  0x7E8
Data:    10 14 49 02 01 31 47 31
         │  │  │  │  │  └──┴──┴──────── VIN bytes 1-3: "1G1"
         │  │  │  │  └─────────────────── Message count = 1
         │  │  │  └────────────────────── InfoType 0x02
         │  │  └───────────────────────── Service 0x49
         │  └──────────────────────────── Total length = 0x14 (20 bytes)
         └─────────────────────────────── First Frame
```

**Consecutive Frame 1:**
```
CAN ID:  0x7E8
Data:    21 4A 43 35 34 34 34 52
         │  └──┴──┴──┴──┴──┴──┴──────── VIN bytes 4-10: "JC5444R"
         └─────────────────────────────── Sequence 1
```

**Consecutive Frame 2:**
```
CAN ID:  0x7E8
Data:    22 37 32 35 32 33 36 37
         │  └──┴──┴──┴──┴──┴──┴──────── VIN bytes 11-17: "7252367"
         └─────────────────────────────── Sequence 2
```

**Complete VIN:** "1G1JC5444R7252367"

---

## Implementation

### Decoder Architecture

The OBD-II implementation follows a modular design:

```
┌─────────────────────────────────────────────────────────────┐
│                   obd2_decoder.py                           │
│                   (Core Implementation)                     │
│                                                             │
│  • OBD2_PIDS (PID database with formulas)                  │
│  • OBD2Decoder (main decoder class)                        │
│  • decode_message() - Parse OBD-II responses               │
│  • decode_pid_value() - Apply PID formulas                 │
│  • decode_supported_pids() - Parse support bitmaps         │
│  • is_obd2_message() - Identify OBD-II traffic             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              obd2_protocol_decoder.py                       │
│              (Protocol Adapter)                             │
│                                                             │
│  • OBD2ProtocolDecoder (ProtocolDecoder interface)         │
│  • Wraps OBD2Decoder                                       │
│  • Returns DecodedData for app                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   dialogs/obd2.py                           │
│                   (User Interface)                          │
│                                                             │
│  • OBD2Dialog (PyQt6 GUI)                                  │
│  • PID selection and filtering                             │
│  • Automatic polling with configurable interval            │
│  • Live values display                                     │
│  • DTC reading and clearing                                │
│  • Raw message logging                                     │
│  • Statistics and diagnostics                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Classes

**1. OBD2Decoder**
```python
class OBD2Decoder:
    def decode_message(self, can_id: int, data: bytes) -> Dict
    def decode_pid_value(self, pid: int, data: bytes) -> float
    def decode_supported_pids(self, data: bytes) -> List[int]
    def is_obd2_message(can_id: int) -> bool
    def get_expected_baudrates() -> List[int]
```

**2. OBD2_PIDS Dictionary**
```python
OBD2_PIDS = {
    0x0C: {
        'name': 'Engine RPM',
        'description': 'Engine speed',
        'bytes': 2,
        'formula': lambda data: ((data[0] * 256) + data[1]) / 4,
        'unit': 'RPM',
        'min': 0,
        'max': 16383.75,
        'category': 'Engine'
    },
    # ... 60+ PIDs
}
```

---

## Usage Guide

### 1. Enable OBD-II Decoder

```
CAN Analyzer → Tools → Protocol Decoders → Enable "OBD-II"
```

### 2. Connect to CAN Bus

**Requirements:**
- Baudrate: **500 kbps** (most common) or **250 kbps**
- Standard IDs: 11-bit
- Termination: 120Ω at both ends
- Vehicle ignition: ON

**Connection Settings:**
```
Settings (Ctrl+,):
  CAN Device: /dev/ttyACM0 (or your device)
  COM Baudrate: 115200 bps
  CAN Baudrate: 500K (500 kbps) or 250K (250 kbps)
```

### 3. Open OBD-II Monitor

```
Tools → OBD-II Monitor... (Ctrl+Shift+O)
```

**Features:**
- **PID Selection:** Choose which parameters to monitor
- **Quick Presets:** Basic, Extended, Lambda, Fuel
- **Category Filters:** Engine, Fuel, Air, Lambda, etc.
- **Polling Controls:** Start/Stop, interval, single shot
- **Live Values:** Real-time data with last update time
- **Raw Messages:** Request/response log
- **Statistics:** Success rate, response time

### 4. Select PIDs

**Method 1: Quick Presets**
```
Dropdown → Select "Basic" (RPM, Speed, Coolant, TPS)
```

**Method 2: Manual Selection**
```
1. Use category filter (e.g., "Engine")
2. Check desired PIDs in list
3. Or click "Select All"
```

**Method 3: Check Available PIDs**
```
1. Click "Check Available PIDs"
2. System queries ECU for supported PIDs
3. Unsupported PIDs are disabled
4. Select from available PIDs
```

### 5. Start Polling

```
1. Set polling interval (recommended: 500-1000ms)
2. Click "▶ Start Polling"
3. View live values in "Live Values" tab
4. Monitor requests/responses in "Raw Messages" tab
```

### 6. Read DTCs

```
1. Click "Read DTCs" button
2. Wait for response (~1-2 seconds)
3. View codes in popup dialog
4. If no codes: "No DTCs found. Vehicle is healthy!"
```

### 6.1 Detect VIN (Service 09 PID 02)

The OBD-II Monitor includes a **Detect VIN** button. It requests vehicle information (Service `0x09`, PID `0x02`) and assembles the ISO-TP multi-frame response.

```
1. Click "Detect VIN"
2. Wait for response (ISO-TP multi-frame)
3. VIN is displayed in the header (right side), next to the channel status
```

Notes:
- VIN responses are typically multi-frame (ISO-TP).
- Some ECUs require a Flow Control (0x30) frame before sending consecutive frames.

### 7. Export Data

```
1. Click "Save Results"
2. Choose location and filename
3. Data exported to CSV format
4. Includes: Timestamp, PID, Name, Value, Unit
```

---

## Troubleshooting

### No Responses from ECU

**Symptoms:**
- "Not connected" status
- No data in Live Values
- Success rate: 0%

**Causes & Solutions:**

1. **Ignition Off**
   - ✅ Turn ignition to ON position (engine can be off)
   - ✅ Some vehicles require engine running

2. **Wrong Baudrate**
   - ✅ Try 500 kbps first (most common)
   - ✅ If no response, try 250 kbps
   - ✅ Some older vehicles use other protocols (not CAN)

3. **Wrong CAN Bus**
   - ✅ Vehicles may have multiple CAN buses
   - ✅ OBD-II is usually on "Diagnostic CAN" or "MS-CAN"
   - ✅ Try different OBD-II pin pairs (6+14, 3+11)

4. **Hardware Issues**
   - ✅ Check CAN-H and CAN-L connections
   - ✅ Verify 120Ω termination
   - ✅ Test with known-good vehicle

### Low Success Rate

**Symptoms:**
- Some PIDs respond, others don't
- Success rate: 20-80%
- Intermittent responses

**Causes & Solutions:**

1. **Polling Too Fast**
   - ✅ Increase interval to ≥500ms
   - ✅ ECU needs time to process requests

2. **Too Many PIDs**
   - ✅ Reduce number of selected PIDs
   - ✅ ECU may not handle many simultaneous requests
   - ✅ Try 4-8 PIDs maximum

3. **Unsupported PIDs**
   - ✅ Use "Check Available PIDs" feature
   - ✅ Only poll supported PIDs
   - ✅ Unsupported PIDs always fail

4. **Bus Congestion**
   - ✅ Other ECUs may be using the bus
   - ✅ Increase polling interval
   - ✅ Avoid polling during active driving

### Incorrect Values

**Symptoms:**
- Values out of range
- Constant zero or max values
- Values don't change

**Causes & Solutions:**

1. **Wrong Formula**
   - ✅ Check PID formula in `obd2_decoder.py`
   - ✅ Some manufacturers use proprietary formulas
   - ✅ Verify against vehicle manual

2. **Byte Order**
   - ✅ OBD-II uses big-endian
   - ✅ Check implementation matches spec

3. **Sensor Not Installed**
   - ✅ PID may be supported but sensor missing
   - ✅ Example: O2 sensors on 4-cylinder showing 8 sensors

4. **Manufacturer-Specific PID**
   - ✅ PIDs 0x20+ may be proprietary
   - ✅ Consult manufacturer documentation

### DTC Reading Issues

**Symptoms:**
- "No response received from ECU"
- "No DTCs found" when check engine light is on
- Incorrect number of DTCs

**Causes & Solutions:**

1. **Timeout Too Short**
   - ✅ DTC responses can be slow (multi-frame)
   - ✅ Wait 2-3 seconds for response
   - ✅ Check "Raw Messages" for partial responses

2. **Multi-Frame Processing**
   - ✅ DTCs use ISO-TP multi-frame
   - ✅ Verify all frames received
   - ✅ Check sequence numbers (0x21, 0x22, ...)

3. **Pending vs Confirmed**
   - ✅ Check engine light shows confirmed DTCs (Service 0x03)
   - ✅ Pending DTCs (Service 0x07) don't trigger light
   - ✅ Try both services

4. **DTCs Cleared**
   - ✅ Recent battery disconnect clears DTCs
   - ✅ Some vehicles clear after successful drive cycle
   - ✅ Check permanent DTCs (Service 0x0A)

### Connection Status Issues

**Symptoms:**
- Status shows "Not connected" despite responses
- Timer doesn't update
- Inconsistent connection state

**Causes & Solutions:**

1. **Response ID Mismatch**
   - ✅ Verify response IDs (0x7E8-0x7EF)
   - ✅ Match request broadcast (0x7DF) to response
   - ✅ Check multiple ECUs responding

2. **Thread Safety**
   - ✅ Ensure UI updates in main thread
   - ✅ Use Qt signals for cross-thread communication
   - ✅ Check `update_timer` is running

3. **Bus Selection**
   - ✅ If multiple buses, select correct one
   - ✅ Filter messages by source bus
   - ✅ Verify active bus in dropdown

---

## Official Standards

### Primary Standards

**ISO 15765-4: Road vehicles — Diagnostics on CAN — Part 4: Requirements for emission-related systems**
- **Publisher:** International Organization for Standardization (ISO)
- **Year:** 2016
- **Scope:** OBD-II over CAN physical layer
- **URL:** https://www.iso.org/standard/66574.html

**ISO 15765-2: Diagnostic communication over Controller Area Network (DoCAN) — Part 2: Transport protocol and network layer services**
- **Publisher:** ISO
- **Year:** 2016
- **Scope:** ISO-TP (multi-frame messages)
- **URL:** https://www.iso.org/standard/66573.html

**SAE J1979: E/E Diagnostic Test Modes**
- **Publisher:** Society of Automotive Engineers (SAE)
- **Year:** 2017 (latest revision)
- **Scope:** OBD-II services, PIDs, DTCs
- **URL:** https://www.sae.org/standards/content/j1979_201702/

**SAE J2012: Diagnostic Trouble Code Definitions**
- **Publisher:** SAE
- **Year:** 2016
- **Scope:** DTC format and definitions
- **URL:** https://www.sae.org/standards/content/j2012_201603/

### Related Standards

- **ISO 9141:** K-Line (pre-CAN OBD)
- **ISO 14230:** KWP2000 (Keyword Protocol)
- **SAE J1850:** PWM/VPW (GM, Ford, Chrysler pre-CAN)

### Online Resources

**Wikipedia: OBD-II PIDs**
- **URL:** https://en.wikipedia.org/wiki/OBD-II_PIDs
- **Content:** Comprehensive PID list with formulas
- **Maintained:** Community-updated

**OBD-II PIDs GitHub Repository**
- **URL:** https://github.com/Knio/carhack/blob/master/carhack/lib/obd2/pids.py
- **Content:** Python PID definitions
- **License:** Open-source

### Regulatory Information

**United States:**
- **EPA (Environmental Protection Agency):** Mandates OBD-II since 1996
- **CARB (California Air Resources Board):** OBD-II regulations

**Europe:**
- **EOBD (European OBD):** Mandatory since 2001 (petrol), 2004 (diesel)
- **Regulation (EC) No 715/2007:** Euro 5/6 emissions

**Other Regions:**
- **JOBD (Japan OBD):** Similar to OBD-II
- **IOBD (India OBD):** Based on EOBD

---

## Implementation Files

### Source Code

| File | Purpose | Lines |
|------|---------|-------|
| `src/decoders/obd2_decoder.py` | Core decoder logic | ~505 |
| `src/decoders/obd2_protocol_decoder.py` | Protocol adapter | ~66 |
| `src/dialogs/obd2.py` | User interface | ~1,249 |

### Tools

| File | Purpose |
|------|---------|
| `tools/general/obd2_poller.py` | CLI polling tool |
| `tools/general/send_can_message.py` | Manual CAN message sender |
| `tools/arduino/arduino_obd2_ecu_simulator.ino` | Arduino ECU simulator |

### Testing

**Arduino OBD-II ECU Simulator:**
```bash
cd tools/arduino
# Upload arduino_obd2_ecu_simulator.ino to Arduino with MCP2515

# Simulates:
- Service 0x01: 8 PIDs (RPM, Speed, Coolant, TPS, etc.)
- Service 0x03: 4 DTCs (P0171, P0300, C0035, B1234)
- Support PIDs: 0x00, 0x20, 0x40, 0x60
```

**Expected Behavior:**
- Responds to 0x7DF broadcast
- Sends responses on 0x7E8
- Animated fake data (RPM sweeps, temperature changes)
- Multi-frame DTC responses

---

## Quick Reference

### Common Requests

**Read Engine RPM:**
```python
request = [0x02, 0x01, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00]
# Response: [0x04, 0x41, 0x0C, A, B, 0x00, 0x00, 0x00]
# RPM = ((A * 256) + B) / 4
```

**Read Vehicle Speed:**
```python
request = [0x02, 0x01, 0x0D, 0x00, 0x00, 0x00, 0x00, 0x00]
# Response: [0x03, 0x41, 0x0D, A, 0x00, 0x00, 0x00, 0x00]
# Speed = A (km/h)
```

**Read Coolant Temperature:**
```python
request = [0x02, 0x01, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]
# Response: [0x03, 0x41, 0x05, A, 0x00, 0x00, 0x00, 0x00]
# Temperature = A - 40 (°C)
```

**Read DTCs:**
```python
request = [0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
# Response: Multi-frame
# [0x10, Length, 0x43, Count, DTC1_H, DTC1_L, ...]
# [0x21, DTC2_H, DTC2_L, ...]
```

**Clear DTCs:**
```python
request = [0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
# Response: [0x01, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
```

### Python Decoder Example

```python
def decode_rpm(response_data):
    """Decode Engine RPM from OBD-II response"""
    if len(response_data) < 5:
        return None
    
    length = response_data[0]
    service = response_data[1]
    pid = response_data[2]
    
    if service != 0x41 or pid != 0x0C:
        return None
    
    A = response_data[3]
    B = response_data[4]
    
    rpm = ((A * 256) + B) / 4
    return rpm

# Example usage:
response = bytes([0x04, 0x41, 0x0C, 0x1A, 0xF8, 0x00, 0x00, 0x00])
rpm = decode_rpm(response)
print(f"Engine RPM: {rpm}")  # Output: Engine RPM: 1726.0
```

---

## Performance Notes

### Polling Rates

| Interval | Use Case | ECU Load |
|----------|----------|----------|
| 100ms | Real-time dashboard (4-6 PIDs max) | High |
| 250ms | Performance monitoring (6-8 PIDs) | Medium-High |
| 500ms | General monitoring (8-12 PIDs) | Medium |
| 1000ms | Data logging (12-20 PIDs) | Low |
| 2000ms+ | Background monitoring (20+ PIDs) | Very Low |

**Recommendation:** Start with 500-1000ms and adjust based on success rate.

### Response Times

| Request Type | Typical Response Time |
|--------------|----------------------|
| Single PID | 10-50ms |
| Multiple PIDs (sequential) | 50-200ms |
| DTC Read (few codes) | 50-100ms |
| DTC Read (many codes) | 100-500ms |
| VIN Read | 100-300ms |

### Bus Load

**Typical scenario (8 PIDs @ 500ms):**
- Requests: 8 × 2 frames/sec = 16 frames/sec
- Responses: 8 × 2 frames/sec = 16 frames/sec
- **Total:** ~32 frames/sec
- **Bus load:** < 1% @ 500 kbps

**Maximum theoretical:**
- 500 kbps = 500,000 bits/sec
- CAN frame ≈ 130 bits (standard, 8 bytes)
- Max frames ≈ 3,850 frames/sec
- OBD-II typical usage: < 1% of maximum

---

## Comparison: OBD-II vs FTCAN

| Aspect | OBD-II | FTCAN 2.0 |
|--------|--------|-----------|
| **Communication** | Request/Response | Broadcast |
| **Polling Required** | ✅ Yes | ❌ No |
| **Latency** | ~100ms per PID | ~10ms continuous |
| **Baudrate** | 500 kbps (250 kbps) | 1 Mbps |
| **ID Format** | 11-bit Standard | 29-bit Extended |
| **Byte Order** | Big-endian | Big-endian |
| **Standardization** | ✅ ISO/SAE | ❌ Proprietary |
| **Compatibility** | ✅ Universal (1996+) | ❌ FuelTech only |
| **Diagnostic Codes** | ✅ DTCs included | ❌ Not included |
| **Data Types** | 60+ PIDs | 100+ Measures |
| **Bus Load** | Low (on-demand) | High (continuous) |
| **Use Case** | Diagnostics, general monitoring | Racing, telemetry, high-frequency |

---

## License

**CAN Bus Analyzer:** Open-source (see main repository)

**OBD-II Protocol:** Standardized by ISO and SAE. Implementation based on publicly available specifications.

---

## Changelog

### v1.0.0 (2026-02-06)
- ✅ Complete protocol documentation
- ✅ Technical specifications
- ✅ Request/response model explained
- ✅ Message structure (single & multi-frame)
- ✅ All 10 services documented
- ✅ 60+ PIDs with formulas
- ✅ DTC format and encoding
- ✅ ISO-TP multi-frame explained
- ✅ Implementation guide
- ✅ Usage instructions
- ✅ Comprehensive troubleshooting
- ✅ Official standards references

---

## Contributing

To improve this documentation:

1. **Found an error?** Open an issue with details
2. **Have a suggestion?** Create a pull request
3. **Discovered new PIDs?** Share formulas and examples
4. **Tested with new vehicles?** Document compatibility

---

## Related Documentation

- **Main README:** `../../README.md`
- **FTCAN Documentation:** `FTCAN.md`
- **Tools Documentation:** `../../tools/general/README.md`
- **Arduino Tools:** `../../tools/arduino/README.md`

---

## Support

- **GitHub Issues:** For bugs and feature requests
- **Documentation:** This directory
- **OBD-II Standards:** ISO 15765-4, SAE J1979
- **Wikipedia:** https://en.wikipedia.org/wiki/OBD-II_PIDs
