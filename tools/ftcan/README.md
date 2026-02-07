# FTCAN Tools

Tools for working with FuelTech's FTCAN 2.0 protocol.

---

## Contents

- [Scripts Overview](#scripts-overview)
- [Installation](#installation)
- [Usage Examples](#usage-examples)
- [Related Documentation](#related-documentation)

---

## Scripts Overview

### `ftcan_simulator.py`

FTCAN 2.0 message simulator for testing and validating the decoder.

**Features:**
- Simulates WB-O2 Nano (lambda readings)
- Simulates FT600 ECU (multiple measures)
- Simulates segmented packets
- Generates Standard CAN messages for comparison
- No hardware required

**Usage:**
```bash
python3 ftcan_simulator.py
```

**Interactive Menu:**
```
1. WB-O2 Nano (Lambda readings)
2. FT600 ECU (Multiple measures)
3. Standard CAN (Non-FTCAN)
4. Segmented Packet
5. Run all simulations
0. Exit
```

**Example Output:**
```
============================================================
FTCAN 2.0 Simulator - WB-O2 Nano
============================================================

Device: WB-O2 Nano #0
CAN ID: 0x1240A7FF

Lambda: 0.850 - Rich - Max Power
  Raw Data: FF002703520000000000
  Decoded: Cylinder 1 O2: 0.850 λ

Lambda: 0.900 - Slightly Rich
  Raw Data: FF0027038400000000000
  Decoded: Cylinder 1 O2: 0.900 λ

Lambda: 1.000 - Stoichiometric
  Raw Data: FF002703E80000000000
  Decoded: Cylinder 1 O2: 1.000 λ
```

---

### `ftcan_config_capture.py`

**Note:** This tool is available but not actively maintained. It was designed for capturing and replaying FTCAN configuration commands through reverse engineering. For current FTCAN protocol implementation, refer to the decoder in `src/ftcan_decoder.py`.

---

## Installation

### Dependencies

```bash
# No dependencies required for simulator
# (Uses only standard library)

# For future replay features:
pip install python-can
```

---

## Usage Examples

### 1. Test FTCAN Decoder

**Scenario:** Validate that the FTCAN decoder correctly identifies and decodes messages.

```bash
# Terminal 1: Run simulator
python3 ftcan_simulator.py

# Choose option 5 (Run all simulations)

# Terminal 2: CAN Analyzer
# Open CAN Analyzer
# Tools → Protocol Decoders → Enable FTCAN 2.0
# Tools → FTCAN 2.0 Analyzer
# Verify decoded messages appear correctly
```

---

### 2. Simulate WB-O2 Nano

**Scenario:** Test lambda sensor readings without physical hardware.

```bash
python3 ftcan_simulator.py

# Choose: 1. WB-O2 Nano (Lambda readings)

# Output shows:
# - Lambda values from 0.82 to 1.05
# - Raw CAN data
# - Decoded values
# - Different operating conditions (rich/lean/stoichiometric)
```

**Simulated Conditions:**
- `0.85λ` - Rich - Max Power
- `0.90λ` - Slightly Rich
- `1.00λ` - Stoichiometric (ideal)
- `1.05λ` - Slightly Lean - Economy
- `0.82λ` - Very Rich - High Boost

---

### 3. Simulate FT600 ECU

**Scenario:** Test multi-measure packets from ECU.

```bash
python3 ftcan_simulator.py

# Choose: 2. FT600 ECU (Multiple measures)

# Output shows single packet with:
# - RPM: 3500
# - TPS: 85.0%
# - MAP: 1.5 Bar
# - Engine Temp: 85.0°C
```

---

### 4. Test Segmented Packets

**Scenario:** Validate decoder handles multi-frame messages correctly.

```bash
python3 ftcan_simulator.py

# Choose: 4. Segmented Packet

# Tests:
# - First frame (0x00) with total length
# - Continuation frames (0x01, 0x02, ...)
# - Reassembly of complete payload
```

---

### 5. Compare FTCAN vs Standard CAN

**Scenario:** Verify decoder correctly identifies FTCAN messages.

```bash
python3 ftcan_simulator.py

# Choose: 3. Standard CAN (Non-FTCAN)

# Shows:
# - Standard 11-bit CAN IDs
# - Decoder correctly identifies as non-FTCAN
# - No false positives
```

---

### 6. Development Workflow

**Scenario:** Developing new FTCAN features.

```bash
# 1. Modify ftcan_decoder.py
nano ../../src/ftcan_decoder.py

# 2. Test with simulator
python3 ftcan_simulator.py

# 3. Verify in CAN Analyzer
# Open app and check Protocol Decoders → FTCAN 2.0

# 4. Iterate until working correctly
```

---

## Simulated Devices

### WB-O2 Nano (Product Type: 0x0240)

**Simulated Measurements:**
- **DataID 0x0013**: Cylinder 1 O2 (Lambda)
- **Range**: 0.65λ - 1.30λ (typical)
- **Multiplier**: 0.001
- **Update Rate**: ~10ms

**CAN ID Structure:**
```
Product Type: 0x0240 (WBO2_NANO)
Unique ID:    0x00 (first device)
Data Field:   0x02 (FTCAN_2_0)
Message ID:   0x1FF (high priority broadcast)
Result:       0x1240A7FF
```

---

### FT600 ECU (Product Type: 0x0281)

**Simulated Measurements:**
- **DataID 0x0042**: Engine RPM
- **DataID 0x0001**: TPS (Throttle Position)
- **DataID 0x0002**: MAP (Manifold Pressure)
- **DataID 0x0004**: Engine Temperature

**CAN ID Structure:**
```
Product Type: 0x0281 (FT600_ECU)
Unique ID:    0x00 (first device)
Data Field:   0x02 (FTCAN_2_0)
Message ID:   0x1FF (high priority broadcast)
Result:       0x14028BFF
```

---

## Technical Details

### FTCAN Message Format

**Single Packet (most common):**
```
Byte 0:    0xFF (single packet marker)
Bytes 1-7: Payload (measures)
```

**Segmented Packet (large data):**
```
First Frame:
  Byte 0:    0x00 (first frame marker)
  Bytes 1-2: Total length (big-endian)
  Bytes 3-7: Payload start

Continuation Frames:
  Byte 0:    0x01-0xFE (sequence number)
  Bytes 1-7: Payload continuation
```

### Measure Format (4 bytes each)

```
Bytes 0-1: MeasureID (16-bit big-endian)
  Bits 15-1: DataID (sensor type)
  Bit 0:     IsStatus flag

Bytes 2-3: Value (16-bit signed big-endian)
  Raw value (apply multiplier for real value)
```

**Example - Lambda 0.850:**
```
MeasureID: 0x0027 (DataID=0x0013, IsStatus=1)
Value:     0x0352 (850 decimal)
Real:      850 * 0.001 = 0.850λ
```

---

## Requirements

- **Python**: 3.7+
- **CAN Bus**: 1 Mbps (FTCAN standard)
- **Dependencies**: None (uses standard library)

---

## Related Documentation

### Main Documentation
- **FTCAN Decoder (Core):** `../../src/ftcan_decoder.py`
- **FTCAN Protocol Decoder (Adapter):** `../../src/ftcan_protocol_decoder.py`
- **FTCAN Dialog (UI):** `../../src/ftcan_dialog.py`

### Official Protocol
- **FTCAN 2.0 Specification:** `Protocol_FTCAN20_Public_R026.pdf`
- **FuelTech Website:** https://fueltech.com.br/

### Related Tools
- **CAN Analyzer (Main App):** `../../README.md`
- **General CAN Tools:** `../general/README.md`
- **Arduino CAN Tools:** `../arduino/README.md`

---

## Troubleshooting

### Simulator Not Working

**Issue:** Script fails to import ftcan_decoder

**Solution:**
```bash
# Verify path structure
ls ../../src/ftcan_decoder.py

# Run from correct directory
cd tools/ftcan
python3 ftcan_simulator.py
```

---

### Decoder Not Recognizing Messages

**Issue:** CAN Analyzer doesn't decode simulated messages

**Solution:**
1. Verify FTCAN decoder is enabled:
   - Tools → Protocol Decoders → Check "FTCAN 2.0"
2. Check CAN bus speed is 1 Mbps
3. Verify extended ID (29-bit) support is enabled
4. Check simulator output for correct CAN IDs

---

### No Messages in CAN Analyzer

**Issue:** Simulator runs but no messages appear

**Solution:**
1. Verify CAN interface is connected
2. Check bus is at 1 Mbps (FTCAN requirement)
3. Ensure simulator is sending to correct interface
4. Use `candump` to verify messages on bus:
   ```bash
   candump can0
   ```

---

## Contributing

### Adding New Simulations

To add a new device simulation:

1. **Define device parameters:**
   ```python
   product_type_id = ProductType.YOUR_DEVICE
   unique_id = 0
   data_field_id = DataFieldID.FTCAN_2_0
   message_id = 0x1FF
   ```

2. **Create measures:**
   ```python
   measure = create_measure_data(data_id, raw_value)
   ```

3. **Create packet:**
   ```python
   data = create_single_packet([measure])
   ```

4. **Decode and display:**
   ```python
   result = decoder.decode_message(can_id, data)
   ```

### Reporting Issues

If you find issues with the simulator:
1. Provide simulator output
2. Include expected vs actual behavior
3. Share CAN Analyzer logs if applicable
4. Mention FTCAN device being simulated

---

## Resources

### Learning FTCAN
- **Protocol Basics:** See `../../src/ftcan_decoder.py` docstrings
- **Message Examples:** Run simulator with option 5
- **Real Hardware:** WB-O2 Nano, FT600 ECU documentation

### CAN Bus Basics
- **CAN 2.0B Extended:** 29-bit identifiers
- **Big-endian:** Most significant byte first
- **Bitrate:** 1 Mbps (FTCAN standard)

---

## License

Part of CAN Bus Analyzer project. See main repository for license information.
