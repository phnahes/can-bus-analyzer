"""
Logger - Logging system for CAN Analyzer
Saves logs to file with automatic rotation

Uses configuration from config.logger_config for centralized settings.
"""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config.logger_config import LoggerConfig


class CANLogger:
    """Application log manager"""
    
    def __init__(self, log_dir: str = None, max_bytes: int = None, backup_count: int = None):
        """
        Initialize the logging system
        
        Args:
            log_dir: Directory to save logs (default: from LoggerConfig)
            max_bytes: Maximum log file size (default: from LoggerConfig)
            backup_count: Number of backup files (default: from LoggerConfig)
        """
        # Use config defaults if not provided
        if log_dir is None:
            self.log_dir = LoggerConfig.get_log_directory()
        else:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(exist_ok=True)
        
        if max_bytes is None:
            max_bytes = LoggerConfig.MAX_LOG_FILE_SIZE
        if backup_count is None:
            backup_count = LoggerConfig.BACKUP_COUNT
        
        # Log filename with date
        log_filename = LoggerConfig.get_log_filepath()
        
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
        file_handler.setLevel(LoggerConfig.FILE_LOG_LEVEL)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LoggerConfig.CONSOLE_LOG_LEVEL)
        
        # Detailed format for file
        file_formatter = logging.Formatter(
            LoggerConfig.FILE_LOG_FORMAT,
            datefmt=LoggerConfig.DATE_FORMAT
        )
        
        # Simple format for console
        console_formatter = logging.Formatter(
            LoggerConfig.CONSOLE_LOG_FORMAT
        )
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Store handlers for level updates
        self.file_handler = file_handler
        self.console_handler = console_handler
        
        # Initial log
        self.logger.info("=" * 80)
        self.logger.info("CAN Analyzer started")
        self.logger.info(f"Log file: {log_filename}")
        self.logger.info(f"File log level: {logging.getLevelName(LoggerConfig.FILE_LOG_LEVEL)}")
        self.logger.info(f"Console log level: {logging.getLevelName(LoggerConfig.CONSOLE_LOG_LEVEL)}")
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
    
    def set_console_level(self, level: int):
        """
        Update console log level dynamically.
        
        Args:
            level: Logging level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.console_handler.setLevel(level)
        level_name = logging.getLevelName(level)
        self.logger.info(f"Console log level changed to: {level_name}")
    
    def set_file_level(self, level: int):
        """
        Update file log level dynamically.
        
        Args:
            level: Logging level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.file_handler.setLevel(level)
        level_name = logging.getLevelName(level)
        self.logger.info(f"File log level changed to: {level_name}")
    
    def get_log_file_path(self) -> str:
        """
        Get the current log file path.
        
        Returns:
            str: Path to current log file
        """
        for handler in self.logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                return handler.baseFilename
        return ""
    
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


# Decorators for error handling

def log_errors(operation_name: str):
    """
    Decorator to automatically log errors in functions
    
    Args:
        operation_name: Name of the operation for logging
        
    Example:
        @log_errors("database connection")
        def connect_to_db():
            # code that might raise exceptions
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = get_logger()
                logger.error(f"Error in {operation_name}: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator


def log_and_suppress_errors(operation_name: str, default_return=None):
    """
    Decorator to log errors and suppress them (return default value)
    
    Args:
        operation_name: Name of the operation for logging
        default_return: Value to return if exception occurs
        
    Example:
        @log_and_suppress_errors("optional feature", default_return=False)
        def optional_feature():
            # code that might fail
            return True
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = get_logger()
                logger.warning(f"Error in {operation_name} (suppressed): {str(e)}")
                return default_return
        return wrapper
    return decorator


def log_execution(operation_name: str, log_args: bool = False):
    """
    Decorator to log function execution (entry and exit)
    
    Args:
        operation_name: Name of the operation for logging
        log_args: Whether to log function arguments
        
    Example:
        @log_execution("file processing", log_args=True)
        def process_file(filename):
            # processing code
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            
            if log_args:
                logger.debug(f"Starting {operation_name} with args={args}, kwargs={kwargs}")
            else:
                logger.debug(f"Starting {operation_name}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Failed {operation_name}: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator
