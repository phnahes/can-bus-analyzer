# CAN Gateway - Complete Documentation

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Bidirectional Gateway](#bidirectional-gateway)
- [Blocking Rules](#blocking-rules)
- [Message Modification](#message-modification)
- [Loop Prevention](#loop-prevention)
- [Visual Indicators](#visual-indicators)
- [Statistics](#statistics)
- [Use Cases](#use-cases)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **CAN Gateway** feature allows you to bridge and control message flow between multiple CAN buses. It acts as an intelligent router that can:

- Forward messages between buses (bidirectional or unidirectional)
- Block specific messages from being forwarded
- Modify messages as they pass through
- Prevent infinite loops in bidirectional configurations
- Track statistics in real-time

### Architecture

```
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────┐     ┌─────────┐
│ Source  │────>│ CAN1     │────>│   Gateway   │────>│ CAN2     │────>│ Dest    │
│ Device  │     │ Interface│     │ (Software)  │     │ Interface│     │ Device  │
└─────────┘     └──────────┘     └─────────────┘     └──────────┘     └─────────┘
                      │                  │                  │
                      │                  │                  │
                      v                  v                  v
                 Receives msg      Processes rules    Forwards msg
                 Shows in UI       (block/modify)     (if not blocked)
```

**Key Principle**: The Gateway processes messages **after** they are received by the interface but **before** they are forwarded to the destination. All received messages are **always displayed** in the UI, regardless of gateway actions.

---

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Bidirectional Routes** | Configure message flow in both directions (CAN1↔CAN2) |
| **Static Blocking** | Block specific message IDs from being forwarded |
| **Dynamic Blocking** | Automatically cycle through ID ranges, blocking each temporarily |
| **Message Modification** | Change message IDs and data bytes during forwarding |
| **Directional Rules** | Apply different rules based on route direction |
| **Loop Prevention** | Automatic detection and prevention of infinite message loops |
| **Visual Indicators** | Real-time feedback showing gateway actions in the UI |
| **Statistics Tracking** | Monitor forwarded, blocked, modified, and loop-prevented messages |
| **Configuration Save/Load** | Save gateway configurations as JSON files |

---

## Getting Started

### Prerequisites

1. **Multiple CAN Buses**: Configure at least 2 CAN buses in Settings (Ctrl+,)
2. **Connection**: Connect to the CAN buses
3. **Gateway Access**: Open Tools → Gateway (Ctrl+Shift+W)

### Quick Setup

**Basic Bidirectional Gateway:**

1. Open **Tools → Gateway** (Ctrl+Shift+W)
2. Click **"⇄ Add Bidirectional"** button
3. Select Source: `CAN1`, Destination: `CAN2`
4. Enable **"Enable Gateway"** checkbox
5. Enable **"Enable loop prevention"** (recommended)
6. Click **Apply** or **OK**

**Result**: All messages from CAN1 are forwarded to CAN2, and vice versa, with automatic loop prevention.

---

## Configuration

### Gateway Dialog

The Gateway configuration dialog has several sections:

#### 1. Transmission Control

**Enable Gateway**: Master switch to enable/disable all gateway functionality

**Routes Table**: Shows configured routes with columns:
- **From**: Source channel
- **To**: Destination channel  
- **Enabled**: Toggle to enable/disable individual routes
- **⇄ Indicator**: Shows bidirectional routes

**Buttons**:
- **➕ Add Route**: Add a single unidirectional route
- **⇄ Add Bidirectional**: Add both directions at once (recommended)
- **➖ Remove**: Remove selected route

#### 2. Loop Prevention Settings

**Enable loop prevention**: Prevents infinite message forwarding in bidirectional configurations

**How it works**:
- Messages forwarded by the gateway are marked with `gateway_processed` flag
- If a marked message arrives again, it's not forwarded (loop detected)
- Essential for bidirectional routes

**When to disable**: Only disable if you have a specific reason and understand the risks of infinite loops.

#### 3. Static Blocking Rules

Block specific message IDs from being forwarded.

**Configuration**:
1. Enter **Block ID** (e.g., `0x109` or `265`)
2. Click **➕ Add**
3. Rule is automatically created for all active source channels

**Table Columns**:
- **Source Channel**: Where the message originates
- **ID**: Message ID to block
- **Enabled**: Toggle to enable/disable rule

**Behavior**:
- Blocked messages **still appear in the UI** (you see them in Monitor/Tracer)
- Visual indicator (🚫) shows the message was blocked
- Message is **not forwarded** to destination

#### 4. Dynamic Blocking

Automatically cycle through a range of IDs, blocking each for a specified period.

**Configuration**:
1. **ID From**: Starting ID (e.g., `0x100`)
2. **ID To**: Ending ID (e.g., `0x1FF`)
3. **Period**: Time in milliseconds to block each ID (e.g., `1000`)
4. Click **➕ Add**

**Example**: Block IDs 0x100-0x1FF, cycling every 1 second
- t=0s: Block 0x100
- t=1s: Block 0x101
- t=2s: Block 0x102
- ...
- After 0x1FF, cycle back to 0x100

**Use Cases**:
- Testing ECU behavior when messages are intermittently missing
- Simulating network issues
- Debugging timing-sensitive systems

#### 5. Message Modification

Modify message IDs and/or data bytes as they pass through the gateway.

**Configuration**:
1. Enter **Modify ID** (e.g., `0x200`)
2. Click **✏️ Add Modify**
3. In the Modify Rule Editor:
   - **New ID**: Change message ID (optional)
   - **Data Mask**: Select which bytes to modify
   - **New Data**: Enter new values for selected bytes
4. Click **OK**

**Table Columns**:
- **Source Channel**: Where the message originates
- **ID**: Original message ID
- **New ID**: Modified ID (or "-" if unchanged)
- **Data Mask**: Number of bytes being modified
- **Enabled**: Toggle to enable/disable rule

**Example**: Change ID 0x200 to 0x201 and modify byte 0
```
Original:  ID=0x200  Data=[12 34 56 78 9A BC DE F0]
Modified:  ID=0x201  Data=[FF 34 56 78 9A BC DE F0]
                           ^^
                         Byte 0 modified
```

#### 6. Statistics

Real-time tracking of gateway operations:

- **Forwarded**: Total messages successfully forwarded
- **Blocked**: Total messages blocked by rules
- **Modified**: Total messages modified
- **Loops Prevented**: Messages blocked to prevent infinite loops

**Reset Stats**: Click to reset all counters to zero

---

## Bidirectional Gateway

### What is Bidirectional?

A bidirectional gateway forwards messages in **both directions** simultaneously:
- CAN1 → CAN2 (forward direction)
- CAN2 → CAN1 (reverse direction)

### Why Use Bidirectional?

**Common Use Cases**:
1. **Network Bridge**: Connect two isolated CAN networks
2. **Gateway ECU Simulation**: Simulate automotive gateway behavior
3. **Multi-Network Testing**: Test devices that communicate across networks
4. **Protocol Translation**: Forward messages between different network segments

### Configuration

**Method 1: Quick Bidirectional Button** (Recommended)
```
1. Select Source: CAN1
2. Select Destination: CAN2
3. Click "⇄ Add Bidirectional"
4. Both routes created automatically:
   - CAN1 → CAN2
   - CAN2 → CAN1
```

**Method 2: Manual Route Addition**
```
1. Add route: CAN1 → CAN2
2. Add route: CAN2 → CAN1
3. Both routes must be enabled
```

### Loop Prevention (Critical!)

**Problem**: Without loop prevention, messages can circulate infinitely:

```
CAN1: Message 0x100 → Gateway → CAN2
CAN2: Receives 0x100 → Gateway → CAN1
CAN1: Receives 0x100 → Gateway → CAN2
... (infinite loop)
```

**Solution**: Enable "Loop prevention" (enabled by default)

```
CAN1: Message 0x100 (gateway_processed=False) → Gateway → CAN2
CAN2: Receives 0x100 (gateway_processed=True) → Gateway → ❌ BLOCKED
Statistics: loops_prevented += 1
```

**How it works**:
1. Original message has `gateway_processed=False`
2. Gateway forwards it and marks copy as `gateway_processed=True`
3. If marked message returns, gateway blocks it
4. Loop prevented, statistics updated

### Visual Indicators

Messages in bidirectional configurations show their gateway status:

| Indicator | Meaning |
|-----------|---------|
| `CAN1 ➡️` | Message forwarded from CAN1 to CAN2 |
| `CAN2 ➡️` | Message forwarded from CAN2 to CAN1 |
| `CAN1 🚫` | Message blocked (not forwarded) |
| `CAN1 ✏️` | Message modified before forwarding |
| `CAN1 🔄` | Loop detected and prevented |

---

## Blocking Rules

### Static Blocking

Block specific message IDs from being forwarded.

**Example 1: Block Single ID**
```
Configuration:
  - Block ID: 0x109
  - Source: CAN1
  - Enabled: ✓

Result:
  - CAN1 receives 0x109 → Shows "CAN1 🚫 0x109" in UI
  - Gateway blocks forwarding → CAN2 does NOT receive 0x109
  - Other messages forwarded normally
```

**Example 2: Block Multiple IDs**
```
Configuration:
  - Block ID: 0x100, Source: CAN1
  - Block ID: 0x200, Source: CAN1
  - Block ID: 0x300, Source: CAN2

Result:
  - CAN1→CAN2: 0x100 and 0x200 blocked
  - CAN2→CAN1: 0x300 blocked
  - All other messages forwarded
```

### Directional Blocking

Block messages only in specific directions (future feature).

**Example**:
```
Configuration:
  - Block ID: 0x109
  - Source: CAN1
  - Destination: CAN2 (specific)

Result:
  - CAN1→CAN2: 0x109 blocked
  - CAN2→CAN1: 0x109 forwarded (not blocked)
```

### Dynamic Blocking

Automatically cycle through ID ranges.

**Example: Scan for Critical IDs**
```
Configuration:
  - ID From: 0x100
  - ID To: 0x110
  - Period: 500ms
  - Source: CAN1

Timeline:
  t=0.0s: Block 0x100
  t=0.5s: Block 0x101
  t=1.0s: Block 0x102
  ...
  t=8.0s: Block 0x110
  t=8.5s: Block 0x100 (cycle repeats)

Use Case:
  - Test which IDs are critical for system operation
  - Find dependencies between messages
  - Debug timing-sensitive issues
```

---

## Message Modification

### ID Modification

Change the message ID as it passes through the gateway.

**Example: ID Translation**
```
Configuration:
  - Modify ID: 0x200
  - Source: CAN1
  - New ID: 0x201

Result:
  CAN1: Sends 0x200 [12 34 56 78]
  UI:   Shows "CAN1 ✏️ 0x200 [12 34 56 78]"
  CAN2: Receives 0x201 [12 34 56 78]
```

**Use Case**: Protocol translation between networks using different ID schemes

### Data Modification

Change specific data bytes while preserving others.

**Example: Modify Single Byte**
```
Configuration:
  - Modify ID: 0x300
  - Source: CAN1
  - Data Mask: [True, False, False, False, False, False, False, False]
  - New Data:  [FF, 00, 00, 00, 00, 00, 00, 00]

Result:
  CAN1: Sends 0x300 [12 34 56 78 9A BC DE F0]
  UI:   Shows "CAN1 ✏️ 0x300 [12 34 56 78 9A BC DE F0]"
  CAN2: Receives 0x300 [FF 34 56 78 9A BC DE F0]
                       ^^
                     Modified
```

**Use Case**: Inject test values, simulate sensor failures, override safety checks

### Combined Modification

Change both ID and data simultaneously.

**Example: Complete Message Transformation**
```
Configuration:
  - Modify ID: 0x400
  - Source: CAN1
  - New ID: 0x500
  - Data Mask: [True, True, False, False, False, False, False, False]
  - New Data:  [AA, BB, 00, 00, 00, 00, 00, 00]

Result:
  CAN1: Sends 0x400 [11 22 33 44 55 66 77 88]
  UI:   Shows "CAN1 ✏️ 0x400 [11 22 33 44 55 66 77 88]"
  CAN2: Receives 0x500 [AA BB 33 44 55 66 77 88]
```

---

## Loop Prevention

### Why Loop Prevention?

In bidirectional configurations, messages can create infinite loops:

```
Without Loop Prevention:
  CAN1 → Gateway → CAN2 → Gateway → CAN1 → Gateway → CAN2 → ...
  (Infinite loop, network congestion, system crash)

With Loop Prevention:
  CAN1 → Gateway → CAN2 → Gateway → ❌ BLOCKED
  (Loop detected, message dropped, system stable)
```

### How It Works

**Technical Implementation**:

1. **Message Marking**: Each `CANMessage` has a `gateway_processed` flag
2. **Initial State**: Messages from the bus have `gateway_processed=False`
3. **Forwarding**: Gateway creates a copy with `gateway_processed=True`
4. **Loop Detection**: If a message with `gateway_processed=True` arrives, it's blocked
5. **Statistics**: `loops_prevented` counter is incremented

**Code Flow**:
```python
def _process_gateway_message(msg):
    # Check if already processed
    if msg.gateway_processed and loop_prevention_enabled:
        stats['loops_prevented'] += 1
        return  # Don't forward again
    
    # Forward to destination
    forwarded_msg = create_copy(msg)
    forwarded_msg.gateway_processed = True
    send_to_destination(forwarded_msg)
```

### Configuration

**Enable/Disable**:
- Checkbox in Gateway dialog: "Enable loop prevention"
- Default: **Enabled** (recommended)
- Disable only if you have a specific reason

**When to Disable**:
- Single-direction gateway (no loops possible)
- Custom loop prevention mechanism
- Testing loop behavior

**Performance Impact**: Minimal (simple boolean check)

---

## Visual Indicators

### Gateway Action Indicators

Messages in the UI show their gateway status with emoji indicators:

| Emoji | Action | Description |
|-------|--------|-------------|
| 🚫 | Blocked | Message received but not forwarded (blocked by rule) |
| ➡️ | Forwarded | Message successfully forwarded to destination |
| ✏️ | Modified | Message modified (ID or data changed) before forwarding |
| 🔄 | Loop Prevented | Message blocked to prevent infinite loop |

### Display Examples

**Monitor Mode**:
```
# | Count | Channel    | ID    | DLC | Data              | Period
1 | 523   | CAN1 🚫    | 0x109 | 8   | 12 34 56 78 ...  | 10ms
2 | 1024  | CAN1 ➡️    | 0x200 | 4   | AA BB CC DD      | 20ms
3 | 87    | CAN2 ✏️    | 0x300 | 2   | 11 22            | 50ms
```

**Tracer Mode**:
```
# | Time      | Channel    | ID    | DLC | Data
1 | 12.345    | CAN1 🚫    | 0x109 | 8   | 12 34 56 78 9A BC DE F0
2 | 12.365    | CAN1 ➡️    | 0x200 | 4   | AA BB CC DD
3 | 12.385    | CAN2 ✏️    | 0x300 | 2   | 11 22
```

### Interpretation

**Blocked (🚫)**:
- Interface **received** the message physically
- Gateway **blocked** forwarding due to blocking rule
- Message **appears in UI** for visibility
- Message **NOT sent** to destination

**Forwarded (➡️)**:
- Interface **received** the message
- Gateway **forwarded** to destination successfully
- Message **appears in UI** with indicator
- Destination **receives** the message

**Modified (✏️)**:
- Interface **received** original message
- Gateway **modified** ID and/or data
- UI shows **original** message with indicator
- Destination receives **modified** version

**Loop Prevented (🔄)**:
- Message already processed by gateway
- Would create infinite loop if forwarded
- Gateway **blocks** to prevent loop
- Statistics counter incremented

---

## Statistics

### Real-Time Tracking

The Gateway dialog shows live statistics:

```
Forwarded: 1523 | Blocked: 45 | Modified: 12 | Loops Prevented: 8
```

### Metrics Explained

| Metric | Description | When It Increases |
|--------|-------------|-------------------|
| **Forwarded** | Messages successfully sent to destination | Every time a message is forwarded |
| **Blocked** | Messages blocked by blocking rules | When a blocking rule matches |
| **Modified** | Messages modified before forwarding | When a modification rule is applied |
| **Loops Prevented** | Messages blocked to prevent loops | When `gateway_processed` message arrives |

### Per-Route Statistics (Internal)

The gateway also tracks statistics per route:

```python
route_stats = {
    "CAN1->CAN2": 1523,
    "CAN2->CAN1": 987
}
```

**Access**: Currently internal only (future: display in UI)

### Reset Statistics

Click **"Reset Stats"** button to reset all counters to zero.

**Use Cases**:
- Start fresh test session
- Measure specific scenario
- Clear old data

---

## Use Cases

### 1. Network Bridge

**Scenario**: Connect two isolated CAN networks

**Configuration**:
```
Routes:
  - CAN1 ↔ CAN2 (bidirectional)
Loop Prevention: Enabled
Blocking: None
Modification: None
```

**Result**: All messages flow freely between networks

---

### 2. Selective Message Filtering

**Scenario**: Forward most messages but block specific IDs

**Configuration**:
```
Routes:
  - CAN1 → CAN2
Blocking:
  - Block 0x109 from CAN1
  - Block 0x200 from CAN1
```

**Result**: 
- CAN1 messages forwarded to CAN2
- Except 0x109 and 0x200 (blocked)

---

### 3. Protocol Translation

**Scenario**: Translate message IDs between networks

**Configuration**:
```
Routes:
  - CAN1 → CAN2
Modification:
  - 0x100 → 0x200 (CAN1 to CAN2)
  - 0x101 → 0x201 (CAN1 to CAN2)
```

**Result**: Messages arrive at CAN2 with translated IDs

---

### 4. ECU Simulation

**Scenario**: Simulate gateway ECU behavior

**Configuration**:
```
Routes:
  - CAN1 ↔ CAN2 (bidirectional)
Blocking:
  - Block 0x7DF from CAN1 (diagnostic requests)
Modification:
  - Modify 0x300: inject test data
Loop Prevention: Enabled
```

**Result**: Gateway acts like real automotive gateway

---

### 5. Testing Network Resilience

**Scenario**: Test system behavior when messages are missing

**Configuration**:
```
Routes:
  - CAN1 → CAN2
Dynamic Blocking:
  - ID Range: 0x100-0x1FF
  - Period: 1000ms
  - Source: CAN1
```

**Result**: Each ID blocked for 1 second in sequence, testing system response

---

### 6. Data Injection

**Scenario**: Override sensor values for testing

**Configuration**:
```
Routes:
  - CAN1 → CAN2
Modification:
  - ID 0x400: Modify byte 0 to 0xFF (simulate max value)
  - ID 0x401: Modify bytes 0-1 to 0x00 (simulate zero)
```

**Result**: Destination receives modified sensor values

---

## Advanced Topics

### Directional Rules

Block or modify messages only in specific directions.

**Configuration** (current implementation):
```python
GatewayBlockRule(
    can_id=0x109,
    channel="CAN1",
    destination="CAN2",  # Only blocks CAN1→CAN2
    enabled=True
)
```

**Behavior**:
- CAN1→CAN2: 0x109 blocked
- CAN2→CAN1: 0x109 forwarded (not affected)

**Use Case**: Asymmetric gateway behavior

---

### Multiple Routes

Configure multiple routes simultaneously.

**Example**:
```
Routes:
  - CAN1 → CAN2
  - CAN1 → CAN3
  - CAN2 → CAN3
```

**Behavior**:
- Message from CAN1 forwarded to both CAN2 and CAN3
- Message from CAN2 forwarded only to CAN3
- Loop prevention applies to all routes

---

### Bench Test (Arduino) - Gateway in the Lab

This section describes a simple bench/lab setup to validate the Gateway feature using Arduino + MCP2515 modules:

- Two Arduinos act as the **PC interfaces** (USB CDC serial to CAN) using `tools/arduino/arduino_usb_cdc.ino`
- One Arduino acts as a **traffic source** using `tools/arduino/arduino_msg_generator.ino`
- One Arduino acts as a **traffic sink** using `tools/arduino/arduino_msg_receiver.ino`

The idea is to create two independent CAN buses and place the PC/app gateway between them:

```
CAN BUS A (source side)                          CAN BUS B (destination side)

[Arduino: msg_generator] -- CAN-A -- [Arduino: usb_cdc #1] --USB--> PC (CAN1)
                                                           |
                                                           |  Gateway (CAN1 -> CAN2)
                                                           v
[Arduino: msg_receiver ] -- CAN-B -- [Arduino: usb_cdc #2] --USB--> PC (CAN2)
```

#### Hardware required
- 4x Arduino-compatible boards (UNO/Nano/etc)
- 4x MCP2515 CAN modules + transceivers
- Correct CAN wiring (CANH/CANL + common GND on each bus)
- 120 ohm termination on each CAN bus (typically at both ends of the bus)

#### Step 1: Flash the sketches

1) Interface boards (2x):
- Upload `tools/arduino/arduino_usb_cdc.ino` to **two** Arduinos (these are the CAN adapters the PC will connect to)

Note about boards without `serialEvent()`:
- In `arduino_usb_cdc.ino` there is a comment about Leonardo/Pro Micro/Esplora.
- If your board does not call `serialEvent()`, uncomment the `lineReader->process()` lines inside `loop()` so commands are processed.

2) Source board (1x):
- Upload `tools/arduino/arduino_msg_generator.ino`

3) Destination board (1x):
- Upload `tools/arduino/arduino_msg_receiver.ino`

Important: check and match these constants in each sketch to your MCP2515 module:
- `CAN_CRYSTAL_CLOCK` (common modules are 8 MHz or 16 MHz)
- `CAN_SPEED` (e.g. 250k/500k/1M, must match within each CAN bus)
- `SPI_CS_PIN` and `CAN_INT_PIN` (must match your wiring)

#### Step 2: Wire the two CAN buses

Build two separate CAN networks:

- CAN BUS A:
  - `msg_generator.ino` Arduino <-> `arduino_usb_cdc.ino` interface Arduino
- CAN BUS B:
  - `msg_receiver.ino` Arduino <-> `arduino_usb_cdc.ino` interface Arduino

Keep the buses physically separated (do not connect CAN-A to CAN-B directly). The Gateway in the PC/app is what bridges them.

#### Step 3: Configure CAN Analyzer for two channels

1) Plug the two `arduino_usb_cdc.ino` boards into the PC via USB
2) Open **Settings** and configure 2 CAN buses (example):
   - CAN1: select the serial device for usb_cdc #1
   - CAN2: select the serial device for usb_cdc #2
   - Use the same CAN baudrate you configured in the sketches
3) Connect to the buses (Connect button)

You should see live traffic on CAN1 coming from the generator (Monitor/Tracer), even before enabling the Gateway.

#### Step 4: Enable the Gateway (CAN1 -> CAN2)

1) Open Tools -> Gateway
2) Add a route:
   - From: CAN1
   - To: CAN2
   - Enabled: yes
