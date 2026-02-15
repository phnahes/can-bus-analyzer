"""
CAN Bus Manager - Manages multiple CAN bus instances

Supports:
- Multiple CAN interfaces (CAN1, CAN2, etc.)
- Independent configuration per bus (channel, baudrate)
- Unified message callback with source identification
- Connect/disconnect all or individual buses
"""

import threading
import time
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False
    print("python-can not installed. Simulation mode activated.")

from .models import CANMessage, GatewayConfig, GatewayRoute


@dataclass
class CANBusConfig:
    """Configuration for a single CAN bus"""
    name: str
    channel: str
    baudrate: int
    listen_only: bool = True
    interface: str = 'socketcan'  # socketcan, slcan, etc.
    receive_own_messages: bool = True  # if True, this channel sees its own TX (for display)
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.name:
            raise ValueError("Bus name cannot be empty")
        if self.baudrate <= 0:
            raise ValueError("Baudrate must be positive")


class CANBusInstance:
    """Represents a single CAN bus interface"""
    
    def __init__(self, config: CANBusConfig, message_callback: Optional[Callable] = None, disconnect_callback: Optional[Callable] = None):
        self.config = config
        self.bus: Optional[can.BusABC] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.connected = False
        self.message_callback = message_callback
        self.disconnect_callback = disconnect_callback  # Callback when device disconnects
        self._lock = threading.Lock()
        self._consecutive_errors = 0  # Track consecutive errors for disconnect detection
        self._max_consecutive_errors = 50  # Threshold for considering device disconnected
        self._last_message_time = 0  # Track last message received time
        self._watchdog_timeout = 10.0  # Seconds without messages before checking connection
        self._watchdog_thread: Optional[threading.Thread] = None
    
    def connect(self) -> bool:
        """Connect to the CAN bus"""
        if self.connected:
            return True
        
        try:
            if not CAN_AVAILABLE:
                print(f"[{self.config.name}] CAN not available, simulation mode")
                self.connected = True
                self.running = True
                self.thread = threading.Thread(
                    target=self._receive_loop_simulation, 
                    daemon=True,
                    name=f"CANRx-{self.config.name}"
                )
                self.thread.start()
                return True
            
            # Detect interface type from channel
            interface = self.config.interface
            channel = self.config.channel
            is_serial = (channel.startswith('/dev/tty') or channel.startswith('/dev/cu.') or
                        channel.startswith('COM'))
            if is_serial:
                interface = 'slcan'
            elif channel in ['can0', 'can1', 'vcan0', 'vcan1']:
                interface = 'socketcan'
            
            # receive_own_messages=True: the channel that sends also sees its own frames
            # (so e.g. CAN2 TX appears in CAN2 receive pane). Set False to hide own TX.
            receive_own = getattr(self.config, 'receive_own_messages', True)
            self.bus = can.interface.Bus(
                channel=self.config.channel,
                interface=interface,
                bitrate=self.config.baudrate,
                receive_own_messages=receive_own
            )
            
            self.connected = True
            self.running = True
            self._last_message_time = time.time()  # Initialize watchdog timer
            
            # Start receive thread
            self.thread = threading.Thread(
                target=self._receive_loop,
                daemon=True,
                name=f"CANRx-{self.config.name}"
            )
            self.thread.start()
            
            # Start watchdog thread for serial devices
            if self.config.channel.startswith('/dev/') or self.config.channel.startswith('COM'):
                self._watchdog_thread = threading.Thread(
                    target=self._connection_watchdog,
                    daemon=True,
                    name=f"CANWatch-{self.config.name}"
                )
                self._watchdog_thread.start()
            
            print(f"[{self.config.name}] Connected: {self.config.channel} @ {self.config.baudrate} bps")
            return True
            
        except Exception as e:
            print(f"[{self.config.name}] Connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the CAN bus"""
        self.running = False
        
        # Wait for threads to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=1.0)
        
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception as e:
                print(f"[{self.config.name}] Shutdown error (ignored): {e}")
            finally:
                self.bus = None
        
        self.connected = False
        print(f"[{self.config.name}] Disconnected")
    
    def send(self, msg) -> bool:
        """Send a CAN message (accepts CANMessage or can.Message)"""
        if not self.connected:
            return False
        
        try:
            # Check if it's a python-can Message or our CANMessage
            # Use hasattr to check for arbitration_id (python-can) vs can_id (our dataclass)
            if hasattr(msg, 'arbitration_id'):
                # Already a python-can Message, send directly
                can_msg = msg
                msg_id = msg.arbitration_id
                msg_data = msg.data
            elif hasattr(msg, 'can_id'):
                # Our CANMessage dataclass, convert to python-can Message
                can_msg = can.Message(
                    arbitration_id=msg.can_id,
                    data=msg.data[:msg.dlc],
                    is_extended_id=msg.is_extended,
                    is_remote_frame=msg.is_rtr
                )
                msg_id = msg.can_id
                msg_data = msg.data
            else:
                print(f"[{self.config.name}] Send error: Unknown message type {type(msg)}")
                return False
            
            if self.bus:
                self.bus.send(can_msg)
                return True
            else:
                # Simulation mode (no print needed, logger handles it)
                return True
        except Exception as e:
            print(f"[{self.config.name}] Send error: {e}")
            return False
    
    def _receive_loop(self):
        """Receive loop for real CAN bus"""
        error_count = 0
        last_error_time = 0
        
        while self.running:
            try:
                if self.bus:
                    message = self.bus.recv(timeout=0.1)
                    if message and self.message_callback:
                        can_msg = CANMessage(
                            timestamp=message.timestamp,
                            can_id=message.arbitration_id,
                            dlc=message.dlc,
                            data=bytes(message.data),
                            is_extended=message.is_extended_id,
                            is_rtr=message.is_remote_frame,
                            channel=self.config.channel if isinstance(self.config.channel, int) else 1,
                            source=self.config.name  # Mark source bus
                        )
                        self.message_callback(self.config.name, can_msg)
                        # Reset error counts on successful receive
                        error_count = 0
                        self._consecutive_errors = 0
                        self._last_message_time = time.time()  # Update watchdog timer
                else:
                    time.sleep(0.1)
            except Exception as e:
                if self.running:  # Only log if not shutting down
                    # Suppress repetitive serial/parsing errors (common with SLCAN noise)
                    error_str = str(e)
                    
                    # Check for critical disconnect errors
                    is_disconnect_error = any(x in error_str for x in [
                        'device disconnected', 'Device or resource busy',
                        'No such file or directory', 'I/O error',
                        'device reports readiness', 'Errno 5', 'Errno 6',
                        'Errno 19'  # ENODEV - No such device
                    ])
                    
                    is_parse_error = any(x in error_str for x in [
                        'invalid literal', 'non-hexadecimal', 'Could not read from serial'
                    ])
                    
                    current_time = time.time()
                    
                    if is_disconnect_error:
                        # Critical error - device likely disconnected
                        self._consecutive_errors += 1
                        print(f"[{self.config.name}] Critical error detected: {e}")
                        
                        if self._consecutive_errors >= self._max_consecutive_errors:
                            print(f"[{self.config.name}] Device appears to be disconnected (too many errors)")
                            # Notify disconnect callback
                            if self.disconnect_callback:
                                self.disconnect_callback(self.config.name, error_str)
                            # Auto-disconnect
                            self.running = False
                            self.connected = False
                            break
                    elif is_parse_error:
                        error_count += 1
                        # Only log every 10th error or every 5 seconds
                        if error_count % 10 == 1 or (current_time - last_error_time) > 5.0:
                            print(f"[{self.config.name}] Serial/parse errors detected ({error_count} total) - possible line noise")
                            last_error_time = current_time
                    else:
                        # Log non-parse errors normally
                        self._consecutive_errors += 1
                        print(f"[{self.config.name}] Receive error: {e}")
                        
                        # Check if too many consecutive errors
                        if self._consecutive_errors >= self._max_consecutive_errors:
                            print(f"[{self.config.name}] Too many consecutive errors, assuming device disconnected")
                            if self.disconnect_callback:
                                self.disconnect_callback(self.config.name, error_str)
                            self.running = False
                            self.connected = False
                            break
                
                time.sleep(0.1)
    
    def _connection_watchdog(self):
        """Monitor connection health and detect silent disconnections"""
        print(f"[{self.config.name}] Connection watchdog started")
        
        while self.running and self.connected:
            time.sleep(2.0)  # Check every 2 seconds
            
            if not self.running:
                break
            
            # Check if we haven't received messages for too long
            time_since_last_msg = time.time() - self._last_message_time
            
            if time_since_last_msg > self._watchdog_timeout:
                # No messages for too long - check if device is still there
                print(f"[{self.config.name}] Watchdog: No messages for {time_since_last_msg:.1f}s, checking connection...")
                
                # Try to verify if device is still connected
                if self.bus:
                    try:
                        # For serial devices, check if port is still accessible
                        if hasattr(self.bus, 'bus') and hasattr(self.bus.bus, 'is_open'):
                            if not self.bus.bus.is_open:
                                print(f"[{self.config.name}] Watchdog: Serial port is closed!")
                                if self.disconnect_callback:
                                    self.disconnect_callback(self.config.name, "Serial port closed")
                                self.running = False
                                self.connected = False
                                break
                        
                        # Check if we can still access the device file (for serial devices)
                        import os
                        if self.config.channel.startswith('/dev/'):
                            if not os.path.exists(self.config.channel):
                                print(f"[{self.config.name}] Watchdog: Device file no longer exists!")
                                if self.disconnect_callback:
                                    self.disconnect_callback(self.config.name, "Device file removed")
                                self.running = False
                                self.connected = False
                                break
                    except Exception as e:
                        print(f"[{self.config.name}] Watchdog: Error checking connection: {e}")
                        if self.disconnect_callback:
                            self.disconnect_callback(self.config.name, f"Connection check failed: {e}")
                        self.running = False
                        self.connected = False
                        break
        
        print(f"[{self.config.name}] Connection watchdog stopped")
    
    def _receive_loop_simulation(self):
        """Simulation mode receive loop"""
        sample_messages = [
            (0x100, 8, bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])),
            (0x200, 4, bytes([0xAA, 0xBB, 0xCC, 0xDD])),
            (0x300, 2, bytes([0x12, 0x34])),
        ]
        msg_index = 0
        
        while self.running:
            if self.message_callback:
                can_id, dlc, data = sample_messages[msg_index]
                msg_index = (msg_index + 1) % len(sample_messages)
                
                msg = CANMessage(
                    timestamp=time.time(),
                    can_id=can_id,
                    dlc=dlc,
                    data=data,
                    channel=self.config.channel if isinstance(self.config.channel, int) else 1,
                    source=self.config.name
                )
                self.message_callback(self.config.name, msg)
            
            time.sleep(0.5)  # Slower for simulation


