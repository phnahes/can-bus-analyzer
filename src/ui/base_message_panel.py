"""
Base Message Panel

Base class for message display panels (Tracer and Monitor).
Extracts common functionality to reduce code duplication.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QPushButton, QLabel, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from typing import Optional


class BaseMessagePanel(QWidget):
    """Base class for message panels with common functionality"""
    
    def __init__(self, parent=None):
        """
        Initialize base message panel
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.parent_window = parent
        self.table: Optional[QTableWidget] = None
        self.status_label: Optional[QLabel] = None
    
    def _create_base_layout(self) -> QVBoxLayout:
        """
        Create base layout structure
        
        Returns:
            QVBoxLayout for the panel
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        return layout
    
    def _create_table(self, columns: list, column_widths: dict = None, 
                      context_menu_callback=None) -> QTableWidget:
        """
        Create table widget with specified columns
        
        Args:
            columns: List of column headers
            column_widths: Optional dict mapping column index to width
            context_menu_callback: Optional callback for context menu
            
        Returns:
            Configured QTableWidget
        """
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        
        # Set font (increased to 14 for better readability)
        font = QFont("Courier New", 14)
        table.setFont(font)
        
        # Configure header
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Apply custom widths if provided
        if column_widths:
            for col_idx, width in column_widths.items():
                if width == 'stretch':
                    header.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Stretch)
                else:
                    header.resizeSection(col_idx, width)
        
        # Hide vertical header (row numbers)
        table.verticalHeader().setVisible(False)
        
        # Enable row selection
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Configure context menu if callback provided
        if context_menu_callback:
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(context_menu_callback)
        
        return table
    
    def _create_control_button(self, text: str, checkable: bool = False, 
                               tooltip: str = "") -> QPushButton:
        """
        Create a control button
        
        Args:
            text: Button text
            checkable: Whether button is checkable
            tooltip: Optional tooltip text
            
        Returns:
            QPushButton
        """
        button = QPushButton(text)
        button.setCheckable(checkable)
        if tooltip:
            button.setToolTip(tooltip)
        return button
    
    def _create_status_label(self, initial_text: str = "Ready") -> QLabel:
        """
        Create status label
        
        Args:
            initial_text: Initial label text
            
        Returns:
            QLabel
        """
        label = QLabel(initial_text)
        return label
    
    def clear(self):
        """Clear all messages from the table"""
        if self.table:
            self.table.setRowCount(0)
    
    def get_message_count(self) -> int:
        """
        Get number of messages in table
        
        Returns:
            Row count
        """
        if self.table:
            return self.table.rowCount()
        return 0
    
    def update_status(self, text: str):
        """
        Update status label
        
        Args:
            text: Status text
        """
        if self.status_label:
            self.status_label.setText(text)
    
    def highlight_row(self, row: int, color: QColor):
        """
        Highlight a table row
        
        Args:
            row: Row index
            color: Background color
        """
        if not self.table:
            return
        
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(color)
    
    def scroll_to_bottom(self):
        """Scroll table to bottom"""
        if self.table:
            self.table.scrollToBottom()
    
    def scroll_to_top(self):
        """Scroll table to top"""
        if self.table:
            self.table.scrollToTop()
