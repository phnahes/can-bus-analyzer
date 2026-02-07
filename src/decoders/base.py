"""
Protocol Decoder System - Modular system for CAN protocol decoding
Allows enabling/disabling specific decoders (FTCAN, OBD-II, J1939, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class DecoderPriority(Enum):
    """Decoder execution priority"""
    HIGHEST = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    LOWEST = 4


@dataclass
class DecodedData:
    """Decoded data from a protocol decoder"""
    protocol: str  # Protocol name (e.g. "FTCAN", "OBD-II")
    success: bool  # Whether decoding succeeded
    confidence: float  # Decoding confidence (0.0 to 1.0)
    data: Dict[str, Any]  # Decoded data
    raw_description: str  # Simple text description
    detailed_info: Optional[Dict] = None  # Optional detailed information
    
    def __str__(self) -> str:
        return f"[{self.protocol}] {self.raw_description}"


class ProtocolDecoder(ABC):
    """Base class for protocol decoders"""
    
    def __init__(self):
        self.enabled = True
        self.priority = DecoderPriority.NORMAL
    
    @abstractmethod
    def get_name(self) -> str:
        """Return decoder name"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return decoder description"""
        pass
    
    @abstractmethod
    def can_decode(self, can_id: int, data: bytes, is_extended: bool) -> bool:
        """
        Check if this decoder can decode the message
        Must be fast (used for filtering)
        """
        pass
    
    @abstractmethod
    def decode(self, can_id: int, data: bytes, is_extended: bool, timestamp: float) -> Optional[DecodedData]:
        """
        Decode CAN message
        Returns None if unable to decode
        """
        pass
    
    def get_priority(self) -> DecoderPriority:
        """Return decoder priority"""
        return self.priority
    
    def is_enabled(self) -> bool:
        """Check if decoder is enabled"""
        return self.enabled
    
    def set_enabled(self, enabled: bool):
        """Enable/disable the decoder"""
        self.enabled = enabled
    
    def get_settings(self) -> Dict[str, Any]:
        """Return decoder settings"""
        return {
            'enabled': self.enabled,
            'priority': self.priority.name
        }
    
    def set_settings(self, settings: Dict[str, Any]):
        """Apply settings to decoder"""
        if 'enabled' in settings:
            self.enabled = settings['enabled']
        if 'priority' in settings:
            try:
                self.priority = DecoderPriority[settings['priority']]
            except KeyError:
                pass


class DecoderManager:
    """Protocol decoder manager"""
    
    def __init__(self):
        self.decoders: List[ProtocolDecoder] = []
        self._decoder_stats: Dict[str, Dict] = {}
    
    def register_decoder(self, decoder: ProtocolDecoder):
        """Register a new decoder"""
        self.decoders.append(decoder)
        self._decoder_stats[decoder.get_name()] = {
            'messages_decoded': 0,
            'messages_failed': 0,
            'total_confidence': 0.0
        }
        
        # Sort by priority
        self.decoders.sort(key=lambda d: d.get_priority().value)
    
    def unregister_decoder(self, decoder_name: str):
        """Remove a decoder"""
        self.decoders = [d for d in self.decoders if d.get_name() != decoder_name]
        if decoder_name in self._decoder_stats:
            del self._decoder_stats[decoder_name]
    
    def get_decoder(self, name: str) -> Optional[ProtocolDecoder]:
        """Return decoder by name"""
        for decoder in self.decoders:
            if decoder.get_name() == name:
                return decoder
        return None
    
    def get_all_decoders(self) -> List[ProtocolDecoder]:
        """Return all registered decoders"""
        return self.decoders.copy()
    
    def decode_message(self, can_id: int, data: bytes, is_extended: bool, 
                      timestamp: float = 0.0) -> List[DecodedData]:
        """
        Try to decode message with all enabled decoders
        Returns list of decodings (may have multiple)
        """
        results = []
        
        for decoder in self.decoders:
            if not decoder.is_enabled():
                continue
            
            try:
                # Check if can decode (fast path)
                if not decoder.can_decode(can_id, data, is_extended):
                    continue
                
                # Try to decode
                decoded = decoder.decode(can_id, data, is_extended, timestamp)
                
                if decoded and decoded.success:
                    results.append(decoded)
                    
                    # Update statistics
                    stats = self._decoder_stats[decoder.get_name()]
                    stats['messages_decoded'] += 1
                    stats['total_confidence'] += decoded.confidence
                else:
                    self._decoder_stats[decoder.get_name()]['messages_failed'] += 1
                    
            except Exception:
                # Decoder failed but should not stop others
                self._decoder_stats[decoder.get_name()]['messages_failed'] += 1
                continue
        
        return results
    
    def get_stats(self) -> Dict[str, Dict]:
        """Return decoder usage statistics"""
        stats = {}
        for name, raw_stats in self._decoder_stats.items():
            decoded = raw_stats['messages_decoded']
            failed = raw_stats['messages_failed']
            total = decoded + failed
            
            avg_confidence = 0.0
            if decoded > 0:
                avg_confidence = raw_stats['total_confidence'] / decoded
            
            stats[name] = {
                'decoded': decoded,
                'failed': failed,
                'total': total,
                'success_rate': (decoded / total * 100) if total > 0 else 0.0,
                'avg_confidence': avg_confidence
            }
        
        return stats
    
    def reset_stats(self):
        """Reset statistics"""
        for stats in self._decoder_stats.values():
            stats['messages_decoded'] = 0
            stats['messages_failed'] = 0
            stats['total_confidence'] = 0.0
    
    def save_config(self) -> Dict:
        """Save configuration of all decoders"""
        config = {}
        for decoder in self.decoders:
            config[decoder.get_name()] = decoder.get_settings()
        return config
    
    def load_config(self, config: Dict):
        """Load decoder configuration"""
        for decoder in self.decoders:
            name = decoder.get_name()
            if name in config:
                decoder.set_settings(config[name])


# Singleton global
_decoder_manager: Optional[DecoderManager] = None


def get_decoder_manager() -> DecoderManager:
    """Return singleton instance of DecoderManager"""
    global _decoder_manager
    if _decoder_manager is None:
        _decoder_manager = DecoderManager()
    return _decoder_manager


def reset_decoder_manager():
    """Reset the decoder manager (useful for tests)"""
    global _decoder_manager
    _decoder_manager = None
