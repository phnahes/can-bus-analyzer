# CAN Bus Analyzer – Tools

This directory contains utilities and scripts grouped by category. Each subdirectory has its own README with detailed usage.

---

## Directory index

| Directory | Description |
|-----------|-------------|
| **[arduino/](arduino/README.md)** | Arduino sketches for CAN: message generator, message receiver, OBD-II ECU simulator, and using Arduino + MCP2515 as a Lawicel SLCAN interface. Wiring, libraries, and protocol reference are in the Arduino README. |
| **[ftcan/](ftcan/README.md)** | FTCAN 2.0 (FuelTech) tools: FTCAN message simulator and configuration capture/replay for ECUs and WB-O2 Nano. |
| **[general/](general/README.md)** | General CAN utilities: send messages from CLI (`send_can_message.py`), baudrate detection, OBD-II polling, and other scripts that work with any SLCAN or SocketCAN interface. |

---

## Quick links

- **Arduino (generator, receiver, OBD2 sim, SLCAN):** [arduino/README.md](arduino/README.md)
- **FTCAN simulator and config capture:** [ftcan/README.md](ftcan/README.md)
- **Send CAN messages, baudrate detect, OBD2 poller:** [general/README.md](general/README.md)
