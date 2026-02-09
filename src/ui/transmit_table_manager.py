"""
Transmit Table Manager

Manages transmit table operations and message editing.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt
from typing import Dict, List, Optional


class TransmitTableManager:
    """Manages transmit table operations"""
    
    def __init__(self, parent_window):
        """
        Initialize transmit table manager
        
        Args:
            parent_window: Main window instance
        """
        self.parent = parent_window
        self.editing_row = -1
    
    def clear_fields(self):
        """Clear all transmit edit fields"""
        self.parent.tx_id_input.setText("000")
        self.parent.tx_dlc_input.setValue(8)
        self.parent.tx_29bit_check.setChecked(False)
        self.parent.tx_rtr_check.setChecked(False)
        for i in range(8):
            self.parent.tx_data_bytes[i].setText("00")
        self.parent.tx_period_input.setText("0")
        self.parent.tx_mode_combo.setCurrentIndex(0)
        self.parent.trigger_id_input.setText("")
        self.parent.trigger_data_input.setText("")
        self.parent.tx_comment_input.setText("")
        self.editing_row = -1
        # Update button to "Add"
        self.parent.btn_add.setText("Add")
    
    def add_message(self, table: QTableWidget) -> bool:
        """
        Add or update message in the transmit list
        
        Args:
            table: Transmit table widget
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we are editing an existing row or adding new
            if self.editing_row >= 0 and self.editing_row < table.rowCount():
                # Editing existing row
                row = self.editing_row
            else:
                # Adding new row
                row = table.rowCount()
                table.insertRow(row)
            
            # Columns: ID, DLC, RTR, Period, TX Mode, Trigger ID, Trigger Data, D0-D7, Count, Comment, Source
            # 0: ID
            table.setItem(row, 0, QTableWidgetItem(self.parent.tx_id_input.text()))
            
            # 1: DLC
            dlc = self.parent.tx_dlc_input.value()
            table.setItem(row, 1, QTableWidgetItem(str(dlc)))
            
            # 2: RTR
            rtr = "✓" if self.parent.tx_rtr_check.isChecked() else ""
            rtr_item = QTableWidgetItem(rtr)
            rtr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, rtr_item)
            
            # 3: Period
            period = self.parent.tx_period_input.text()
            table.setItem(row, 3, QTableWidgetItem(period if period != "0" else "off"))
            
            # 4: TX Mode
            tx_mode = self.parent.tx_mode_combo.currentText()
            table.setItem(row, 4, QTableWidgetItem(tx_mode))
            
            # 5: Trigger ID
            trigger_id = self.parent.trigger_id_input.text()
            table.setItem(row, 5, QTableWidgetItem(trigger_id if trigger_id else ""))
            
            # 6: Trigger Data
            trigger_data = self.parent.trigger_data_input.text()
            table.setItem(row, 6, QTableWidgetItem(trigger_data if trigger_data else ""))
            
            # 7-14: Data bytes (D0-D7)
            for i in range(8):
                byte_val = self.parent.tx_data_bytes[i].text() if i < dlc else ""
                byte_item = QTableWidgetItem(byte_val)
                byte_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, 7 + i, byte_item)
            
            # 15: Count - keep existing value if editing
            if self.editing_row >= 0:
                # Keep existing count when editing
                count_item = table.item(row, 15)
                if not count_item:
                    table.setItem(row, 15, QTableWidgetItem("0"))
            else:
                # New message, count = 0
                table.setItem(row, 15, QTableWidgetItem("0"))
            
            # 16: Comment
            table.setItem(row, 16, QTableWidgetItem(self.parent.tx_comment_input.text()))
            
            # 17: Source
            source = self.parent.tx_source_combo.currentText()
            source_item = QTableWidgetItem(source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 17, source_item)
            
            # Reset edit state
            self.editing_row = -1
            self.clear_fields()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Error adding message: {str(e)}")
            return False
    
    def load_message_to_edit(self, table: QTableWidget):
        """
        Load message from table into edit fields (double-click or copy)
        
        Args:
            table: Transmit table widget
        """
        current_row = table.currentRow()
        if current_row < 0:
            return
        
        try:
            # 0: ID
            self.parent.tx_id_input.setText(table.item(current_row, 0).text())
            
            # 1: DLC
            dlc = int(table.item(current_row, 1).text())
            self.parent.tx_dlc_input.setValue(dlc)
            
            # 2: RTR
            rtr_item = table.item(current_row, 2)
            self.parent.tx_rtr_check.setChecked(rtr_item and rtr_item.text() == "✓")
            
            # 3: Period
            period = table.item(current_row, 3).text()
            self.parent.tx_period_input.setText(period if period != "off" else "0")
            
            # 4: TX Mode
            tx_mode = table.item(current_row, 4).text()
            index = self.parent.tx_mode_combo.findText(tx_mode)
            if index >= 0:
                self.parent.tx_mode_combo.setCurrentIndex(index)
            
            # 5: Trigger ID
            trigger_id_item = table.item(current_row, 5)
            self.parent.trigger_id_input.setText(trigger_id_item.text() if trigger_id_item else "")
            
            # 6: Trigger Data
            trigger_data_item = table.item(current_row, 6)
            self.parent.trigger_data_input.setText(trigger_data_item.text() if trigger_data_item else "")
            
            # 7-14: Data bytes (D0-D7)
            for i in range(8):
                byte_item = table.item(current_row, 7 + i)
                if byte_item and byte_item.text():
                    self.parent.tx_data_bytes[i].setText(byte_item.text())
                else:
                    self.parent.tx_data_bytes[i].setText("00")
            
            # 16: Comment
            comment_item = table.item(current_row, 16)
            self.parent.tx_comment_input.setText(comment_item.text() if comment_item else "")
            
            # 17: Source
            source_item = table.item(current_row, 17)
            if source_item:
                source_text = source_item.text()
                index = self.parent.tx_source_combo.findText(source_text)
                if index >= 0:
                    self.parent.tx_source_combo.setCurrentIndex(index)
            
            # Set that we are editing this row
            self.editing_row = current_row
            
            # Change button to "Save"
            self.parent.btn_add.setText("Save")
            
        except Exception as e:
            self.parent.logger.error(f"Error loading message: {e}")
    
    def delete_message(self, table: QTableWidget) -> bool:
        """
        Remove message from list
        
        Args:
            table: Transmit table widget
            
        Returns:
            True if successful, False otherwise
        """
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
            return True
        return False
    
    def get_message_data(self, table: QTableWidget, row: int) -> Optional[Dict]:
        """
        Get data of a message from the transmit table
        
        Args:
            table: Transmit table widget
            row: Row number
            
        Returns:
            Dictionary with message data or None if error
        """
        try:
            from ..logger import get_logger
            logger = get_logger()
            
            # Columns: PID(0), DLC(1), RTR(2), Period(3), TX Mode(4), Trigger ID(5), Trigger Data(6), D0-D7(7-14), Count(15), Comment(16), Channel(17)
            
            # ID
            can_id_str = table.item(row, 0).text().replace('0x', '').replace('0X', '')
            can_id = int(can_id_str, 16)
            logger.debug(f"get_message_data[{row}]: can_id=0x{can_id:03X}")
            
            # DLC
            dlc = int(table.item(row, 1).text())
            logger.debug(f"get_message_data[{row}]: dlc={dlc}")
            
            # RTR
            rtr_item = table.item(row, 2)
            rtr_text = rtr_item.text() if rtr_item else ""
            is_rtr = rtr_item and rtr_item.text() == "✓"
            logger.debug(f"get_message_data[{row}]: rtr_item={rtr_item}, rtr_text='{rtr_text}', is_rtr={is_rtr}")
            
            # Period
            period_item = table.item(row, 3)
            period = period_item.text() if period_item else "off"
            logger.debug(f"get_message_data[{row}]: period={period}")
            
            # TX Mode
            tx_mode_item = table.item(row, 4)
            tx_mode = tx_mode_item.text() if tx_mode_item else "off"
            logger.debug(f"get_message_data[{row}]: tx_mode={tx_mode}")
            
            # Trigger ID
            trigger_id_item = table.item(row, 5)
            trigger_id = trigger_id_item.text() if trigger_id_item else ""
            
            # Trigger Data
            trigger_data_item = table.item(row, 6)
            trigger_data = trigger_data_item.text() if trigger_data_item else ""
            
            # Data bytes (D0-D7)
            data_bytes = []
            for i in range(dlc):
                byte_item = table.item(row, 7 + i)
                if byte_item and byte_item.text():
                    data_bytes.append(byte_item.text())
                else:
                    data_bytes.append("00")
            
            logger.debug(f"get_message_data[{row}]: data_bytes={data_bytes}")
            data = bytes.fromhex(''.join(data_bytes))
            logger.debug(f"get_message_data[{row}]: data={data.hex()}")
            
            # Comment
            comment_item = table.item(row, 16)
            comment = comment_item.text() if comment_item else ""
            
            # Source/Channel
            source_item = table.item(row, 17)
            target_bus = source_item.text() if source_item else None
            
            result = {
                'id': can_id,
                'can_id': can_id,
                'dlc': dlc,
                'data': data,
                'extended': can_id > 0x7FF,
                'is_rtr': is_rtr,
                'period': period,
                'tx_mode': tx_mode,
                'trigger_id': trigger_id,
                'trigger_data': trigger_data,
                'comment': comment,
                'target_bus': target_bus
            }
            
            logger.debug(f"get_message_data[{row}]: returning {result}")
            return result
            
        except Exception as e:
            self.parent.logger.error(f"Error getting message data from row {row}: {e}")
            return None
    
    def increment_count(self, table: QTableWidget, row: int):
        """
        Increment message count in table
        
        Args:
            table: Transmit table widget
            row: Row number
        """
        count_item = table.item(row, 15)
        if count_item:
            current_count = int(count_item.text()) if count_item.text().isdigit() else 0
            count_item.setText(str(current_count + 1))
        else:
            # Create item if it doesn't exist
            new_item = QTableWidgetItem("1")
            new_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 15, new_item)
    
    def load_from_data(self, table: QTableWidget, transmit_data: List[Dict], clear_existing: bool = True):
        """
        Load transmit list from data
        
        Args:
            table: Transmit table widget
            transmit_data: List of message dictionaries
            clear_existing: Whether to clear existing messages
        """
        if clear_existing:
            table.setRowCount(0)
        
        for item in transmit_data:
            row = table.rowCount()
            table.insertRow(row)
            
            table.setItem(row, 0, QTableWidgetItem(item.get('id', '000')))
            
            dlc = item.get('dlc', 8)
            table.setItem(row, 1, QTableWidgetItem(str(dlc)))
            
            rtr = "✓" if item.get('rtr', False) else ""
            rtr_item = QTableWidgetItem(rtr)
            rtr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, rtr_item)
            
            table.setItem(row, 3, QTableWidgetItem(item.get('period', 'off')))
            table.setItem(row, 4, QTableWidgetItem(item.get('tx_mode', 'off')))
            table.setItem(row, 5, QTableWidgetItem(item.get('trigger_id', '')))
            table.setItem(row, 6, QTableWidgetItem(item.get('trigger_data', '')))
            
            data_str = item.get('data', '0000000000000000')
            for i in range(8):
                if i * 2 < len(data_str):
                    byte_hex = data_str[i*2:i*2+2]
                    byte_item = QTableWidgetItem(byte_hex.upper())
                else:
                    byte_item = QTableWidgetItem("")
                byte_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, 7 + i, byte_item)
            
            table.setItem(row, 15, QTableWidgetItem(str(item.get('count', 0))))
            table.setItem(row, 16, QTableWidgetItem(item.get('comment', '')))
            
            source = item.get('source', 'CAN1')
            source_item = QTableWidgetItem(source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 17, source_item)
