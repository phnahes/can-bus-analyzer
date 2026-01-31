"""
USB Device Monitor - Cross-platform detection of USB/Serial devices
Supports: macOS, Windows, Linux
"""

import os
import sys
import glob
import threading
import time
from typing import List, Dict, Optional, Callable
from .logger import get_logger


def _is_serial_port_path(path: str) -> bool:
    """Check if path looks like a serial port (exclude pseudo-terminals)."""
    if sys.platform == "win32":
        return path.upper().startswith("COM") and path[3:].strip().isdigit()
    # Unix: exclude virtual consoles, ptys, etc.
    name = os.path.basename(path)
    if name.startswith("ttyS") or name.startswith("ttyAMA") or name.startswith("ttyO"):
        return True  # Linux hardware serial
    if "usb" in name or "usbserial" in name or "usbmodem" in name:
        return True
    if "SLAB" in name or "wchusbserial" in name:
        return True
    if name.startswith("ttyACM") or name.startswith("ttyUSB"):
        return True  # Linux USB serial
    return False


class USBDeviceInfo:
    """Information about a USB/Serial device"""
    
    def __init__(self, path: str, name: str = None, description: str = None):
        self.path = path
        self.name = name or os.path.basename(path)
        self._description_override = description
        if description is None:
            self.description = self._get_description()
        else:
            self.description = description
        
    def _get_description(self) -> str:
        """Get device description from name"""
        name_lower = self.name.lower()
        
        if 'usb' in name_lower:
            if 'serial' in name_lower:
                return "USB Serial Adapter"
            elif 'modem' in name_lower:
                return "USB Modem"
            else:
                return "USB Device"
        elif 'bluetooth' in name_lower:
            return "Bluetooth Device"
        elif 'cu.' in self.name:
            return "Call-Out Device (macOS)"
        elif 'tty.' in self.name:
            return "Terminal Device"
        elif sys.platform == "win32" and self.name.upper().startswith("COM"):
            return "Serial Port (Windows)"
        else:
            return "Serial Device"
    
    def __str__(self):
        return f"{self.name} ({self.description})"
    
    def __repr__(self):
        return f"USBDeviceInfo(path='{self.path}', name='{self.name}')"


