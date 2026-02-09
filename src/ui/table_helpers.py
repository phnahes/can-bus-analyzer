"""
Table Helpers - Utility functions for table creation
Extracted from main_window.py to reduce code duplication
"""
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt


def create_centered_item(text: str, user_data=None) -> QTableWidgetItem:
    """
    Create a centered table item
    
    Args:
        text: Text to display
        user_data: Optional user data to store
        
    Returns:
        QTableWidgetItem with centered alignment
    """
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    if user_data is not None:
        item.setData(Qt.ItemDataRole.UserRole, user_data)
    return item


def create_left_aligned_item(text: str, user_data=None) -> QTableWidgetItem:
    """
    Create a left-aligned table item
    
    Args:
        text: Text to display
        user_data: Optional user data to store
        
    Returns:
        QTableWidgetItem with left alignment
    """
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    if user_data is not None:
        item.setData(Qt.ItemDataRole.UserRole, user_data)
    return item


def create_right_aligned_item(text: str, user_data=None) -> QTableWidgetItem:
    """
    Create a right-aligned table item
    
    Args:
        text: Text to display
        user_data: Optional user data to store
        
    Returns:
        QTableWidgetItem with right alignment
    """
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if user_data is not None:
        item.setData(Qt.ItemDataRole.UserRole, user_data)
    return item


def format_can_id(can_id: int, extended: bool = False) -> str:
    """
    Format CAN ID as hex string
    
    Args:
        can_id: CAN ID value
        extended: True for 29-bit extended ID
        
    Returns:
        Formatted hex string
    """
    if extended:
        return f"0x{can_id:08X}"
    else:
        return f"0x{can_id:03X}"


def format_data_bytes(data: bytes) -> str:
    """
    Format data bytes as hex string
    
    Args:
        data: Data bytes
        
    Returns:
        Space-separated hex string
    """
    return " ".join([f"{b:02X}" for b in data])


def format_ascii(data: bytes) -> str:
    """
    Format data bytes as ASCII string (printable only)
    
    Args:
        data: Data bytes
        
    Returns:
        ASCII string with non-printable chars as dots
    """
    return "".join([chr(b) if 32 <= b < 127 else "." for b in data])


def set_centered_item(table, row: int, col: int, text: str):
    """
    Create and set a centered table item
    
    Args:
        table: QTableWidget instance
        row: Row index
        col: Column index
        text: Text to display
    """
    table.setItem(row, col, create_centered_item(text))


def set_left_aligned_item(table, row: int, col: int, text: str):
    """
    Create and set a left-aligned table item
    
    Args:
        table: QTableWidget instance
        row: Row index
        col: Column index
        text: Text to display
    """
    table.setItem(row, col, create_left_aligned_item(text))


def set_right_aligned_item(table, row: int, col: int, text: str):
    """
    Create and set a right-aligned table item
    
    Args:
        table: QTableWidget instance
        row: Row index
        col: Column index
        text: Text to display
    """
    table.setItem(row, col, create_right_aligned_item(text))
