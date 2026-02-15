"""
Transmit Load Handler
Handles loading of transmit message lists
"""

from PyQt6.QtWidgets import QFileDialog
from ..ui.message_box_helper import MessageBoxHelper
from ..i18n import t


class TransmitLoadHandler:
    """Handles loading of transmit message lists"""
    
    def __init__(self, parent):
        """Initialize the handler
        
        Args:
            parent: The parent window (main_window)
        """
        self.parent = parent
        self.logger = parent.logger
    
    def load_transmit_list(self):
        """Load transmit message list from file"""
        filename, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Transmit List",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            transmit_data = self.parent.file_handler.load_transmit_list(filename)
            
            if not transmit_data:
                MessageBoxHelper.show_warning(
                    self.parent, 
                    "Load Error", 
                    "Failed to load transmit list"
                )
                return
            
            # Ask if should clear existing data
            clear_existing = True
            if self.parent.transmit_table.rowCount() > 0:
                clear_existing = MessageBoxHelper.ask_yes_no(
                    self.parent,
                    "Load Transmit List",
                    "Limpar lista atual antes de carregar?"
                )
            
            # Use transmit_table_mgr to populate the table
            self.parent.transmit_table_mgr.load_from_data(
                self.parent.transmit_table, 
                transmit_data, 
                clear_existing
            )
            
            # Show notification
            import os
            filename_short = os.path.basename(filename)
            self.parent.show_notification(
                t('notif_tx_loaded', filename=filename_short, count=len(transmit_data)),
                5000
            )
            
        except Exception as e:
            self.logger.error(f"Error loading transmit list: {e}", exc_info=True)
            MessageBoxHelper.show_error(
                self.parent, 
                "Load Error", 
                f"Erro ao carregar: {str(e)}"
            )
