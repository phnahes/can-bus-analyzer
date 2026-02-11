"""
Logger Configuration

Centralizes logging configuration settings for the CAN Analyzer application.
This file defines log levels, file paths, rotation settings, and formatting options.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any


class LoggerConfig:
    """Configuration for the application logger"""
    
    # Default log directory (relative to project root)
    DEFAULT_LOG_DIR = "logs"
    
    # Log file settings
    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5  # Number of backup log files to keep
    
    # Log levels
    FILE_LOG_LEVEL = logging.INFO      # Level for file logs
    CONSOLE_LOG_LEVEL = logging.INFO    # Level for console output
    
    # Log format strings
    FILE_LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
    CONSOLE_LOG_FORMAT = '%(levelname)s: %(message)s'
    
    # Date format
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Log filename pattern
    LOG_FILENAME_PATTERN = 'can_analyzer_{date}.log'
    
    @classmethod
    def get_log_directory(cls) -> Path:
        """
        Get the log directory path, creating it if necessary.
        
        Returns:
            Path: Absolute path to log directory
        """
        log_dir = Path(cls.DEFAULT_LOG_DIR)
        log_dir.mkdir(exist_ok=True)
        return log_dir
    
    @classmethod
    def get_log_filepath(cls, date_str: str = None) -> Path:
        """
        Get the full path for a log file.
        
        Args:
            date_str: Date string in format YYYYMMDD (default: today)
        
        Returns:
            Path: Full path to log file
        """
        if date_str is None:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
        
        filename = cls.LOG_FILENAME_PATTERN.format(date=date_str)
        return cls.get_log_directory() / filename
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """
        Get logger configuration as a dictionary.
        
        Returns:
            Dict with all logger configuration settings
        """
        return {
            'log_dir': str(cls.get_log_directory()),
            'max_bytes': cls.MAX_LOG_FILE_SIZE,
            'backup_count': cls.BACKUP_COUNT,
            'file_level': cls.FILE_LOG_LEVEL,
            'console_level': cls.CONSOLE_LOG_LEVEL,
            'file_format': cls.FILE_LOG_FORMAT,
            'console_format': cls.CONSOLE_LOG_FORMAT,
            'date_format': cls.DATE_FORMAT
        }
    
    @classmethod
    def set_console_level(cls, level: int):
        """
        Set console log level.
        
        Args:
            level: Logging level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        cls.CONSOLE_LOG_LEVEL = level
    
    @classmethod
    def set_file_level(cls, level: int):
        """
        Set file log level.
        
        Args:
            level: Logging level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        cls.FILE_LOG_LEVEL = level
    
    @classmethod
    def set_log_directory(cls, directory: str):
        """
        Set custom log directory.
        
        Args:
            directory: Path to log directory
        """
        cls.DEFAULT_LOG_DIR = directory


# Predefined log level configurations

LOG_LEVELS = {
    'DEBUG': logging.DEBUG,      # Detailed information for diagnosing problems
    'INFO': logging.INFO,        # General informational messages
    'WARNING': logging.WARNING,  # Warning messages
    'ERROR': logging.ERROR,      # Error messages
    'CRITICAL': logging.CRITICAL # Critical error messages
}


def get_log_level_name(level: int) -> str:
    """
    Get the name of a log level.
    
    Args:
        level: Logging level constant
    
    Returns:
        str: Level name (e.g., 'DEBUG', 'INFO')
    """
    for name, value in LOG_LEVELS.items():
        if value == level:
            return name
    return 'UNKNOWN'


def get_log_level_from_name(name: str) -> int:
    """
    Get log level constant from name.
    
    Args:
        name: Level name (e.g., 'DEBUG', 'INFO')
    
    Returns:
        int: Logging level constant
    """
    return LOG_LEVELS.get(name.upper(), logging.INFO)


# Export for easy access
__all__ = [
    'LoggerConfig',
    'LOG_LEVELS',
    'get_log_level_name',
    'get_log_level_from_name'
]