3) Enable "Enable Gateway"
4) (Recommended) Keep loop prevention enabled

#### Step 5: Validate forwarding

You have two simple validations:

1) On the receiver side:
- Open Serial Monitor for the Arduino running `arduino_msg_receiver.ino`
- You should see the forwarded frames arriving on CAN BUS B (timestamps, IDs, data)

2) In CAN Analyzer UI:
- You should see gateway indicators in the Channel column showing forwarding activity (for example, CAN1 -> CAN2 forwarding)

If you see messages on CAN1 but nothing on CAN2 / receiver:
- Verify both CAN buses are connected in the app
- Verify baudrate and MCP2515 crystal settings match
- Verify termination and wiring (CANH/CANL are not swapped)
- Verify both `arduino_usb_cdc.ino` interfaces are responsive (serial device present)

---

### Configuration Files

Save and load gateway configurations.

**File Format**: JSON (`.json`)

**Structure**:
```json
{
  "version": "1.0",
  "file_type": "gateway",
  "gateway_config": {
    "routes": [
      {"source": "CAN1", "destination": "CAN2", "enabled": true},
      {"source": "CAN2", "destination": "CAN1", "enabled": true}
    ],
    "enabled": true,
    "loop_prevention_enabled": true,
    "max_hops": 1,
    "block_rules": [
      {"can_id": 265, "channel": "CAN1", "enabled": true, "destination": null}
    ],
    "dynamic_blocks": [],
    "modify_rules": []
  }
}
```

