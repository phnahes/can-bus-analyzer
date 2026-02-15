"""
Monitor Log Handler
Handles loading and saving of monitor mode logs
"""

from PyQt6.QtWidgets import QFileDialog
from ..ui.message_box_helper import MessageBoxHelper
from ..i18n import t


class MonitorLogHandler:
    """Handles monitor mode log operations"""
    
    def __init__(self, parent):
        """Initialize the handler
        
        Args:
            parent: The parent window (main_window)
        """
        self.parent = parent
        self.logger = parent.logger
    
    def load_monitor_log(self):
        """Load monitor mode log from file"""
        filename, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Monitor Log",
            "",
            "JSON Files (*.json);;Trace Files (*.trc);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            self.logger.info(f"Carregando Monitor log: {filename}")
            
            # Switch to Monitor mode if needed
            if self.parent.tracer_mode:
                self.logger.info("Load Monitor: Mudando para modo Monitor")
                self.parent.toggle_tracer_mode()
            
            # Clear existing data
            self.parent.clear_receive()
            self.parent.message_counters.clear()
            
            # Load messages based on file type
            messages = self._load_messages_by_type(filename)
            
            if not messages:
                MessageBoxHelper.show_warning(self.parent, "Load Error", "Failed to load messages")
                return
            
            self.logger.info(f"Monitor log carregado: {len(messages)} mensagens")
            
            # Add messages to monitor mode
            for msg in messages:
                self.parent.received_messages.append(msg)
                self.parent.add_message_monitor_mode(msg)
            
            self.parent.update_message_count()
            
            # Show notification
            import os
            filename_short = os.path.basename(filename)
            self.parent.show_notification(
                t('notif_monitor_loaded', filename=filename_short, count=len(messages)),
                5000
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar Monitor log: {e}", exc_info=True)
            MessageBoxHelper.show_error(
                self.parent, 
                "Load Error", 
                f"Erro ao carregar: {str(e)}"
            )
    
    def _load_messages_by_type(self, filename: str):
        """Load messages based on file extension"""
        if filename.endswith('.csv'):
            return self.parent.file_handler.load_log_csv(filename)
        elif filename.endswith('.trc'):
            return self.parent.file_handler.load_log_json(filename)
        else:
            return self.parent.file_handler.load_log_json(filename)
    
    def save_monitor_log(self):
        """Save monitor mode log to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save Monitor Log",
            "",
            "JSON Files (*.json);;Trace Files (*.trc);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            self.logger.info(f"Salvando Monitor log: {filename}")
            
            messages_to_save = self.parent.received_messages
            
            success = False
            if filename.endswith('.csv'):
                success = self.parent.file_handler.save_log_csv(filename, messages_to_save)
            elif filename.endswith('.trc'):
                success = self.parent.file_handler.save_log_trace(filename, messages_to_save)
            else:
                success = self.parent.file_handler.save_log_json(filename, messages_to_save)
            
            if success:
                import os
                filename_short = os.path.basename(filename)
                self.parent.show_notification(
                    t('notif_monitor_saved', filename=filename_short, count=len(messages_to_save)),
                    5000
                )
        except Exception as e:
            self.logger.error(f"Erro ao salvar Monitor log: {str(e)}", exc_info=True)
            MessageBoxHelper.show_error(
                self.parent, 
                "Save Error", 
                f"Erro ao salvar: {str(e)}"
            )
