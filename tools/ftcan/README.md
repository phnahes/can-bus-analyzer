# FuelTech FTCAN Tools

This directory contains specialized tools for working with FuelTech FTCAN protocol devices.

## SwitchPanel Viewer

Interactive GUI tool for visualizing and controlling FuelTech SwitchPanel devices.

### Features

- **Real-time Button State Visualization**: Displays all 8 buttons with live state updates
- **RGB LED Control**: Control individual button LED colors with RGB sliders
- **Quick Color Presets**: One-click access to common colors
- **Multiple Panel Support**: Compatible with all SwitchPanel variants:
  - Big 8-button
  - Mini 4-button
  - Mini 5-button
  - Mini 8-button
- **Message Logging**: View all CAN messages for debugging

### Requirements

```bash
pip install python-can PyQt6
```

### Usage

#### Basic Usage (Virtual CAN)

```bash
# Setup virtual CAN interface (Linux)
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Run the viewer
python3 switchpanel_viewer.py
```

#### With Real CAN Interface

```bash
# SocketCAN (Linux)
python3 switchpanel_viewer.py --interface socketcan --channel can0

# PCAN (Windows/Linux)
python3 switchpanel_viewer.py --interface pcan --channel PCAN_USBBUS1
```

### How It Works

#### Receiving Button States

The viewer listens for CAN messages with MessageID `0x320` (button states):

- **Byte 0**: Row 1 button states (bits 0-3 = buttons 1-4)
- **Byte 1**: Row 2 button states (bits 0-3 = buttons 5-8)

When a button is pressed, the corresponding bit is set to `1`.

#### Sending LED Control

The viewer sends CAN messages with MessageID `0x321` (LED control):

- **Byte 0**: Row 1 state mask (which buttons are active)
- **Byte 1**: Row 1 dimming (0x00-0xFF)
- **Byte 2**: Row 2 state mask
- **Byte 3**: Row 2 dimming
- **Bytes 4-7**: RGB values for each button

### Panel Variants

The tool supports all SwitchPanel variants with their respective ProductIDs:

| Variant | ProductID | Buttons |
|---------|-----------|---------|
| Big 8-button | 0x12200320 | 8 |
| Mini 4-button | 0x12210320 | 4 |
| Mini 5-button | 0x12218320 | 5 |
| Mini 8-button | 0x12228320 | 8 |

### Troubleshooting

#### No Messages Received

1. Check CAN interface is up: `ip link show vcan0`
2. Verify bitrate is 1 Mbps: `ip -details link show can0`
3. Check CAN bus termination (120Ω resistors)
4. Verify panel is powered and connected

#### LED Control Not Working

1. Ensure panel is receiving power
2. Check CAN wiring (CAN-H and CAN-L)
3. Verify ProductID matches your panel variant
4. Check message log for transmission errors

### Development

The viewer is built with PyQt6 and python-can. Key components:

- `SwitchPanelButton`: Visual button widget with LED color display
- `RGBControl`: RGB color picker with sliders
- `SwitchPanelViewer`: Main window with CAN communication

To extend functionality:

1. Add new color presets in `init_ui()`
2. Implement per-button LED control (currently global)
3. Add dimming control per row
4. Save/load color profiles

### References

- [FTCAN Protocol Documentation](../../docs/decoders/FTCAN.md)
- [FuelTech Official Documentation](https://www.fueltech.com.br)
- [TManiac.de Research](https://tmaniac.de/index.php?option=com_content&view=article&id=100)
