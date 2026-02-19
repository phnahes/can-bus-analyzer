# VAG BAP Protocol Documentation

Complete technical documentation for Volkswagen/Audi BAP (Bedien- und Anzeigeprotokoll) protocol support in CAN Bus Analyzer.

---

## Contents

- [Protocol Overview](#protocol-overview)
- [Technical Specifications](#technical-specifications)
- [Message Architecture](#message-architecture)
- [Multi-Frame Protocol](#multi-frame-protocol)
- [BAP Header Structure](#bap-header-structure)
- [CAN ID Addressing](#can-id-addressing)
- [Detection Modes](#detection-modes)
- [Implementation](#implementation)
- [Usage Guide](#usage-guide)
- [Export/Import & Replay](#exportimport--replay)
- [Performance & Threading](#performance--threading)
- [Troubleshooting](#troubleshooting)
- [References](#references)

---

## Protocol Overview

**BAP (Bedien- und Anzeigeprotokoll)** is Volkswagen Group's bidirectional communication protocol designed for interaction between control units and display units in vehicles. It succeeded the older DDP (Display Data Protocol) and provides event-driven, standardized messaging across multiple vehicle platforms.

### Key Features

- **Bidirectional Communication**: Two-way data exchange between ECUs
- **Event-Driven Architecture**: Reduces bus load vs constant polling
- **Multi-Frame Support**: Messages up to 4095 bytes (12-bit length field)
- **Parallel Streams**: Up to 4 simultaneous streams per CAN ID (multi-frame channels)
- **Error Resilience**: Automatic timeout and stream cleanup
- **Platform Flexibility**: Works with both 11-bit and 29-bit CAN IDs

### Device Roles

- **FSG (Funktionsteuergerät)**: Function Control Unit - sends data (e.g., radio/infotainment)
- **ASG (Anzeigesteuergerät)**: Display Control Unit - receives data (e.g., instrument cluster)

### Why BAP?

Standard CAN provides only 8 bytes per frame. BAP adds:
1. **Segmentation**: Send payloads up to 4095 bytes across multiple frames
2. **Logical Addressing**: LSG (Logical Service Group) and FCT (Function ID) for routing
3. **Operation Codes**: Define the type of action (GET, SET, STATUS, etc.)
4. **Stream Management**: Multiple parallel conversations on the same CAN ID

---

## Technical Specifications

### Physical Layer

- **Protocol**: CAN 2.0A (11-bit) or CAN 2.0B Extended (29-bit)
- **Bitrate**: Typically 500 kbps (vehicle-dependent)
- **Frame Type**: Standard or Extended
- **Data Length**: 0-8 bytes per CAN frame
- **Byte Order**: Big-endian (for multi-byte fields)
- **Termination**: 120Ω resistors at both ends

### Protocol Limits

- **Maximum Payload**: 4095 bytes (12-bit length field)
- **Multi-Frame Channels**: 4 parallel streams per CAN ID (2-bit channel field)
- **Stream Timeout**: 2.0 seconds (configurable in implementation)

---

## Message Architecture

BAP messages can be classified into two types based on payload size:

### Short Messages (≤ 6 bytes payload)

Short messages fit within a single CAN frame (8 bytes total):

```
┌────────────┬────────────┬──────────────────────┐
│ Byte 0-1   │ Byte 2-7   │                      │
│ BAP Header │ Payload    │                      │
│ (2 bytes)  │ (0-6 B)    │                      │
└────────────┴────────────┴──────────────────────┘
```

**Byte 0 (First byte of BAP Header)**:
- Bit 0: `0` (indicates short message)
- Bits 1-3: Opcode (3 bits, 0-7)
- Bits 4-7: LSG high nibble

**Byte 1 (Second byte of BAP Header)**:
- Bits 0-1: LSG low bits
- Bits 2-7: FCT (Function ID, 6 bits, 0-63)

Combined Header (16-bit big-endian):
```
┌─┬───────┬──────────┬────────────┐
│0│Opcode │   LSG    │    FCT     │
│ │(3 bit)│  (6 bit) │  (6 bit)   │
└─┴───────┴──────────┴────────────┘
```

### Long Messages (> 6 bytes payload)

Long messages span multiple CAN frames using a preamble system:

#### Start Frame (First frame of multi-frame message)

```
┌────────────┬────────────┬────────────┬─────────────┐
│ Byte 0     │ Byte 1     │ Byte 2-3   │ Byte 4-7    │
│ Preamble   │ Total Len  │ BAP Header │ Payload     │
│ (0x8X)     │ (8 bits)   │ (2 bytes)  │ (0-4 bytes) │
└────────────┴────────────┴────────────┴─────────────┘
```

**Byte 0 (Preamble)**:
- Bits 7-6: `10` (0x80 pattern, indicates start frame)
- Bits 5-4: MF Channel (0-3, allows parallel streams)
- Bits 3-0: Length high nibble (top 4 bits of 12-bit total length)

**Byte 1**: Length low byte (bottom 8 bits of 12-bit total length)

**Total Length (12-bit)**:
```
total_len = ((byte0 & 0x0F) << 8) | byte1
```

**Bytes 2-3**: BAP Header (same format as short messages)

**Bytes 4-7**: First chunk of payload (up to 4 bytes in start frame)

#### Continuation Frame (Subsequent frames)

```
┌────────────┬────────────────────────────┐
│ Byte 0     │ Bytes 1-7                  │
│ Preamble   │ Payload Chunk              │
│ (0xCX)     │ (up to 7 bytes)            │
└────────────┴────────────────────────────┘
```

**Byte 0 (Preamble)**:
- Bits 7-6: `11` (0xC0 pattern, indicates continuation frame)
- Bits 5-4: MF Channel (must match start frame)
- Bits 3-0: Sequence index (increments: 0, 1, 2, ...)

**Bytes 1-7**: Continuation payload chunk (up to 7 bytes per frame)

---

## Multi-Frame Protocol

### Stream Identification

Each active multi-frame stream is uniquely identified by:
- **CAN ID**: The CAN identifier
- **ID Type**: Standard (11-bit) vs Extended (29-bit)
- **MF Channel**: 2-bit channel field (0-3)

This allows up to 4 parallel multi-frame conversations on the same CAN ID.

### Reassembly Process

1. **Start Frame Arrives** (0x80...):
   - Extract total length (12-bit)
   - Parse BAP header (opcode/lsg/fct)
   - Initialize buffer with first chunk
   - Create stream state keyed by (CAN ID, ID type, channel)

2. **Continuation Frames Arrive** (0xC0...):
   - Match to active stream by (CAN ID, ID type, channel)
   - Append chunk to buffer
   - Check if buffer length == total length

3. **Completion**:
   - When buffer reaches total length, emit complete payload
   - Assign unique packet_id for UI grouping
   - Clean up stream state

4. **Timeout**:
   - Streams older than `STREAM_TIMEOUT_SEC` (default: 2.0s) are discarded
   - Prevents mixing old/new traffic

### Example: 3-Frame Message

**Frame 1 (Start)**: `80 1A 4C C1 01 02 03 04`
- Preamble: `0x80` → Start frame, channel 0
- Total length: `0x01A` (26 bytes)
- Header: `0x4CC1` → opcode=2, lsg=19, fct=1
- First chunk: `01 02 03 04` (4 bytes)

**Frame 2 (Continuation)**: `C0 05 06 07 08 09 0A 0B`
- Preamble: `0xC0` → Continuation, channel 0, seq=0
- Chunk: `05 06 07 08 09 0A 0B` (7 bytes)
- Buffer now: 4 + 7 = 11 bytes

**Frame 3 (Continuation)**: `C1 0C 0D 0E ... 1A`
- Preamble: `0xC1` → Continuation, channel 0, seq=1
- Chunk: remaining 15 bytes
- Buffer complete: 11 + 15 = 26 bytes ✓

**Reassembled Payload**: `01 02 03 04 05 06 ... 1A` (26 bytes)

---

## BAP Header Structure

The BAP header is a 2-byte (16-bit) field that appears after the preamble (in multi-frame) or at the start (in short messages).

### Bit Layout (Big-Endian)

```
┌─────────────────────────────────────────────────┐
│            16-bit BAP Header (Big-Endian)       │
├─────────┬──────────────────┬───────────────────┤
│ Opcode  │      LSG         │       FCT         │
│ (3 bit) │    (6 bit)       │     (6 bit)       │
│  0-7    │     0-63         │      0-63         │
└─────────┴──────────────────┴───────────────────┘

Bit positions (MSB first):
15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
├──────┤ ├────────────┤ ├─────────────────────┤
 Opcode      LSG               FCT
```

### Parsing (from 2 bytes)

```python
header = (byte0 << 8) | byte1
opcode = (header >> 12) & 0x7    # Top 3 bits (shifted right 12)
lsg    = (header >> 6) & 0x3F    # Next 6 bits (shifted right 6)
fct    = header & 0x3F           # Bottom 6 bits
```

### Fields

- **Opcode (3 bits, 0-7)**: Operation type
  - Common values: `0x01` GET, `0x02` SET, `0x03` STATUS, `0x04` RESPONSE, etc.
  - Exact semantics vary by LSG/FCT combination

- **LSG (6 bits, 0-63)**: Logical Service Group
  - Groups related functions (e.g., LSG 0x33 might be camera, LSG 0x43 might be HVAC)
  - Acts as a logical sub-unit within the ECU

- **FCT (6 bits, 0-63)**: Function ID
  - Specific function within the LSG (e.g., brightness, contrast, mode)
  - Combined with LSG to uniquely identify the target function

---

## CAN ID Addressing

### Standard IDs (11-bit)

With 11-bit CAN IDs, the BAP header (opcode/lsg/fct) is entirely contained in the payload.

Example:
- CAN ID: `0x63B` (11-bit standard)
- Payload: `4C C1 01 02 03 04` → Header `0x4CC1` (opcode=2, lsg=19, fct=1), payload `01 02 03 04`

### Extended IDs (29-bit)

With 29-bit CAN IDs, some addressing information may be embedded in the CAN ID itself for routing efficiency.

Common layout (observed in some networks):
```
┌──────────────┬────────────┬──────────────┐
│ Base ID      │ LSG Hint   │ Endpoint     │
│ (16 bits)    │ (8 bits)   │ (8 bits)     │
└──────────────┴────────────┴──────────────┘

Example: 0x17333310
- Base: 0x1733
- LSG hint: 0x33
- Endpoint: 0x10
```

**Extraction**:
```python
base_id  = (can_id >> 16) & 0xFFFF
lsg_hint = (can_id >> 8) & 0x3F
endpoint = can_id & 0xFF
```

**Important**: This layout is a heuristic observed in some vehicle networks. Not all extended ID BAP traffic follows this pattern. The decoder uses this as a hint for analysis, not as a strict rule.

---

## Detection Modes

The decoder supports two detection modes to balance confidence vs coverage:

### Conservative Mode (Default)

**High confidence detection**: Only multi-frame traffic (0x80/0xC0 preambles).

- ✅ Very low false positive rate
- ✅ Strong signal: multi-frame segmentation is distinctive
- ❌ Misses single-frame BAP messages

**Use when**: You want to be certain captured traffic is BAP.

### Aggressive Mode

**Extended detection**: Attempts single-frame decoding with heuristics.

- ✅ Captures single-frame BAP messages
- ❌ Higher false positive rate (CAN traffic can look like BAP)
- 🛡️ **Heuristic**: Only attempts single-frame on CAN IDs that have previously completed a valid multi-frame message

**Use when**: You need complete coverage and can tolerate some false positives.

---

## Implementation

### Architecture

The BAP decoder follows the modular decoder pattern used throughout the application:

```
┌─────────────────────────────────────────────────┐
│           CANAnalyzerWindow (main_window.py)    │
│  ┌───────────────────────────────────────────┐  │
│  │      DecoderManager (decoders/base.py)    │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │  BAPProtocolDecoder (adapter_bap.py)│  │  │
│  │  │    ├─ BAPDecoder (decoder_bap.py)   │  │  │
│  │  │    └─ DecodedData output            │  │  │
│  │  └─────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │     BAPDialog (dialogs/bap.py)            │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │  _BAPDecodeWorker (background)      │  │  │
│  │  │    └─ BAPDecoder (dedicated)        │  │  │
│  │  └─────────────────────────────────────┘  │  │
│  │  - Reassembled Messages tab             │  │
│  │  - Raw Frames tab                       │  │
│  │  - Export/Import/Replay                 │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Core Components

#### 1. `BAPDecoder` (decoder_bap.py)

**Pure protocol logic** - no UI dependencies.

Key responsibilities:
- Detect multi-frame preambles (0x80/0xC0)
- Manage stream state (keyed by CAN ID + ID type + channel)
- Reassemble payloads from start + continuation frames
- Parse BAP headers (opcode/lsg/fct)
- Extract hints from extended CAN IDs
- Timeout cleanup for incomplete streams

**Constants** (configurable):
```python
STREAM_TIMEOUT_SEC = 2.0       # Max age for incomplete streams
MAX_BAP_LENGTH = 4095          # Maximum payload length
MF_PREAMBLE_MASK = 0xC0        # Mask for preamble bits
MF_START_PREAMBLE = 0x80       # Start frame pattern
MF_CONT_PREAMBLE = 0xC0        # Continuation frame pattern
MF_CHANNEL_MASK = 0x03         # Multi-frame channel mask
MF_CHANNEL_SHIFT = 4           # Shift to extract channel
```

**Output** (`decode_message` returns dict):
```python
{
    "success": bool,
    "is_bap_candidate": bool,
    "is_complete": bool,
    "platform": "standard" | "extended" | None,  # Heuristic label
    "mf_channel": 0-3,                           # Multi-frame channel
    "total_len": int,                            # Total payload length
    "packet_id": int,                            # Unique ID for UI grouping
    "header": {"opcode": int, "lsg": int, "fct": int},
    "payload": str,                              # Hex string of complete payload
    "raw_id": int,
    "raw_data": str,
    "is_extended": bool,
    "error": str | None
}
```

#### 2. `BAPProtocolDecoder` (adapter_bap.py)

**Modular system adapter** - integrates BAPDecoder with DecoderManager.

Key responsibilities:
- Wraps BAPDecoder for the modular decoder system
- Implements `can_decode()`: Returns True for 0x80/0xC0 preambles or active streams
- Implements `decode()`: Returns `DecodedData` only for **completed** payloads
- Priority: `LOW` (stays out of the way; this is a detector)
- Default: **Disabled** (must be enabled via Decoder Manager)

**Note**: The modular decoder only emits completed messages to avoid spamming the main UI with partial frames.

#### 3. `BAPDialog` (dialogs/bap.py)

**Dedicated analyzer UI** - for deep BAP traffic analysis.

Key features:
- Receives ALL messages while open (forwarded by `UIUpdateHandler`)
- Background decoding via `_BAPDecodeWorker` thread
- Two views:
  - **Reassembled Messages**: Complete payloads grouped by `packet_id`
  - **Raw Frames**: Individual CAN frames (start/continuation) with progress indicators
- Filters: CAN ID, LSG, Source
- Details panel: Shows complete payload, header fields, and frame linkage explanation
- Export/Import: Save/load captures as JSON for offline analysis
- Replay: Resend captured frames to CAN bus (with optional timing preservation)

---

## Usage Guide

### Opening the BAP Analyzer

**Menu**: `Tools → Protocol Decoders → VAG BAP Analyzer...`  
**Shortcut**: `Ctrl+3` (Windows/Linux) / `Cmd+3` (macOS)  

### Detection Mode

**Conservative (High Confidence)** - Default
- Only detects multi-frame traffic (0x80/0xC0 preambles)
- Very low false positive rate
- Recommended for production analysis

**Aggressive (Include Single-Frame)**
- Also attempts single-frame decoding
- Uses heuristic: only on CAN IDs that have previously completed a valid multi-frame
- Higher coverage but may include false positives

### Analyzing Traffic

#### Reassembled Messages Tab

Displays complete BAP payloads:
- **Time**: Timestamp of first frame
- **Bus**: Source CAN bus
- **CAN ID**: Identifier (hex)
- **Channel**: Multi-frame channel (if applicable)
- **Endpoint**: Extracted from extended ID (if applicable)
- **Pkt**: Packet ID (unique identifier for grouping)
- **LSG**: Logical Service Group
- **FCT**: Function ID
- **Opcode**: Operation code
- **Len**: Total payload length
- **Payload**: Complete reassembled payload (hex)

#### Raw Frames Tab

Displays individual CAN frames that compose BAP messages:
- **Type**: Start / Cont / Other
- **MF ch**: Multi-frame channel
- **Len**: Total expected length (from start frame)
- **Done**: Bytes received so far (progress indicator)
- **Header**: BAP header fields
- **Raw data**: Frame payload (hex)

**Visual Grouping**: When you select a reassembled message, all its raw frames are highlighted in the Raw Frames tab (and vice versa).

#### Details Panel

Shows expanded information for the selected message:
- Complete (non-truncated) payload
- Parsed header fields
- Extended ID hints (when applicable)
- **Frame Linkage**: Tabular explanation showing how each raw frame contributes to the final payload

**Layout**: Details panel is below the table (vertical split). Use the splitter handle to resize or click `Hide/Show Details` to toggle visibility.

### Filters

Apply filters to focus on specific traffic:
- **CAN ID**: Filter by identifier (hex, e.g., `0x63B` or `0x17333310`)
- **LSG**: Filter by Logical Service Group (decimal or hex)
- **Source**: Filter by CAN bus source

Click **Re-filter** to apply changes.

### Controls

- **Pause**: Stop analysis (incoming frames are dropped while paused)
- **Auto-scroll**: Keep tables scrolled to bottom as new messages arrive
- **Clear**: Clear all captured messages
- **Copy Payload**: Copy selected message's payload to clipboard

---

## Export/Import & Replay

### Export Capture

**Button**: `Export...`

Saves the **complete capture** to JSON:
- All reassembled messages
- All raw frames
- Current detection mode
- Active filters

**Use case**: Capture traffic in the vehicle, export, and analyze offline.

### Import Capture

**Button**: `Import...`

Loads a previously exported JSON file:
- Restores all messages and frames
- Applies saved detection mode and filters
- Rebuilds tables and linkage

### Replay Packet

**Button**: `Replay Packet`

Resends the raw frames of the selected packet to the CAN bus:
- Sends start frame + all continuation frames in order
- **Replay timing** (checkbox): If enabled, respects captured inter-frame delays
- **Use case**: Reproduce captured behavior for testing or reverse engineering

**Requirements**:
- At least one CAN bus must be connected
- Prefers the original source bus if still connected

---

## Performance & Threading

### Background Worker

To prevent UI freezes with high-volume traffic:

- **`_BAPDecodeWorker`**: Dedicated thread for decoding
- **Input queue**: Bounded queue (maxsize: 25,000) with backpressure
- **Output queue**: Decoded results sent back to UI thread
- **Batch processing**: UI consumes up to 300 messages per tick

### Optimizations

1. **Batch UI updates**: `setUpdatesEnabled(False/True)` around bulk insertions
2. **Details cache**: Formatted text cached by packet_id (thread-safe with lock)
3. **Raw frame index**: `_raw_records_by_packet` dict for O(1) lookup
4. **Column autosizing**: Sampled approach (up to 120 rows) to avoid full table scans
5. **Selection model**: `QItemSelectionModel` for efficient multi-row highlighting

### Metrics

The status bar shows real-time performance:
- **Frames**: Total CAN frames seen
- **BAP**: Reassembled BAP messages
- **Streams**: Active multi-frame streams
- **Lag**: Time between frame arrival and UI display (ms)
- **Inflight**: Messages queued in worker
- **Dropped**: Messages dropped due to backpressure

---

## Troubleshooting

### No Messages Appearing

**Check**:
1. Is the BAP analyzer dialog open? (messages only forwarded when dialog is visible)
2. Is analysis paused? (click Resume)
3. Are you seeing 0x80/0xC0 patterns in the main Monitor/Tracer? (if not, traffic may not be BAP)
4. Try Aggressive mode if you expect single-frame BAP

### Incomplete Messages (Streams Timing Out)

**Symptoms**: Raw Frames show start frames but no completion.

**Possible causes**:
1. **Frames arriving too slowly**: Increase `STREAM_TIMEOUT_SEC` in `decoder_bap.py`
2. **Missing continuation frames**: Check if frames are being filtered/dropped elsewhere
3. **Wrong channel**: Continuation frames must match the start frame's channel

### High Lag / Dropped Messages

**Symptoms**: Lag metric > 500ms, Dropped count increasing.

**Solutions**:
1. **Pause analysis**: Click Pause, clear, then Resume
2. **Apply filters**: Reduce traffic volume by filtering CAN ID or LSG
3. **Close other dialogs**: FTCAN/OBD-II analyzers running simultaneously consume resources

### Details Panel Not Showing

**Check**:
1. Is the Details panel collapsed? (drag splitter handle up or click `Show Details`)
2. Have you selected a message? (click a row in the table)

---

## References

The implementation is based on open-source reverse engineering efforts and practical testing:

### Primary References

1. **norly/revag-bap** (C implementation)
   - URL: https://github.com/norly/revag-bap
   - License: GPLv2
   - Key learnings: Multi-frame preamble patterns, channel extraction, header parsing

2. **tmbinc/kisim** (Python implementation)
   - URL: https://github.com/tmbinc/kisim
   - License: BSD-3
   - Key learnings: Frame sequencing, reassembly logic

3. **ea/vag-bap** (Header definitions)
   - URL: https://github.com/ea/vag-bap
   - Key learnings: Opcode/LSG/FCT bit layouts

4. **MIGINC/BAP_RE** (Reverse engineering documentation)
   - URL: https://github.com/MIGINC/BAP_RE
   - Key learnings: Extended ID layouts, LSG mappings, startup handshake sequences

5. **thomasakarlsen/e-golf-comfort-can** (Protocol explanation)
   - URL: https://github.com/thomasakarlsen/e-golf-comfort-can
   - Key learnings: FSG/ASG roles, short vs long message diagrams

### Additional Resources

- Karl Dietmann's BAP research (2009-2012): https://blog.dietmann.org/?p=324
- Drive2 user "VanHighlander": Extended ID mappings (via MIGINC/BAP_RE)

### Acknowledgments

This implementation would not be possible without the open-source community's reverse engineering efforts. Special thanks to all contributors of the above projects.

---

## Notes & Limitations

### Current Scope

- **Detection + Reassembly**: The decoder identifies BAP traffic and reconstructs multi-frame payloads
- **Field Extraction**: Parses opcode/lsg/fct and extracts hints from extended IDs
- **No Semantic Decoding**: Does not interpret the meaning of specific LSG/FCT/Opcode combinations (requires extensive database)

### Known Limitations

1. **Single-frame false positives**: Without multi-frame preamble, any 8-byte CAN message could theoretically be misidentified as BAP
2. **No reordering**: Assumes frames arrive in order per stream
3. **Platform heuristics**: `is_extended` is used as a proxy for parsing path, not as definitive platform detection
4. **Unofficial protocol**: BAP specifications are not publicly available; implementation is based on reverse engineering

### Future Enhancements

Potential areas for expansion:
- LSG/FCT/Opcode database for semantic decoding
- BAP operation simulation (generate valid BAP messages)
- Startup handshake analysis (FSG-Setup, BAP-Config, Function-List)
- Statistical analysis (message frequency, stream success rate)

---

## Quick Reference: Protocol Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MF_PREAMBLE_MASK` | `0xC0` | Mask for preamble bits (top 2 bits) |
| `MF_START_PREAMBLE` | `0x80` | Start frame pattern (10xxxxxx) |
| `MF_CONT_PREAMBLE` | `0xC0` | Continuation frame pattern (11xxxxxx) |
| `MF_CHANNEL_MASK` | `0x03` | Mask for channel bits |
| `MF_CHANNEL_SHIFT` | `4` | Shift to extract channel from byte 0 |
| `MF_SEQ_MASK` | `0x0F` | Mask for sequence/length nibble |
| `OPCODE_MASK` | `0xE0` | Mask for opcode (top 3 bits of header) |
| `LSG_MASK` | `0x1F` | Mask for LSG (5 bits in first header byte) |
| `FCT_MASK` | `0x3F` | Mask for FCT (6 bits in second header byte) |
| `STREAM_TIMEOUT_SEC` | `2.0` | Timeout for incomplete streams |
| `MAX_BAP_LENGTH` | `4095` | Maximum payload length (12-bit field) |

---


**For more information on the modular decoder system, see**: `docs/decoders/` (FTCAN.md, OBD2.md)
