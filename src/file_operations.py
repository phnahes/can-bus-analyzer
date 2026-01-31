"""
File Operations - Gerenciamento de save/load de logs, traces e TX lists
"""

import json
import csv
from typing import List, Dict
from datetime import datetime

from .models import CANMessage


class FileOperations:
    """Classe para operações de arquivo (save/load)"""
    
    @staticmethod
    def save_log_json(filename: str, messages: List[CANMessage], mode: str = "tracer"):
        """Salva log em formato JSON"""
        data = {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'mode': mode,
            'message_count': len(messages),
            'messages': [msg.to_dict() for msg in messages]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def save_log_csv(filename: str, messages: List[CANMessage]):
        """Salva log em formato CSV"""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'ID', 'DLC', 'Data', 'Comment'])
            
            for msg in messages:
                data_hex = msg.data.hex().upper()
                data_spaced = ' '.join([data_hex[i:i+2] for i in range(0, len(data_hex), 2)])
                writer.writerow([
                    msg.timestamp,
                    f"0x{msg.can_id:03X}",
                    msg.dlc,
                    data_spaced,
                    msg.comment
                ])
    
    @staticmethod
    def save_log_trace(filename: str, messages: List[CANMessage]):
        """Salva log em formato TRC (Trace)"""
        with open(filename, 'w') as f:
            f.write(";$FILEVERSION=1.1\n")
            f.write(";$STARTTIME=0.0\n")
            f.write(";$COLUMNS=N,O,T,I,d,l,D\n")
            f.write(";   N: Message number\n")
            f.write(";   O: Time offset (ms)\n")
            f.write(";   T: Message type\n")
            f.write(";   I: CAN ID (hex)\n")
            f.write(";   d: Data length\n")
            f.write(";   l: Data bytes (hex)\n")
            f.write(";   D: ASCII representation\n")
            f.write(";\n")
            
            first_timestamp = messages[0].timestamp if messages else 0
            
            for idx, msg in enumerate(messages, start=1):
                time_offset = (msg.timestamp - first_timestamp) * 1000  # ms
                data_hex = ' '.join([f"{b:02X}" for b in msg.data])
                ascii_repr = msg.to_ascii()
                
                f.write(f"{idx:6d} {time_offset:10.1f} Rx {msg.can_id:03X} {msg.dlc} {data_hex:23s} {ascii_repr}\n")
    
    @staticmethod
    def load_log_json(filename: str) -> List[CANMessage]:
        """Carrega log de formato JSON"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Suportar formato antigo (lista) e novo (dict com metadata)
        if isinstance(data, list):
            messages_data = data
        else:
            messages_data = data.get('messages', [])
        
        messages = []
        for item in messages_data:
            msg = CANMessage(
                timestamp=item['timestamp'],
                can_id=item['can_id'],
                dlc=item['dlc'],
                data=bytes.fromhex(item['data']),
                comment=item.get('comment', ''),
                period=item.get('period', 0),
                count=item.get('count', 0)
            )
            messages.append(msg)
        
        return messages
    
    @staticmethod
    def load_log_csv(filename: str) -> List[CANMessage]:
        """Carrega log de formato CSV"""
        messages = []
        
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Parse ID
                    id_str = row['ID'].replace('0x', '').replace('0X', '')
                    can_id = int(id_str, 16)
                    
                    # Parse data
                    data_str = row['Data'].replace(' ', '')
                    data = bytes.fromhex(data_str)
                    
                    msg = CANMessage(
                        timestamp=float(row['Timestamp']),
                        can_id=can_id,
                        dlc=int(row['DLC']),
                        data=data,
                        comment=row.get('Comment', '')
                    )
                    messages.append(msg)
                except Exception as e:
                    print(f"Erro ao carregar linha CSV: {e}")
                    continue
        
        return messages
    
    @staticmethod
    def load_log_trace(filename: str) -> List[CANMessage]:
        """Carrega log de formato TRC (Trace)"""
        messages = []
        start_time = None
        
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Pular comentários e linhas vazias
                if line.startswith(';') or not line:
                    continue
                
                try:
                    parts = line.split()
                    if len(parts) < 6:
                        continue
                    
                    # Parse: N O T I d l D
                    msg_num = int(parts[0])
                    time_offset = float(parts[1]) / 1000.0  # ms para s
                    msg_type = parts[2]  # Rx/Tx
                    can_id = int(parts[3], 16)
                    dlc = int(parts[4])
                    
                    # Data bytes
                    data_bytes = []
                    for i in range(5, 5 + dlc):
                        if i < len(parts):
                            data_bytes.append(int(parts[i], 16))
                    
                    data = bytes(data_bytes)
                    
                    # ASCII (resto da linha)
                    ascii_part = ' '.join(parts[5 + dlc:]) if len(parts) > 5 + dlc else ''
                    
                    if start_time is None:
                        start_time = time_offset
                    
                    msg = CANMessage(
                        timestamp=time_offset,
                        can_id=can_id,
                        dlc=dlc,
                        data=data,
                        comment=ascii_part
                    )
                    messages.append(msg)
                    
                except Exception as e:
                    print(f"Erro ao carregar linha TRC: {e}")
                    continue
        
        return messages
    
    @staticmethod
    def save_transmit_list(filename: str, transmit_data: List[Dict]):
        """Salva lista de transmissão em JSON"""
        data = {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'transmit_messages': transmit_data
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def load_transmit_list(filename: str) -> List[Dict]:
        """Carrega lista de transmissão de JSON"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Suportar formato antigo (lista) e novo (dict com metadata)
        if isinstance(data, list):
            return data
        else:
            return data.get('transmit_messages', [])
