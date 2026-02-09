"""
Load Log Handler
Handles loading of message logs from various file formats
"""

from PyQt6.QtWidgets import QFileDialog
from ..ui.message_box_helper import MessageBoxHelper
from ..i18n import t


class LoadLogHandler:
    """Handles loading of message logs"""
    
    def __init__(self, parent):
        """Initialize the handler
        
        Args:
            parent: The parent window (main_window)
        """
        self.parent = parent
        self.logger = parent.logger
    
    def load_log(self):
        """Load message log from file
        
        Supports JSON, CSV, and Trace file formats.
        Automatically switches to Tracer mode if needed.
        """
        filename, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Receive Log",
            "",
            "JSON Files (*.json);;Trace Files (*.trc);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            self.logger.info(f"Load Log: Starting - tracer_mode={self.parent.tracer_mode}")
            
            # Switch to Tracer mode if needed
            if not self.parent.tracer_mode:
                self.logger.info("Load Log: Switching to Tracer mode")
                self.parent.toggle_tracer_mode()
                self.logger.info(f"Load Log: After toggle - tracer_mode={self.parent.tracer_mode}")
            
            # Clear existing data
            self.parent.clear_receive()
            self.parent.message_counters.clear()
            
            # Load messages based on file type
            messages = self._load_messages_by_type(filename)
            
            if not messages:
                MessageBoxHelper.show_warning(self.parent, "Load Error", "Failed to load messages")
                return
            
            self.logger.info(f"Load Log: {len(messages)} messages loaded")
            
            # Add messages to recording and display
            for msg in messages:
                self.parent.recording_mgr.add_message(msg)
                self.parent.add_message_tracer_mode(msg)
            
            # Enable playback buttons if messages were loaded
            if self.parent.recording_mgr.get_message_count() > 0:
                self.parent.btn_play_all.setEnabled(True)
                self.parent.btn_play_selected.setEnabled(True)
            
            self.parent.update_message_count()
            
            # Show notification
            import os
            filename_short = os.path.basename(filename)
            self.parent.show_notification(
                t('notif_log_loaded', filename=filename_short, count=len(messages)),
                5000
            )
            
        except Exception as e:
            self.logger.error(f"Error loading log: {e}")
            MessageBoxHelper.show_error(self.parent, "Load Error", f"Error loading log: {str(e)}")
    
    def _load_messages_by_type(self, filename: str):
        """Load messages based on file extension
        
        Args:
            filename: Path to the file to load
            
        Returns:
            List of CANMessage objects or None on error
        """
        if filename.endswith('.csv'):
            return self.parent.file_handler.load_log_csv(filename)
        elif filename.endswith('.trc'):
            return self.parent.file_handler.load_log_json(filename)  # Trace uses JSON internally
        else:
            return self.parent.file_handler.load_log_json(filename)
