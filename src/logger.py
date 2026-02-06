"""
Logger - Logging system for CAN Analyzer
Saves logs to file with automatic rotation
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class CANLogger:
    """Application log manager"""
    
    def __init__(self, log_dir: str = "logs", max_bytes: int = 10*1024*1024, backup_count: int = 5):
        """
        Initialize the logging system
        
        Args:
            log_dir: Directory to save logs
            max_bytes: Maximum log file size (default: 10MB)
            backup_count: Number of backup files (default: 5)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Log filename with date
        log_filename = self.log_dir / f"can_analyzer_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Configure main logger
        self.logger = logging.getLogger('CANAnalyzer')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler (INFO and above only)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Detailed format for file
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Simple format for console
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Initial log
        self.logger.info("=" * 80)
        self.logger.info("CAN Analyzer started")
        self.logger.info(f"Log file: {log_filename}")
        self.logger.info("=" * 80)
    
    def debug(self, message: str):
        """Debug log"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Info log"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Warning log"""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info=False):
        """Error log"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info=False):
        """Critical log"""
        self.logger.critical(message, exc_info=exc_info)
    
    def log_can_message(self, direction: str, msg_id: int, data: bytes, dlc: int):
        """
        Specific log for CAN messages
        
        Args:
            direction: 'RX' or 'TX'
            msg_id: CAN message ID
            data: Message data
            dlc: Data Length Code
        """
        data_hex = ' '.join([f'{b:02X}' for b in data])
        self.logger.debug(f"CAN {direction} | ID: 0x{msg_id:03X} | DLC: {dlc} | Data: {data_hex}")
    
    def log_connection(self, status: str, details: str = ""):
        """Log connection events"""
        self.logger.info(f"Connection {status} | {details}")
    
    def log_file_operation(self, operation: str, filename: str, status: str = "success"):
        """Log file operations"""
        self.logger.info(f"File {operation} | {filename} | Status: {status}")
    
    def log_filter(self, action: str, details: str):
        """Log filter operations"""
        self.logger.info(f"Filter {action} | {details}")
    
    def log_trigger(self, trigger_id: int, tx_id: int, comment: str = ""):
        """Log fired triggers"""
        self.logger.info(f"Trigger fired | 0x{trigger_id:03X} → 0x{tx_id:03X} | {comment}")
    
    def log_playback(self, action: str, message_count: int = 0):
        """Log playback operations"""
        self.logger.info(f"Playback {action} | Messages: {message_count}")
    
    def log_exception(self, exception: Exception, context: str = ""):
        """Log exceptions with context"""
        self.logger.error(f"Exception in {context}: {str(exception)}", exc_info=True)
    
    def shutdown(self):
        """Shutdown the logging system"""
        self.logger.info("=" * 80)
        self.logger.info("CAN Analyzer terminated")
        self.logger.info("=" * 80)
        
        # Close handlers
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)


# Global logger instance
_logger_instance = None


def get_logger() -> CANLogger:
    """Returns the global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = CANLogger()
    return _logger_instance


def init_logger(log_dir: str = "logs", max_bytes: int = 10*1024*1024, backup_count: int = 5) -> CANLogger:
    """
    Initialize the global logger
    
    Args:
        log_dir: Directory to save logs
        max_bytes: Maximum log file size
        backup_count: Number of backup files
    
    Returns:
        Logger instance
    """
    global _logger_instance
    _logger_instance = CANLogger(log_dir, max_bytes, backup_count)
    return _logger_instance


def shutdown_logger():
    """Shutdown the global logger"""
    global _logger_instance
    if _logger_instance:
        _logger_instance.shutdown()
        _logger_instance = None