**Operations**:
- **Save**: Gateway dialog → "Save Configuration" → Choose filename
- **Load**: Gateway dialog → "Load Configuration" → Select file

**Use Cases**:
- Reuse configurations across sessions
- Share configurations with team
- Version control gateway setups

---

## Troubleshooting

### Messages Not Forwarding

**Symptoms**: Messages appear in source channel but not in destination

**Checklist**:
1. ✓ Gateway enabled? (checkbox in dialog)
2. ✓ Route enabled? (checkbox in routes table)
3. ✓ Source and destination correct?
4. ✓ Both interfaces connected?
5. ✓ No blocking rule matching the message?
6. ✓ Loop prevention not blocking? (check `loops_prevented` counter)

**Debug**:
- Check gateway statistics (should see "Forwarded" increasing)
- Look for visual indicators (🚫 = blocked, ➡️ = forwarded)
- Verify message source matches route source

---

### High "Loops Prevented" Count

**Symptoms**: `loops_prevented` counter increasing rapidly

**Causes**:
1. **Bidirectional routes without loop prevention**: Disable and re-enable loop prevention
2. **Message generators on both sides**: Normal if devices on both networks are transmitting
3. **Gateway misconfiguration**: Check routes for circular paths

**Solutions**:
- Ensure loop prevention is enabled
- Review route configuration
- Check if external devices are echoing messages

