"""
Save Transmit Handler
Handles saving of transmit message lists
"""

from PyQt6.QtWidgets import QFileDialog
from ..config import DEFAULT_CHANNEL
from ..ui.message_box_helper import MessageBoxHelper
from ..i18n import t


class SaveTransmitHandler:
    """Handles saving of transmit message lists"""
    
    def __init__(self, parent):
        """Initialize the handler
        
        Args:
            parent: The parent window (main_window)
        """
        self.parent = parent
        self.logger = parent.logger
    
    def save_transmit_list(self):
        """Save transmit message list to JSON file"""
        filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save Transmit List",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            transmit_data = self._extract_transmit_data()
            
            if self.parent.file_handler.save_transmit_list(filename, transmit_data):
                import os
                filename_short = os.path.basename(filename)
                self.parent.show_notification(
                    t('notif_tx_saved', filename=filename_short, count=len(transmit_data)),
                    5000
                )
        except Exception as e:
            MessageBoxHelper.show_error(self.parent, "Save Error", f"Error saving: {str(e)}")
    
    def _extract_transmit_data(self) -> list:
        """Extract transmit data from the table
        
        Returns:
            List of dictionaries containing message data
        """
        transmit_data = []
        
        for row in range(self.parent.transmit_table.rowCount()):
            msg_data = self.parent.get_tx_message_data_from_table(row)
            
            # Get additional table items
            tx_mode_item = self.parent.transmit_table.item(row, 4)
            trigger_id_item = self.parent.transmit_table.item(row, 5)
            trigger_data_item = self.parent.transmit_table.item(row, 6)
            count_item = self.parent.transmit_table.item(row, 15)
            comment_item = self.parent.transmit_table.item(row, 16)
            source_item = self.parent.transmit_table.item(row, 17)
            
            item_data = {
                'id': f"{msg_data['can_id']:03X}",
                'dlc': msg_data['dlc'],
                'rtr': msg_data['is_rtr'],
                'data': msg_data['data'].hex().upper(),
                'period': msg_data['period'],
                'tx_mode': tx_mode_item.text() if tx_mode_item else 'off',
                'trigger_id': trigger_id_item.text() if trigger_id_item else '',
                'trigger_data': trigger_data_item.text() if trigger_data_item else '',
                'count': int(count_item.text()) if count_item else 0,
                'comment': comment_item.text() if comment_item else '',
                'source': source_item.text() if source_item else DEFAULT_CHANNEL
            }
            transmit_data.append(item_data)
        
        return transmit_data