class USBDeviceMonitor:
    """Monitor for connected USB/Serial devices (cross-platform)"""
    
    def __init__(self, poll_interval: float = 2.0):
        """
        Initialize device monitor.
        
        Args:
            poll_interval: Polling interval in seconds
        """
        self.logger = get_logger()
        self.poll_interval = poll_interval
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        self.known_devices: Dict[str, USBDeviceInfo] = {}
        
        self.on_device_connected: Optional[Callable[[USBDeviceInfo], None]] = None
        self.on_device_disconnected: Optional[Callable[[USBDeviceInfo], None]] = None
        
    def get_available_devices(self) -> List[USBDeviceInfo]:
        """
        Return list of available USB/Serial devices.
        Uses pyserial's list_ports on all platforms when available.
        Falls back to glob patterns on macOS/Linux.
        """
        devices: List[USBDeviceInfo] = []
        
        # Prefer pyserial list_ports (cross-platform)
        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                path = port.device
                if not _is_serial_port_path(path) and sys.platform != "win32":
                    continue
                desc = port.description or None
                dev = USBDeviceInfo(path, name=os.path.basename(path), description=desc)
                devices.append(dev)
                self.logger.debug(f"Found device (list_ports): {dev}")
        except Exception as e:
            self.logger.debug(f"list_ports not available: {e}")
        
        # Fallback: glob patterns (macOS / Linux)
        if not devices and sys.platform != "win32":
            patterns = [
                '/dev/tty.usb*',
                '/dev/cu.usb*',
                '/dev/tty.usbserial*',
                '/dev/cu.usbserial*',
                '/dev/tty.usbmodem*',
                '/dev/cu.usbmodem*',
                '/dev/tty.SLAB*',
                '/dev/cu.SLAB*',
                '/dev/tty.wchusbserial*',
                '/dev/cu.wchusbserial*',
                '/dev/ttyUSB*',   # Linux
                '/dev/ttyACM*',   # Linux (Arduino, etc.)
            ]
            for pattern in patterns:
                for path in glob.glob(pattern):
                    try:
                        if os.path.exists(path) and _is_serial_port_path(path):
                            device = USBDeviceInfo(path)
                            devices.append(device)
                            self.logger.debug(f"Found device (glob): {device}")
                    except Exception as e:
                        self.logger.error(f"Error checking device {path}: {e}")
        
        # Deduplicate: on macOS prefer cu.* over tty.* for the same device
        unique_devices: Dict[str, USBDeviceInfo] = {}
        for device in devices:
            base = device.name.replace('tty.', '').replace('cu.', '')
            if sys.platform == "darwin":
                if base not in unique_devices or device.name.startswith('cu.'):
                    unique_devices[base] = device
            else:
                unique_devices[device.path] = device
        
        return list(unique_devices.values())
    
    def start_monitoring(self):
        """Inicia o monitoramento de dispositivos"""
        if self.running:
            self.logger.warning("Device monitor already running")
            return
        
        self.logger.info("Starting USB device monitor")
        self.running = True
        
        # Obter dispositivos iniciais
        initial_devices = self.get_available_devices()
        for device in initial_devices:
            self.known_devices[device.path] = device
        
        # Iniciar thread de monitoramento
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Para o monitoramento de dispositivos"""
        if not self.running:
            return
        
        self.logger.info("Stopping USB device monitor")
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
            self.monitor_thread = None
    
    def _monitor_loop(self):
        """Loop de monitoramento de dispositivos"""
        while self.running:
            try:
                # Obter dispositivos atuais
                current_devices = self.get_available_devices()
                current_paths = {device.path for device in current_devices}
                known_paths = set(self.known_devices.keys())
                
                # Detectar novos dispositivos
                new_paths = current_paths - known_paths
                for path in new_paths:
                    device = next((d for d in current_devices if d.path == path), None)
                    if device:
                        self.logger.info(f"Device connected: {device}")
                        self.known_devices[path] = device
                        
                        # Chamar callback
                        if self.on_device_connected:
                            try:
                                self.on_device_connected(device)
                            except Exception as e:
                                self.logger.error(f"Error in device connected callback: {e}")
                
                # Detectar dispositivos removidos
                removed_paths = known_paths - current_paths
                for path in removed_paths:
                    device = self.known_devices.pop(path, None)
                    if device:
                        self.logger.info(f"Device disconnected: {device}")
                        
                        # Chamar callback
                        if self.on_device_disconnected:
                            try:
                                self.on_device_disconnected(device)
                            except Exception as e:
                                self.logger.error(f"Error in device disconnected callback: {e}")
                
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
            
            # Aguardar antes da próxima verificação
            time.sleep(self.poll_interval)
    
    def is_device_available(self, device_path: str) -> bool:
        """
        Verifica se um dispositivo específico está disponível
        
        Args:
            device_path: Caminho do dispositivo
            
        Returns:
            True se o dispositivo está disponível
        """
        return os.path.exists(device_path) and os.access(device_path, os.R_OK | os.W_OK)
    
    def get_device_info(self, device_path: str) -> Optional[USBDeviceInfo]:
        """
        Obtém informações sobre um dispositivo específico
        
        Args:
            device_path: Caminho do dispositivo
            
        Returns:
            USBDeviceInfo ou None se não encontrado
        """
        if device_path in self.known_devices:
            return self.known_devices[device_path]
        
        # Tentar criar info para dispositivo desconhecido
        if os.path.exists(device_path):
            return USBDeviceInfo(device_path)
        
        return None


# Instância global
_usb_monitor: Optional[USBDeviceMonitor] = None


def get_usb_monitor() -> USBDeviceMonitor:
    """Obtém a instância global do monitor USB"""
    global _usb_monitor
    if _usb_monitor is None:
        _usb_monitor = USBDeviceMonitor()
    return _usb_monitor


def init_usb_monitor(poll_interval: float = 2.0) -> USBDeviceMonitor:
    """
    Inicializa o monitor USB global
    
    Args:
        poll_interval: Intervalo de verificação em segundos
        
    Returns:
        Instância do USBDeviceMonitor
    """
    global _usb_monitor
    _usb_monitor = USBDeviceMonitor(poll_interval)
    return _usb_monitor
