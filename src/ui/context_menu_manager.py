"""
Context Menu Manager

Manages context menus for receive and transmit tables.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import QMenu, QTableWidget, QApplication, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from typing import Callable, Optional

from ..config import DEFAULT_CAN_ID_STR, DEFAULT_CHANNEL, DEFAULT_DLC_STR, DEFAULT_DLC_STR_EMPTY


class ContextMenuManager:
    """Manages context menus for tables"""
    
    def __init__(self, parent_window):
        """
        Initialize context menu manager
        
        Args:
            parent_window: Main window instance
        """
        self.parent = parent_window
    
    def show_receive_menu(self, table: QTableWidget, position):
        """
        Show context menu for receive table
        
        Args:
            table: Table widget
            position: Menu position
        """
        # Get the item at the clicked position
        item = table.itemAt(position)
        if item:
            # Select the row that was right-clicked
            row = item.row()
            table.selectRow(row)
        
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        menu = QMenu(self.parent)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Add to Transmit
        add_to_tx_action = QAction("➕ Add to Transmit", self.parent)
        add_to_tx_action.triggered.connect(lambda: self.add_selected_to_transmit(table))
        menu.addAction(add_to_tx_action)
        
        # Copy ID
        copy_id_action = QAction("📋 Copy ID", self.parent)
        copy_id_action.triggered.connect(lambda: self.copy_selected_id(table))
        menu.addAction(copy_id_action)
        
        # Copy Data
        copy_data_action = QAction("📋 Copy Data", self.parent)
        copy_data_action.triggered.connect(lambda: self.copy_selected_data(table))
        menu.addAction(copy_data_action)
        
        menu.addSeparator()
        
        # Bit Field Viewer (single selection only)
        if len(selected_rows) == 1:
            bit_viewer_action = QAction("🔬 Bit Field Viewer", self.parent)
            bit_viewer_action.triggered.connect(lambda: self.show_bit_field_viewer(table))
            menu.addAction(bit_viewer_action)
        
        menu.exec(table.viewport().mapToGlobal(position))
    
    def show_transmit_menu(self, position):
        """
        Show context menu for transmit table
        
        Args:
            position: Menu position
        """
        table = self.parent.transmit_table
        
        # Get the item at the clicked position
        item = table.itemAt(position)
        if item:
            # Select the row that was right-clicked
            row = item.row()
            table.selectRow(row)
        
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        menu = QMenu(self.parent)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Send Once
        send_once_action = QAction("📤 Send Once", self.parent)
        send_once_action.triggered.connect(self.send_selected_tx_once)
        menu.addAction(send_once_action)
        
        menu.addSeparator()
        
        # Start Periodic
        start_periodic_action = QAction("▶ Start Periodic", self.parent)
        start_periodic_action.triggered.connect(self.start_selected_periodic)
        menu.addAction(start_periodic_action)
        
        # Stop Periodic
        stop_periodic_action = QAction("⏹ Stop Periodic", self.parent)
        stop_periodic_action.triggered.connect(self.stop_selected_periodic)
        menu.addAction(stop_periodic_action)
        
        menu.addSeparator()
        
        # Delete
        delete_action = QAction("🗑 Delete", self.parent)
        delete_action.triggered.connect(self.delete_selected_tx_messages)
        menu.addAction(delete_action)
        
        menu.exec(table.viewport().mapToGlobal(position))
    
    def add_selected_to_transmit(self, table: QTableWidget):
        """Add selected messages to transmit list"""
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        added_count = 0
        for index in selected_rows:
            row = index.row()
            
            try:
                # Get message data from table
                period_for_tx = "off"
                if self.parent.tracer_mode:
                    # Tracer: columns are ID, Time, Channel, PID, DLC, Data, ASCII, Comment
                    pid_str = table.item(row, 3).text() if table.item(row, 3) else DEFAULT_CAN_ID_STR
                    dlc_str = table.item(row, 4).text() if table.item(row, 4) else DEFAULT_DLC_STR
                    data_str = table.item(row, 5).text() if table.item(row, 5) else ""
                    channel_str = table.item(row, 2).text() if table.item(row, 2) else DEFAULT_CHANNEL
                else:
                    # Monitor: columns are ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
                    pid_str = table.item(row, 3).text() if table.item(row, 3) else DEFAULT_CAN_ID_STR
                    dlc_str = table.item(row, 4).text() if table.item(row, 4) else DEFAULT_DLC_STR
                    data_str = table.item(row, 5).text() if table.item(row, 5) else ""
                    channel_str = table.item(row, 2).text() if table.item(row, 2) else DEFAULT_CHANNEL
                    # Use observed period from monitor; fallback to default 100 ms
                    period_item = table.item(row, 6)
                    period_str = period_item.text().strip() if period_item else ""
                    try:
                        period_ms = int(period_str)
                        period_for_tx = str(period_ms) if period_ms > 0 else "off"
                    except ValueError:
                        period_for_tx = "100"  # predefined default when period not yet available
                
                # Parse data
                can_id_str = pid_str.replace('0x', '').replace('0X', '')
                can_id = int(can_id_str, 16)
                dlc = int(dlc_str)
                data_clean = data_str.replace(' ', '')
                
                # Add to transmit table
                tx_row = self.parent.transmit_table.rowCount()
                self.parent.transmit_table.insertRow(tx_row)
                
                # Set items
                from PyQt6.QtWidgets import QTableWidgetItem
                self.parent.transmit_table.setItem(tx_row, 0, QTableWidgetItem(pid_str))
                self.parent.transmit_table.setItem(tx_row, 1, QTableWidgetItem(str(dlc)))
                self.parent.transmit_table.setItem(tx_row, 2, QTableWidgetItem(""))  # RTR
                self.parent.transmit_table.setItem(tx_row, 3, QTableWidgetItem(period_for_tx))  # Period (from monitor or default)
                self.parent.transmit_table.setItem(tx_row, 4, QTableWidgetItem("off"))  # TX Mode
                self.parent.transmit_table.setItem(tx_row, 5, QTableWidgetItem(""))  # Trigger ID
                self.parent.transmit_table.setItem(tx_row, 6, QTableWidgetItem(""))  # Trigger Data
                
                # Data bytes (D0-D7)
                for i in range(8):
                    if i * 2 < len(data_clean):
                        byte_hex = data_clean[i*2:i*2+2]
                        byte_item = QTableWidgetItem(byte_hex.upper())
                    else:
                        byte_item = QTableWidgetItem("")
                    byte_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.parent.transmit_table.setItem(tx_row, 7 + i, byte_item)
                
                # Count and Comment
                self.parent.transmit_table.setItem(tx_row, 15, QTableWidgetItem("0"))
                self.parent.transmit_table.setItem(tx_row, 16, QTableWidgetItem(""))
                
                # Source
                source_item = QTableWidgetItem(channel_str)
                source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.parent.transmit_table.setItem(tx_row, 17, source_item)
                
                added_count += 1
                
            except Exception as e:
                self.parent.logger.error(f"Error adding message from row {row}: {e}")
                continue
        
        if added_count > 0:
            self.parent.show_notification(f"✅ {added_count} mensagem(ns) adicionada(s) à lista de transmissão!", 3000)
    
    def copy_selected_id(self, table: QTableWidget):
        """Copy selected message ID to clipboard"""
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        id_str = table.item(row, 3).text() if table.item(row, 3) else ""
        
        clipboard = QApplication.clipboard()
        clipboard.setText(id_str)
        
        from ..i18n import t
        self.parent.show_notification(t('notif_id_copied', id=id_str), 2000)
    
    def copy_selected_data(self, table: QTableWidget):
        """Copy selected message data to clipboard"""
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        data_str = table.item(row, 5).text() if table.item(row, 5) else ""
        
        clipboard = QApplication.clipboard()
        clipboard.setText(data_str)
        
        from ..i18n import t
        self.parent.show_notification(t('notif_data_copied', data=data_str), 2000)
    
    def show_bit_field_viewer(self, table: QTableWidget):
        """Show bit field viewer for selected message"""
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Get message data from table
        pid_str = table.item(row, 3).text() if table.item(row, 3) else DEFAULT_CAN_ID_STR
        dlc_str = table.item(row, 4).text() if table.item(row, 4) else DEFAULT_DLC_STR_EMPTY
        data_str = table.item(row, 5).text() if table.item(row, 5) else ""
        
        try:
            can_id = int(pid_str.replace('0x', ''), 16)
            dlc = int(dlc_str)
            data = bytes.fromhex(data_str.replace(' ', ''))
            
            from ..models import CANMessage
            message = CANMessage(
                timestamp=0,
                can_id=can_id,
                dlc=dlc,
                data=data
            )
            
            from ..dialogs import BitFieldViewerDialog
            dialog = BitFieldViewerDialog(self.parent, message)
            dialog.exec()
            
        except Exception as e:
            self.parent.logger.error(f"Error opening Bit Field Viewer: {e}")
    
    def send_selected_tx_once(self):
        """Send selected transmit messages once"""
        table = self.parent.transmit_table
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        if not self.parent.transmit_handler:
            from ..i18n import t
            self.parent.show_notification(t('notif_connect_first'), 3000)
            return
        
        sent_count = 0
        for index in selected_rows:
            row = index.row()
            
            try:
                msg_data = self.parent.get_tx_message_data_from_table(row)
                target_bus = msg_data.get('target_bus')
                
                if self.parent.transmit_handler.send_single(msg_data, target_bus):
                    sent_count += 1
                    self.parent._increment_tx_count(row)
                    
            except Exception as e:
                self.parent.logger.error(f"Error sending message from row {row}: {e}")
        
        if sent_count > 0:
            from ..i18n import t
            self.parent.show_notification(t('notif_messages_sent', count=sent_count), 2000)
    
    def start_selected_periodic(self):
        """Start periodic transmission of selected messages"""
        # Delegate to parent
        self.parent.start_selected_periodic()
    
    def stop_selected_periodic(self):
        """Stop periodic transmission of selected messages"""
        # Delegate to parent
        self.parent.stop_selected_periodic()
    
    def delete_selected_tx_messages(self):
        """Delete selected messages from transmit table"""
        # Delegate to parent
        self.parent.delete_selected_tx_messages()
