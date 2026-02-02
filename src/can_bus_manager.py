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

from .models import CANMessage, GatewayConfig


@dataclass
class CANBusConfig:
    """Configuration for a single CAN bus"""
    name: str
    channel: str
    baudrate: int
    listen_only: bool = True
    interface: str = 'socketcan'  # socketcan, slcan, etc.
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.name:
            raise ValueError("Bus name cannot be empty")
        if self.baudrate <= 0:
            raise ValueError("Baudrate must be positive")


class CANBusInstance:
    """Represents a single CAN bus interface"""
    
    def __init__(self, config: CANBusConfig, message_callback: Optional[Callable] = None):
        self.config = config
        self.bus: Optional[can.BusABC] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.connected = False
        self.message_callback = message_callback
        self._lock = threading.Lock()
    
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
            if self.config.channel.startswith('/dev/tty') or self.config.channel.startswith('COM'):
                interface = 'slcan'
            elif self.config.channel in ['can0', 'can1', 'vcan0', 'vcan1']:
                interface = 'socketcan'
            
            # Create CAN bus
            self.bus = can.interface.Bus(
                channel=self.config.channel,
                interface=interface,
                bitrate=self.config.baudrate,
                receive_own_messages=False
            )
            
            self.connected = True
            self.running = True
            self.thread = threading.Thread(
                target=self._receive_loop,
                daemon=True,
                name=f"CANRx-{self.config.name}"
            )
            self.thread.start()
            
            print(f"[{self.config.name}] Connected: {self.config.channel} @ {self.config.baudrate} bps")
            return True
            
        except Exception as e:
            print(f"[{self.config.name}] Connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the CAN bus"""
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
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
                            source=self.config.name  # Mark source bus
                        )
                        self.message_callback(self.config.name, can_msg)
                else:
                    time.sleep(0.1)
            except Exception as e:
                if self.running:  # Only log if not shutting down
                    print(f"[{self.config.name}] Receive error: {e}")
                time.sleep(0.1)
    
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
                    source=self.config.name
                )
                self.message_callback(self.config.name, msg)
            
            time.sleep(0.5)  # Slower for simulation


class CANBusManager:
    """Manages multiple CAN bus instances with Gateway support"""
    
    def __init__(self, message_callback: Optional[Callable[[CANMessage], None]] = None, logger=None):
        self.buses: Dict[str, CANBusInstance] = {}
        self.message_callback = message_callback
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
            'modified': 0
        }
    
    def add_bus(self, config: CANBusConfig) -> bool:
        """Add a CAN bus to the manager"""
        with self._lock:
            if config.name in self.buses:
                print(f"Bus '{config.name}' already exists")
                return False
            
            bus_instance = CANBusInstance(config, self._on_message_received)
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
    
    def set_message_callback(self, callback: Callable[[str, CANMessage], None]):
        """Set callback for received messages. Signature: callback(bus_name, message)"""
        self.message_callback = callback
    
    def _on_message_received(self, bus_name: str, msg: CANMessage):
        """Internal callback that forwards to user callback and handles gateway"""
        # Process gateway if enabled
        if self.gateway_config and self.gateway_config.enabled:
            self._process_gateway_message(msg)
        
        # Forward to user callback
        if self.message_callback:
            # Message already has source field set, just forward it
            self.message_callback(msg)
    
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
            'modified': 0
        }
    
    def _process_gateway_message(self, msg: CANMessage):
        """Process message through gateway rules"""
        if not self.gateway_config or not self.gateway_config.enabled:
            return
        
        # Check if message should be blocked
        if self.gateway_config.should_block(msg):
            self.gateway_stats['blocked'] += 1
            return
        
        # Check if message should be modified
        modify_rule = self.gateway_config.get_modify_rule(msg)
        if modify_rule:
            msg = modify_rule.apply(msg)
            self.gateway_stats['modified'] += 1
        
        # Determine target bus based on routes (new method)
        target_bus = self.gateway_config.get_destination_for_source(msg.source)
        
        # Fallback to old method for backward compatibility
        if not target_bus:
            bus_names = self.get_bus_names()
            if len(bus_names) >= 2:
                bus1, bus2 = bus_names[0], bus_names[1]
                if msg.source == bus1 and self.gateway_config.transmit_1_to_2:
                    target_bus = bus2
                elif msg.source == bus2 and self.gateway_config.transmit_2_to_1:
                    target_bus = bus1
        
        # Send to target bus if determined
        if target_bus and target_bus in self.buses:
            if self.send_to(target_bus, msg):
                self.gateway_stats['forwarded'] += 1
    
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
