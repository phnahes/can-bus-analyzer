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

from .models import CANMessage


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
    
    def send(self, msg: CANMessage) -> bool:
        """Send a CAN message"""
        if not self.connected:
            return False
        
        try:
            if self.bus:
                can_msg = can.Message(
                    arbitration_id=msg.can_id,
                    data=msg.data[:msg.dlc],
                    is_extended_id=msg.is_extended,
                    is_remote_frame=msg.is_rtr
                )
                self.bus.send(can_msg)
                return True
            else:
                # Simulation mode
                print(f"[{self.config.name}] SIM TX: ID=0x{msg.can_id:03X}, Data={msg.to_hex_string()}")
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
    """Manages multiple CAN bus instances"""
    
    def __init__(self):
        self.buses: Dict[str, CANBusInstance] = {}
        self.message_callback: Optional[Callable[[str, CANMessage], None]] = None
        self._lock = threading.Lock()
    
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
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect all buses. Returns dict of {bus_name: success}"""
        results = {}
        for name, bus in self.buses.items():
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
    
    def send_to(self, bus_name: str, msg: CANMessage) -> bool:
        """Send message to a specific bus"""
        if bus_name in self.buses:
            return self.buses[bus_name].send(msg)
        return False
    
    def send_to_all(self, msg: CANMessage) -> Dict[str, bool]:
        """Send message to all connected buses. Returns dict of {bus_name: success}"""
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
        """Internal callback that forwards to user callback"""
        if self.message_callback:
            self.message_callback(bus_name, msg)
    
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