---

### Messages Blocked Unexpectedly

**Symptoms**: Messages you want forwarded are being blocked

**Checklist**:
1. ✓ Check blocking rules (might have unintended rule)
2. ✓ Check dynamic blocks (might be in active range)
3. ✓ Verify message ID matches what you expect
4. ✓ Check source channel (rule might be for wrong channel)

**Debug**:
- Look for 🚫 indicator in UI
- Review blocking rules table
- Temporarily disable all blocking rules to test

---

### Modification Not Working

**Symptoms**: Messages not being modified as expected

**Checklist**:
1. ✓ Modification rule enabled?
2. ✓ Message ID matches rule?
3. ✓ Source channel correct?
4. ✓ Data mask configured correctly?

**Debug**:
- Look for ✏️ indicator in UI (shows modification is active)
- Check "Modified" counter in statistics
- Double-click modification rule to review settings
- Verify byte order (0-7, left to right)

---

### Performance Issues

**Symptoms**: UI slow, messages delayed, high CPU usage

**Causes**:
1. **Too many modification rules**: Each rule adds processing overhead
2. **High message rate + complex rules**: Combination can slow processing
3. **Dynamic blocks with short periods**: Frequent ID changes add overhead

**Solutions**:
- Reduce number of modification rules
- Increase dynamic block period (e.g., 1000ms instead of 100ms)
- Disable unused rules
- Use specific blocking instead of dynamic blocks

---

### Gateway Not Appearing in Menu

**Symptoms**: Can't find Gateway option in Tools menu

**Cause**: Less than 2 CAN buses configured

**Solution**:
1. Open Settings (Ctrl+,)
2. Configure at least 2 CAN buses
3. Save and reconnect
4. Gateway option will appear in Tools menu

---

## Summary

The CAN Gateway is a powerful tool for:
- **Bridging** multiple CAN networks
- **Filtering** message traffic
- **Modifying** messages in real-time
- **Testing** network resilience
- **Simulating** gateway ECU behavior

**Key Features**:
- ✅ Bidirectional message forwarding
- ✅ Automatic loop prevention
- ✅ Static and dynamic blocking
- ✅ Message ID and data modification
- ✅ Real-time visual indicators
- ✅ Comprehensive statistics
- ✅ Save/load configurations

**Best Practices**:
1. Always enable loop prevention for bidirectional routes
2. Use visual indicators to verify gateway operation
3. Monitor statistics to track gateway activity
4. Save configurations for reuse
5. Test with simple setups before adding complexity

**Next Steps**:
- Configure your first gateway route
- Experiment with blocking rules
- Try message modification
- Monitor statistics in real-time

For more information, see the main [README](../README.md) or open an issue on GitHub.

