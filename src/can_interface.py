"""
CAN Interface - Gerenciamento de comunicação CAN
"""

import threading
import queue
import time
from typing import Optional, Callable
from .models import CANMessage, CANConfig

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False
    print("python-can not installed. Simulation mode activated.")


class CANInterface:
    """Manages communication with the CAN bus"""
    
    def __init__(self, config: CANConfig):
        self.config = config
        self.bus: Optional[can.BusABC] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False
        self.message_callback: Optional[Callable[[CANMessage], None]] = None
        
    def connect(self) -> bool:
        """Connect to CAN bus"""
        try:
            if CAN_AVAILABLE:
                # Aqui será implementada a conexão real
                # self.bus = can.interface.Bus(
                #     channel=self.config.channel,
                #     bustype=self.config.interface,
                #     bitrate=self.config.baudrate
                # )
                pass
            
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            return True
            
        except Exception as e:
            print(f"Error while connecting: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from CAN bus"""
        self.running = False
        
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
        
        if self.bus:
            self.bus.shutdown()
            self.bus = None
    
    def send_message(self, msg: CANMessage) -> bool:
        """Send a CAN message"""
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
                # Modo simulação
                print(f"[SIM] Enviando: ID=0x{msg.can_id:03X}, Data={msg.to_hex_string()}")
                return True
        except Exception as e:
            print(f"Error while sending message: {e}")
            return False
    
    def set_message_callback(self, callback: Callable[[CANMessage], None]):
        """Set callback for received messages"""
        self.message_callback = callback
    
    def _receive_loop(self):
        """Message receive loop"""
        while self.running:
            try:
                if self.bus:
                    message = self.bus.recv(timeout=0.1)
                    if message and self.message_callback:
                        can_msg = CANMessage(
                            timestamp=message.timestamp,
                            can_id=message.arbitration_id,
                            dlc=message.dlc,
                            data=message.data,
                            is_extended=message.is_extended_id,
                            is_rtr=message.is_remote_frame
                        )
                        self.message_callback(can_msg)
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Receive error: {e}")
                time.sleep(0.1)
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.running


class SimulatedCANInterface(CANInterface):
    """Interface CAN simulada para testes"""
    
    def __init__(self, config: CANConfig):
        super().__init__(config)
        self.sample_messages = [
            (0x280, 8, bytes([0xBB, 0x8E, 0x00, 0x00, 0x29, 0xFA, 0x29, 0x29])),
            (0x284, 6, bytes([0x06, 0x06, 0x00, 0x00, 0x00, 0x00])),
            (0x480, 8, bytes([0x54, 0x80, 0x00, 0x00, 0x19, 0x41, 0x00, 0x20])),
            (0x680, 8, bytes([0x81, 0x00, 0x00, 0x7F, 0x00, 0xF0, 0x47, 0x01])),
        ]
        self.message_index = 0
    
    def _receive_loop(self):
        """Simulated receive loop"""
        while self.running:
            if self.message_callback:
                # Gerar mensagem simulada
                can_id, dlc, data = self.sample_messages[self.message_index]
                self.message_index = (self.message_index + 1) % len(self.sample_messages)
                
                msg = CANMessage(
                    timestamp=time.time(),
                    can_id=can_id,
                    dlc=dlc,
                    data=data
                )
                self.message_callback(msg)
            
            time.sleep(0.1)