class CANBusManager:
    """Manages multiple CAN bus instances with Gateway support"""
    
    def __init__(self, message_callback: Optional[Callable[[CANMessage], None]] = None, logger=None, disconnect_callback: Optional[Callable] = None):
        self.buses: Dict[str, CANBusInstance] = {}
        self.message_callback = message_callback
        self.disconnect_callback = disconnect_callback  # Callback when device disconnects
        self.logger = logger
        self._lock = threading.Lock()
        
        # Gateway configuration
        self.gateway_config: Optional[GatewayConfig] = None
        self.gateway_thread: Optional[threading.Thread] = None
        self.gateway_running = False
        
        # Statistics
        self.gateway_stats = {
            'forwarded': 0,
            'blocked': 0,
            'modified': 0,
            'loops_prevented': 0
        }
        
        # Statistics per route (for bidirectional tracking)
        self.route_stats: Dict[str, int] = {}  # key: "source->destination", value: count
    
    def add_bus(self, config: CANBusConfig) -> bool:
        """Add a CAN bus to the manager"""
        with self._lock:
            if config.name in self.buses:
                print(f"Bus '{config.name}' already exists")
                return False
            
            bus_instance = CANBusInstance(config, self._on_message_received, self._on_device_disconnected)
            self.buses[config.name] = bus_instance
            print(f"Bus '{config.name}' added")
            return True
    
    def remove_bus(self, name: str) -> bool:
        """Remove a CAN bus from the manager"""
        with self._lock:
            if name not in self.buses:
                return False
            
            bus = self.buses[name]
            if bus.connected:
                bus.disconnect()
            
            del self.buses[name]
            print(f"Bus '{name}' removed")
            return True
    
    def connect_all(self, simulation: bool = False) -> Dict[str, bool]:
        """Connect all buses. Returns dict of {bus_name: success}"""
        results = {}
        for name, bus in self.buses.items():
            if simulation:
                # Force simulation mode
                bus.connect()  # Will use simulation if CAN not available
                results[name] = True
            else:
                results[name] = bus.connect()
        return results
    
    def connect_bus(self, name: str) -> bool:
        """Connect a specific bus"""
        if name in self.buses:
            return self.buses[name].connect()
        return False
    
    def disconnect_all(self):
        """Disconnect all buses"""
        for bus in self.buses.values():
            bus.disconnect()
    
    def disconnect_bus(self, name: str) -> bool:
        """Disconnect a specific bus"""
        if name in self.buses:
            self.buses[name].disconnect()
            return True
        return False
    
    def send_to(self, bus_name: str, msg) -> bool:
        """Send message to a specific bus (accepts CANMessage or can.Message)"""
        if bus_name in self.buses:
            return self.buses[bus_name].send(msg)
        return False
    
    def send_to_all(self, msg) -> Dict[str, bool]:
        """Send message to all connected buses (accepts CANMessage or can.Message)
        Returns dict of {bus_name: success}"""
        results = {}
        for name, bus in self.buses.items():
            if bus.connected:
                results[name] = bus.send(msg)
        return results
    
    def get_bus_names(self) -> List[str]:
        """Get list of all bus names"""
        return list(self.buses.keys())
    
    def get_connected_buses(self) -> List[str]:
        """Get list of connected bus names"""
        return [name for name, bus in self.buses.items() if bus.connected]
    
    def is_bus_connected(self, name: str) -> bool:
        """Check if a specific bus is connected"""
        return name in self.buses and self.buses[name].connected
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all buses
        
        Returns:
            Dictionary mapping bus name to connection status
        """
        return {name: bus.connected for name, bus in self.buses.items()}
    
    def set_message_callback(self, callback: Callable[[str, CANMessage], None]):
        """Set callback for received messages. Signature: callback(bus_name, message)"""
        self.message_callback = callback
    
    def _on_message_received(self, bus_name: str, msg: CANMessage):
        """Internal callback that forwards to user callback and handles gateway"""
        # Process gateway if enabled (but don't block display)
        if self.gateway_config and self.gateway_config.enabled:
            self._process_gateway_message(msg)
        
        # ALWAYS forward to user callback (UI display)
        # The UI should show everything the interface receives
        if self.message_callback:
            # Forward with bus_name and message
            self.message_callback(bus_name, msg)
    
    def _on_device_disconnected(self, bus_name: str, error_msg: str):
        """Internal callback when a device is physically disconnected"""
        print(f"[CANBusManager] Device disconnected: {bus_name} - {error_msg}")
        
        # Mark bus as disconnected
        if bus_name in self.buses:
            self.buses[bus_name].connected = False
        
        # Notify parent callback if available
        if self.disconnect_callback:
            self.disconnect_callback(bus_name, error_msg)
    
    def get_bus_info(self, name: str) -> Optional[Dict]:
        """Get information about a bus"""
        if name not in self.buses:
            return None
        
        bus = self.buses[name]
        return {
            'name': bus.config.name,
            'channel': bus.config.channel,
            'baudrate': bus.config.baudrate,
            'listen_only': bus.config.listen_only,
            'interface': bus.config.interface,
            'connected': bus.connected
        }
    
    def __len__(self) -> int:
        """Return number of buses"""
        return len(self.buses)
    
    def __contains__(self, name: str) -> bool:
        """Check if bus exists"""
        return name in self.buses
    
    # ========== Gateway Methods ==========
    
    def set_gateway_config(self, config: GatewayConfig):
        """Set gateway configuration"""
        self.gateway_config = config
        
        # Start dynamic blocking thread if needed
        if config.enabled and any(db.enabled for db in config.dynamic_blocks):
            self._start_dynamic_blocking()
    
    def get_gateway_config(self) -> Optional[GatewayConfig]:
        """Get current gateway configuration"""
        return self.gateway_config
    
    def enable_gateway(self, enabled: bool = True):
        """Enable or disable gateway"""
        if self.gateway_config:
            self.gateway_config.enabled = enabled
            if enabled and any(db.enabled for db in self.gateway_config.dynamic_blocks):
                self._start_dynamic_blocking()
            elif not enabled:
                self._stop_dynamic_blocking()
    
    def get_gateway_stats(self) -> Dict[str, int]:
        """Get gateway statistics"""
        return self.gateway_stats.copy()
    
    def reset_gateway_stats(self):
        """Reset gateway statistics"""
        self.gateway_stats = {
            'forwarded': 0,
            'blocked': 0,
            'modified': 0,
            'loops_prevented': 0
        }
        self.route_stats.clear()
    
    def _process_gateway_message(self, msg: CANMessage):
        """Process message through gateway rules with loop prevention"""
        if not self.gateway_config or not self.gateway_config.enabled:
            return
        
        # Loop prevention: check if message already processed by gateway
        if self.gateway_config.loop_prevention_enabled and msg.gateway_processed:
            self.gateway_stats['loops_prevented'] += 1
            msg.gateway_action = "loop_prevented"
            if self.logger:
                self.logger.debug(f"Loop prevented: ID 0x{msg.can_id:03X} from {msg.source} (already processed)")
            return
        
        # Find all active routes from this source
        active_routes = [r for r in self.gateway_config.routes if r.enabled and r.source == msg.source]
        
        # Fallback to old method for backward compatibility
        if not active_routes:
            bus_names = self.get_bus_names()
            if len(bus_names) >= 2:
                bus1, bus2 = bus_names[0], bus_names[1]
                if msg.source == bus1 and self.gateway_config.transmit_1_to_2:
                    active_routes.append(GatewayRoute(source=bus1, destination=bus2, enabled=True))
                elif msg.source == bus2 and self.gateway_config.transmit_2_to_1:
                    active_routes.append(GatewayRoute(source=bus2, destination=bus1, enabled=True))
        
        # Track if message was blocked or forwarded
        was_blocked = False
        was_forwarded = False
        was_modified = False
        
        # Process each active route
        for route in active_routes:
            target_bus = route.destination
            
            # Check if message should be blocked for this specific route
            if self.gateway_config.should_block(msg, target_bus):
                self.gateway_stats['blocked'] += 1
                was_blocked = True
                if self.logger:
                    self.logger.debug(f"Blocked: ID 0x{msg.can_id:03X} from {msg.source} to {target_bus}")
                continue
            
            # Check if message should be modified for this specific route
            modify_rule = self.gateway_config.get_modify_rule(msg, target_bus)
            forwarded_msg = msg
            if modify_rule:
                forwarded_msg = modify_rule.apply(msg)
                self.gateway_stats['modified'] += 1
                was_modified = True
                if self.logger:
                    self.logger.debug(f"Modified: ID 0x{msg.can_id:03X} from {msg.source} to {target_bus}")
            
            # Mark message as processed to prevent loops
            if self.gateway_config.loop_prevention_enabled:
                # Create a copy with gateway_processed flag set
                forwarded_msg = CANMessage(
                    timestamp=forwarded_msg.timestamp,
                    can_id=forwarded_msg.can_id,
                    dlc=forwarded_msg.dlc,
                    data=forwarded_msg.data,
                    comment=forwarded_msg.comment,
                    period=forwarded_msg.period,
                    count=forwarded_msg.count,
                    channel=forwarded_msg.channel,
                    is_extended=forwarded_msg.is_extended,
                    is_rtr=forwarded_msg.is_rtr,
                    source=forwarded_msg.source,
                    gateway_processed=True  # Mark as processed
                )
            
            # Send to target bus
            if target_bus and target_bus in self.buses:
                if self.send_to(target_bus, forwarded_msg):
                    self.gateway_stats['forwarded'] += 1
                    was_forwarded = True
                    
                    # Update per-route statistics
                    route_key = f"{msg.source}->{target_bus}"
                    self.route_stats[route_key] = self.route_stats.get(route_key, 0) + 1
                    
                    if self.logger:
                        self.logger.debug(f"Forwarded: ID 0x{msg.can_id:03X} from {msg.source} to {target_bus}")
        
        # Mark the original message with gateway action for UI display
        if was_blocked and not was_forwarded:
            msg.gateway_action = "blocked"
        elif was_modified:
            msg.gateway_action = "modified"
        elif was_forwarded:
            msg.gateway_action = "forwarded"
    
    def _start_dynamic_blocking(self):
        """Start thread for dynamic blocking"""
        if self.gateway_running:
            return
        
        self.gateway_running = True
        self.gateway_thread = threading.Thread(
            target=self._dynamic_blocking_loop,
            daemon=True,
            name="GatewayDynamicBlock"
        )
        self.gateway_thread.start()
    
    def _stop_dynamic_blocking(self):
        """Stop dynamic blocking thread"""
        self.gateway_running = False
        if self.gateway_thread and self.gateway_thread.is_alive():
            self.gateway_thread.join(timeout=1.0)
    
    def _dynamic_blocking_loop(self):
        """Thread loop for dynamic blocking"""
        while self.gateway_running:
            if not self.gateway_config:
                time.sleep(0.1)
                continue
            
            # Advance all enabled dynamic blocks
            for dyn_block in self.gateway_config.dynamic_blocks:
                if dyn_block.enabled:
                    dyn_block.advance()
            
            # Sleep for the period (use minimum period from all blocks)
            if self.gateway_config.dynamic_blocks:
                min_period = min(
                    (db.period for db in self.gateway_config.dynamic_blocks if db.enabled),
                    default=1000
                )
                time.sleep(min_period / 1000.0)
            else:
                time.sleep(1.0)
