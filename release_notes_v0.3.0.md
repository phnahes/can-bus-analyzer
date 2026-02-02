# CAN Analyzer v0.3.0 – CAN Gateway & Split-Screen

## Added – CAN Gateway & Split-Screen

### CAN Gateway
- **Gateway Mode**: Bridge and filter messages between two CAN buses
- **Bidirectional control**: Enable/disable CAN1→CAN2 and CAN2→CAN1 independently
- **Static blocking**: Block specific IDs per channel; multiple rules supported
- **Dynamic blocking**: Cycle through ID ranges with configurable period (ECU testing)
- **Message modification** (framework ready): ID/data transformation in transit
- **Statistics**: Forwarded, blocked, modified counts; reset; shortcut Ctrl+W
- **Configuration dialog**: Full gateway UI; shortcut Ctrl+W

### Split-Screen Monitor
- **Split-Screen Mode**: View two channels side by side
- **Channel selection**: Choose left/right panel channel; independent filtering
- **Shortcut**: Ctrl+D to toggle split-screen
- **Use cases**: Compare traffic, monitor gateway, timing analysis, multi-network debug

### Backend & i18n
- **GatewayConfig**, **GatewayBlockRule**, **GatewayDynamicBlock**, **GatewayModifyRule**
- **CANBusManager** gateway processing; gateway thread management
- **Translations**: Gateway and Split-Screen (EN, PT, ES, DE, FR)

## Changed
- Menu: Gateway under Tools; Split-Screen under View
- **CANBusManager**: Gateway processing; messages pass through gateway rules before display
- **Documentation**: Screenshots moved to `docs/images/`; README paths updated

## Documentation
- CAN Gateway and Split-Screen sections in README; keyboard shortcuts; CAN-Hacker reference

---

**Full changelog**: [v0.2.0...v0.3.0](https://github.com/phnahes/can-bus-analyzer/compare/v0.2.0...v0.3.0)
