"""
File Handler

Manages file operations for saving and loading CAN logs and transmit lists.
Separated from UI code for better testability and maintainability.
"""

import json
import csv
from typing import List, Dict, Optional
from datetime import datetime
from ..models import CANMessage
from ..logger import get_logger


class FileHandler:
    """Handles file save/load operations"""
    
    def __init__(self, parent_window):
        """
        Initialize file handler.
        
        Args:
            parent_window: Main window instance
        """
        self.parent = parent_window
        self.logger = get_logger()
    
    # Save operations
    
    def save_log_json(self, filename: str, messages: List[CANMessage]) -> bool:
        """
        Save messages to JSON format.
        
        Args:
            filename: Output filename
            messages: List of CAN messages
            
        Returns:
            bool: True if saved successfully
        """
        try:
            data = {
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'message_count': len(messages),
                'messages': [msg.to_dict() for msg in messages]
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(messages)} messages to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving JSON: {e}")
            return False
    
    def save_log_csv(self, filename: str, messages: List[CANMessage]) -> bool:
        """
        Save messages to CSV format.
        
        Args:
            filename: Output filename
            messages: List of CAN messages
            
        Returns:
            bool: True if saved successfully
        """
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    'Timestamp', 'CAN ID', 'DLC', 'Data', 
                    'Extended', 'RTR', 'Source'
                ])
                
                # Data
                for msg in messages:
                    writer.writerow([
                        f"{msg.timestamp:.6f}",
                        f"0x{msg.can_id:X}",
                        msg.dlc,
                        msg.to_hex_string(),
                        msg.is_extended_id,
                        msg.is_remote_frame,
                        getattr(msg, 'source', 'N/A')
                    ])
            
            self.logger.info(f"Saved {len(messages)} messages to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving CSV: {e}")
            return False
    
    def save_log_trace(self, filename: str, messages: List[CANMessage]) -> bool:
        """
        Save messages to trace format (ASC-like).
        
        Args:
            filename: Output filename
            messages: List of CAN messages
            
        Returns:
            bool: True if saved successfully
        """
        try:
            with open(filename, 'w') as f:
                # Header
                f.write("date " + datetime.now().strftime("%a %b %d %I:%M:%S %p %Y") + "\n")
                f.write("base hex  timestamps absolute\n")
                f.write("internal events logged\n")
                f.write("// version 1.0.0\n")
                f.write("Begin Triggerblock\n")
                f.write("End Triggerblock\n\n")
                
                # Messages
                for msg in messages:
                    source = getattr(msg, 'source', '1')
                    id_str = f"{msg.can_id:X}"
                    if msg.is_extended_id:
                        id_str += "x"
                    
                    data_str = " ".join(f"{b:02X}" for b in msg.data)
                    
                    if msg.is_remote_frame:
                        f.write(f"{msg.timestamp:.6f} {source}  {id_str}             Rx   r {msg.dlc}\n")
                    else:
                        f.write(f"{msg.timestamp:.6f} {source}  {id_str}             Rx   d {msg.dlc} {data_str}\n")
            
            self.logger.info(f"Saved {len(messages)} messages to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving trace: {e}")
            return False
    
    # Load operations
    
    def load_log_json(self, filename: str) -> Optional[List[CANMessage]]:
        """
        Load messages from JSON format.
        
        Args:
            filename: Input filename
            
        Returns:
            List of CAN messages or None if error
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            messages = []
            for msg_data in data.get('messages', []):
                msg = CANMessage.from_dict(msg_data)
                messages.append(msg)
            
            self.logger.info(f"Loaded {len(messages)} messages from {filename}")
            return messages
            
        except Exception as e:
            self.logger.error(f"Error loading JSON: {e}")
            return None
    
    def load_log_csv(self, filename: str) -> Optional[List[CANMessage]]:
        """
        Load messages from CSV format.
        
        Args:
            filename: Input filename
            
        Returns:
            List of CAN messages or None if error
        """
        try:
            messages = []
            
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Parse data
                    data_str = row['Data'].replace(' ', '')
                    data = bytes.fromhex(data_str)
                    
                    # Create message
                    msg = CANMessage(
                        timestamp=float(row['Timestamp']),
                        can_id=int(row['CAN ID'], 16),
                        dlc=int(row['DLC']),
                        data=data,
                        is_extended_id=row['Extended'].lower() == 'true',
                        is_remote_frame=row['RTR'].lower() == 'true'
                    )
                    
                    if 'Source' in row and row['Source'] != 'N/A':
                        msg.source = row['Source']
                    
                    messages.append(msg)
            
            self.logger.info(f"Loaded {len(messages)} messages from {filename}")
            return messages
            
        except Exception as e:
            self.logger.error(f"Error loading CSV: {e}")
            return None
    
    # Transmit list operations
    
    def save_transmit_list(self, filename: str, transmit_list: List[Dict]) -> bool:
        """
        Save transmit list to JSON.
        
        Args:
            filename: Output filename
            transmit_list: List of transmit message dictionaries
            
        Returns:
            bool: True if saved successfully
        """
        try:
            data = {
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'messages': transmit_list
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(transmit_list)} transmit messages to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving transmit list: {e}")
            return False
    
    def load_transmit_list(self, filename: str) -> Optional[List[Dict]]:
        """
        Load transmit list from JSON.
        
        Args:
            filename: Input filename
            
        Returns:
            List of transmit message dictionaries or None if error
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            messages = data.get('messages', [])
            
            self.logger.info(f"Loaded {len(messages)} transmit messages from {filename}")
            return messages
            
        except Exception as e:
            self.logger.error(f"Error loading transmit list: {e}")
            return None
