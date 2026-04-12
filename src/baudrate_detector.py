"""
Baudrate Detector - Detecta automaticamente o baudrate de um CAN bus
"""

import time
from typing import Optional, List, Tuple
from dataclasses import dataclass

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False


@dataclass
class BaudrateDetectionResult:
    """Baudrate detection result"""
    baudrate: Optional[int]
    confidence: float  # 0.0 - 1.0
    messages_received: int
    detection_time: float  # segundos
    tested_baudrates: List[int]


class BaudrateDetector:
    """Automatic CAN baudrate detector"""
    
    # Common baudrates in probability order
    COMMON_BAUDRATES = [
        500000,   # 500 kbps - OBD-II (mais comum)
        1000000,  # 1 Mbps - FTCAN, CAN-FD
        250000,   # 250 kbps - Industrial, alguns OBD-II
        125000,   # 125 kbps - CANopen
        100000,   # 100 kbps
        83333,    # 83.333 kbps
        50000,    # 50 kbps
    ]
    
    def __init__(self, channel: str, interface: str = 'socketcan'):
        """
        Inicializa detector
        
        Args:
            channel: Canal CAN (ex: 'can0', 'vcan0')
            interface: Interface (ex: 'socketcan', 'slcan')
        """
        self.channel = channel
        self.interface = interface
    
    def detect(
        self,
        baudrates: Optional[List[int]] = None,
        timeout_per_baudrate: float = 2.0,
        min_messages: int = 5,
        callback=None
    ) -> BaudrateDetectionResult:
        """
        Detecta baudrate automaticamente
        
        Args:
            baudrates: Lista de baudrates para testar (None = usar comuns)
            timeout_per_baudrate: Timeout para cada baudrate (segundos)
            min_messages: Número mínimo de mensagens para confirmar
            callback: Função callback(baudrate, status) para progresso
        
        Returns:
            BaudrateDetectionResult com resultado da detecção
        """
        if not CAN_AVAILABLE:
            return BaudrateDetectionResult(
                baudrate=None,
                confidence=0.0,
                messages_received=0,
                detection_time=0.0,
                tested_baudrates=[]
            )
        
        if baudrates is None:
            baudrates = self.COMMON_BAUDRATES
        
        start_time = time.time()
        tested = []
        
        for baudrate in baudrates:
            tested.append(baudrate)
            
            if callback:
                callback(baudrate, 'testing')
            
            result = self._test_baudrate(
                baudrate,
                timeout_per_baudrate,
                min_messages
            )
            
            if result['success']:
                detection_time = time.time() - start_time
                
                if callback:
                    callback(baudrate, 'found')
                
                return BaudrateDetectionResult(
                    baudrate=baudrate,
                    confidence=result['confidence'],
                    messages_received=result['messages_received'],
                    detection_time=detection_time,
                    tested_baudrates=tested
                )
            
            if callback:
                callback(baudrate, 'failed')
        
        # Nenhum baudrate funcionou
        detection_time = time.time() - start_time
        
        return BaudrateDetectionResult(
            baudrate=None,
            confidence=0.0,
            messages_received=0,
            detection_time=detection_time,
            tested_baudrates=tested
        )
    
    def _test_baudrate(
        self,
        baudrate: int,
        timeout: float,
        min_messages: int
    ) -> dict:
        """
        Testa um baudrate específico
        
        Returns:
            dict com 'success', 'confidence', 'messages_received'
        """
        bus = None
        
        try:
            # Try connecting with this baudrate
            bus = can.interface.Bus(
                channel=self.channel,
                interface=self.interface,
                bitrate=baudrate,
                receive_own_messages=False
            )
            
            # Wait for messages
            messages_received = 0
            error_frames = 0
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                msg = bus.recv(timeout=0.1)
                
                if msg is None:
                    continue
                
                # Check if this is a valid message
                if msg.is_error_frame:
                    error_frames += 1
                    continue
                
                # Valid message received
                messages_received += 1
                
                # If enough messages were received, consider success
                if messages_received >= min_messages:
                    # Calculate confidence based on error rate
                    total_frames = messages_received + error_frames
                    confidence = messages_received / total_frames if total_frames > 0 else 0.0
                    
                    return {
                        'success': True,
                        'confidence': confidence,
                        'messages_received': messages_received
                    }
            
            # Timeout - check if at least some messages were received
            if messages_received > 0:
                total_frames = messages_received + error_frames
                confidence = messages_received / total_frames if total_frames > 0 else 0.0
                
                # If some messages were received (even < min), this may be the correct baudrate
                # but with low traffic
                if confidence > 0.5:
                    return {
                        'success': True,
                        'confidence': confidence * 0.7,  # Penaliza por não atingir min_messages
                        'messages_received': messages_received
                    }
            
            return {
                'success': False,
                'confidence': 0.0,
                'messages_received': messages_received
            }
            
        except Exception as e:
            # Error connecting or receiving - incorrect baudrate
            return {
                'success': False,
                'confidence': 0.0,
                'messages_received': 0
            }
        
        finally:
            if bus:
                try:
                    bus.shutdown()
                except:
                    pass
    
    def quick_detect(self, callback=None) -> Optional[int]:
        """
        Detecção rápida - testa apenas os baudrates mais comuns
        
        Args:
            callback: Função callback(baudrate, status) para progresso
        
        Returns:
            Baudrate detectado ou None
        """
        # Test only the 3 most common
        quick_baudrates = [500000, 1000000, 250000]
        
        result = self.detect(
            baudrates=quick_baudrates,
            timeout_per_baudrate=1.5,
            min_messages=3,
            callback=callback
        )
        
        return result.baudrate


def detect_baudrate(
    channel: str,
    interface: str = 'socketcan',
    quick: bool = False,
    callback=None
) -> Optional[int]:
    """
    Função helper para detecção de baudrate
    
    Args:
        channel: Canal CAN
        interface: Interface CAN
        quick: Se True, testa apenas baudrates comuns
        callback: Callback para progresso
    
    Returns:
        Baudrate detectado ou None
    """
    detector = BaudrateDetector(channel, interface)
    
    if quick:
        return detector.quick_detect(callback)
    else:
        result = detector.detect(callback=callback)
        return result.baudrate


# Exemplo de uso
if __name__ == '__main__':
    import sys
    
    def progress_callback(baudrate, status):
        """Callback para mostrar progresso"""
        if status == 'testing':
            print(f"🔍 Testing {baudrate:7d} bps...", end='', flush=True)
        elif status == 'found':
            print(f" ✅ FOUND!")
        elif status == 'failed':
            print(f" ❌")
    
    channel = sys.argv[1] if len(sys.argv) > 1 else 'can0'
    
    print(f"🚀 Auto-detecting baudrate on {channel}...")
    print()
    
    detector = BaudrateDetector(channel)
    result = detector.detect(callback=progress_callback)
    
    print()
    print("=" * 50)
    
    if result.baudrate:
        print(f"✅ Baudrate detected: {result.baudrate} bps")
        print(f"   Confidence: {result.confidence * 100:.1f}%")
        print(f"   Messages received: {result.messages_received}")
        print(f"   Detection time: {result.detection_time:.2f}s")
    else:
        print("❌ No baudrate detected")
        print(f"   Tested: {', '.join(str(b) for b in result.tested_baudrates)}")
        print(f"   Detection time: {result.detection_time:.2f}s")
    
    print("=" * 50)
