#!/usr/bin/env python3
"""
OBD-II Poller - Ferramenta para coletar dados OBD-II automaticamente
Envia requests periódicos e exibe respostas decodificadas
"""

import can
import time
import sys
from typing import List, Dict


# PIDs comuns para monitoramento
DEFAULT_PIDS = [
    0x0C,  # Engine RPM
    0x0D,  # Vehicle speed
    0x05,  # Engine coolant temperature
    0x11,  # Throttle position
    0x04,  # Engine load
    0x0F,  # Intake air temperature
    0x2F,  # Fuel level
    0x42,  # Control module voltage
]


class OBD2Poller:
    """Automatic OBD-II poller"""
    
    def __init__(self, channel='can0', interface='socketcan', bitrate=500000):
        self.channel = channel
        self.interface = interface
        self.bitrate = bitrate
        self.bus = None
        self.running = False
        
        # IDs OBD-II
        self.request_id = 0x7DF  # Functional broadcast
        self.response_ids = range(0x7E8, 0x7F0)  # 0x7E8 - 0x7EF
    
    def connect(self):
        """Conecta ao barramento CAN"""
        try:
            self.bus = can.interface.Bus(
                channel=self.channel,
                bustype=self.interface,
                bitrate=self.bitrate
            )
            print(f"✅ Conectado: {self.channel} @ {self.bitrate} bps")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do barramento"""
        if self.bus:
            self.bus.shutdown()
            self.bus = None
    
    def send_request(self, service: int, pid: int) -> bool:
        """Envia request OBD-II"""
        try:
            # Formato: [length, service, pid, padding...]
            data = bytes([0x02, service, pid, 0x00, 0x00, 0x00, 0x00, 0x00])
            
            msg = can.Message(
                arbitration_id=self.request_id,
                data=data,
                is_extended_id=False
            )
            
            self.bus.send(msg)
            return True
            
        except Exception as e:
            print(f"❌ Erro ao enviar: {e}")
            return False
    
    def wait_response(self, timeout=1.0) -> List[can.Message]:
        """Aguarda respostas OBD-II"""
        responses = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                msg = self.bus.recv(timeout=0.1)
                
                if msg and msg.arbitration_id in self.response_ids:
                    responses.append(msg)
                    
            except Exception:
                break
        
        return responses
    
    def decode_response(self, msg: can.Message) -> Dict:
        """Decodifica resposta OBD-II"""
        if len(msg.data) < 3:
            return None
        
        length = msg.data[0]
        service = msg.data[1]
        
        # Check if response (service + 0x40)
        if service < 0x40:
            return None
        
        actual_service = service - 0x40
        pid = msg.data[2]
        value_data = msg.data[3:3+length-2]
        
        return {
            'ecu_id': msg.arbitration_id,
            'service': actual_service,
            'pid': pid,
            'data': value_data,
            'raw': msg.data.hex().upper()
        }
    
    def poll_pids(self, pids: List[int], interval: float = 0.5, count: int = 0):
        """
        Faz polling de PIDs continuamente
        
        Args:
            pids: Lista de PIDs para monitorar
            interval: Intervalo entre requests (segundos)
            count: Número de iterações (0 = infinito)
        """
        print()
        print("=" * 60)
        print("OBD-II Polling Started")
        print("=" * 60)
        print(f"PIDs: {[f'0x{p:02X}' for p in pids]}")
        print(f"Interval: {interval}s")
        print(f"Press Ctrl+C to stop")
        print("=" * 60)
        print()
        
        self.running = True
        iteration = 0
        
        try:
            while self.running and (count == 0 or iteration < count):
                iteration += 1
                print(f"\n[Iteration {iteration}] {time.strftime('%H:%M:%S')}")
                print("-" * 60)
                
                for pid in pids:
                    # Envia request
                    if not self.send_request(0x01, pid):
                        continue
                    
                    # Aguarda resposta
                    responses = self.wait_response(timeout=0.5)
                    
                    if responses:
                        for resp in responses:
                            decoded = self.decode_response(resp)
                            if decoded and decoded['pid'] == pid:
                                # Decodifica valor
                                value_str = self._format_value(pid, decoded['data'])
                                ecu = f"ECU 0x{decoded['ecu_id']:03X}"
                                
                                print(f"  PID 0x{pid:02X}: {value_str} [{ecu}]")
                    else:
                        print(f"  PID 0x{pid:02X}: No response")
                    
                    # Pequeno delay entre PIDs
                    time.sleep(0.05)
                
                # Aguarda intervalo
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n⏹ Polling stopped by user")
        
        print("\n" + "=" * 60)
        print(f"Total iterations: {iteration}")
        print("=" * 60)
    
    def _format_value(self, pid: int, data: bytes) -> str:
        """Formata valor decodificado"""
        if len(data) == 0:
            return "No data"
        
        try:
            # Temperatura (offset -40)
            if pid in [0x05, 0x0F, 0x46, 0x5C]:
                return f"{data[0] - 40}°C"
            
            # RPM
            elif pid == 0x0C:
                if len(data) >= 2:
                    rpm = ((data[0] << 8) | data[1]) / 4
                    return f"{rpm:.0f} RPM"
            
            # Velocidade
            elif pid == 0x0D:
                return f"{data[0]} km/h"
            
            # Porcentagem (0-100%)
            elif pid in [0x04, 0x11, 0x2F, 0x45, 0x47, 0x49, 0x4A, 0x4B, 0x4C, 0x52, 0x5B]:
                value = data[0] * 100 / 255
                return f"{value:.1f}%"
            
            # Voltagem
            elif pid == 0x42:
                if len(data) >= 2:
                    voltage = ((data[0] << 8) | data[1]) / 1000
                    return f"{voltage:.2f}V"
            
            # MAF
            elif pid == 0x10:
                if len(data) >= 2:
                    maf = ((data[0] << 8) | data[1]) / 100
                    return f"{maf:.2f} g/s"
            
            # Lambda
            elif pid in [0x24, 0x25, 0x26, 0x27]:
                if len(data) >= 4:
                    lambda_val = ((data[0] << 8) | data[1]) * 2 / 65536
                    voltage = ((data[2] << 8) | data[3]) * 8 / 65536
                    return f"λ:{lambda_val:.3f}, {voltage:.2f}V"
            
            elif pid == 0x44:
                if len(data) >= 2:
                    lambda_val = ((data[0] << 8) | data[1]) * 2 / 65536
                    return f"λ:{lambda_val:.3f}"
            
            # Fuel trim
            elif pid in [0x06, 0x07, 0x08, 0x09]:
                value = data[0] * 100 / 128 - 100
                return f"{value:.1f}%"
            
            # Timing advance
            elif pid == 0x0E:
                value = data[0] / 2 - 64
                return f"{value:.1f}° before TDC"
            
            # Fuel type
            elif pid == 0x51:
                fuel_types = {
                    0: "N/A", 1: "Gasoline", 2: "Methanol", 3: "Ethanol",
                    4: "Diesel", 5: "LPG", 6: "CNG", 7: "Propane", 8: "Electric",
                    17: "Hybrid Gas", 19: "Hybrid Diesel"
                }
                return fuel_types.get(data[0], f"Unknown ({data[0]})")
            
            # Uint16
            elif pid in [0x1F, 0x21, 0x31, 0x4D, 0x4E, 0x63]:
                if len(data) >= 2:
                    value = (data[0] << 8) | data[1]
                    pid_info = OBD2_PIDS.get(pid, {})
                    unit = pid_info.get('unit', '')
                    return f"{value} {unit}"
            
            # Torque
            elif pid in [0x61, 0x62]:
                value = data[0] - 125
                return f"{value}%"
            
            # Generic
            else:
                return f"Raw: {data.hex().upper()}"
        
        except Exception as e:
            return f"Decode error: {e}"


def main():
    """Menu principal"""
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║              OBD-II Automatic Poller                      ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print("⚠️  IMPORTANTE: Conecte-se a um veículo com OBD-II!")
    print()
    
    # Configuration
    print("Configuração:")
    channel = input("  CAN Channel [can0]: ").strip() or "can0"
    interface = input("  Interface [socketcan]: ").strip() or "socketcan"
    bitrate_str = input("  Bitrate [500000]: ").strip() or "500000"
    bitrate = int(bitrate_str)
    
    print()
    print("PIDs para monitorar:")
    print("  1. Basic (RPM, Speed, Temp, TPS)")
    print("  2. Extended (+ Load, MAF, Fuel, Voltage)")
    print("  3. Lambda/O2 Sensors")
    print("  4. Custom (digite os PIDs)")
    print()
    
    choice = input("Escolha [1]: ").strip() or "1"
    
    if choice == '1':
        pids = [0x0C, 0x0D, 0x05, 0x11]
    elif choice == '2':
        pids = [0x0C, 0x0D, 0x05, 0x11, 0x04, 0x10, 0x2F, 0x42]
    elif choice == '3':
        pids = [0x24, 0x25, 0x44]
    elif choice == '4':
        pids_str = input("  PIDs (hex, separados por espaço): ").strip()
        pids = [int(p, 16) for p in pids_str.split()]
    else:
        pids = DEFAULT_PIDS
    
    interval_str = input("\nIntervalo entre polls [1.0s]: ").strip() or "1.0"
    interval = float(interval_str)
    
    # Conecta
    poller = OBD2Poller(channel, interface, bitrate)
    
    if not poller.connect():
        print("❌ Falha ao conectar!")
        return
    
    # Inicia polling
    try:
        poller.poll_pids(pids, interval)
    finally:
        poller.disconnect()
        print("\n✅ Desconectado")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário")
        sys.exit(0)
