"""
Split Screen Manager

Manages split-screen view for multi-CAN monitoring.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import (
    QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QDialogButtonBox, QGroupBox, 
    QTableWidget, QSplitter
)
from PyQt6.QtCore import Qt
from typing import Optional, Tuple


class SplitScreenManager:
    """Manages split-screen view functionality"""
    
    def __init__(self, parent_window, logger):
        """
        Initialize split screen manager
        
        Args:
            parent_window: Main window instance
            logger: Logger instance
        """
        self.parent = parent_window
        self.logger = logger
        self.is_active = False
        self.left_channel = None
        self.right_channel = None
        self.table_left = None
        self.table_right = None
    
    def show_channel_selection_dialog(self, bus_names: list) -> Optional[Tuple[str, str]]:
        """
        Show channel selection dialog for split-screen
        
        Args:
            bus_names: List of available bus names
            
        Returns:
            Tuple of (left_channel, right_channel) or None if cancelled
        """
        from ..i18n import t
        
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(t('split_screen_mode'))
        layout = QVBoxLayout(dialog)
        
        # Left panel channel
        left_layout = QHBoxLayout()
        left_layout.addWidget(QLabel(t('split_screen_left') + ":"))
        left_combo = QComboBox()
        for bus in bus_names:
            left_combo.addItem(bus)
        left_layout.addWidget(left_combo)
        layout.addLayout(left_layout)
        
        # Right panel channel
        right_layout = QHBoxLayout()
        right_layout.addWidget(QLabel(t('split_screen_right') + ":"))
        right_combo = QComboBox()
        for bus in bus_names:
            right_combo.addItem(bus)
        if len(bus_names) > 1:
            right_combo.setCurrentIndex(1)
        right_layout.addWidget(right_combo)
        layout.addLayout(right_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return (left_combo.currentText(), right_combo.currentText())
        
        return None
    
    def toggle(self, can_bus_manager) -> bool:
        """
        Toggle split-screen mode
        
        Args:
            can_bus_manager: CAN bus manager instance
            
        Returns:
            True if split-screen is now active, False otherwise
        """
        from ..i18n import t
        
        self.is_active = not self.is_active
        
        if self.is_active:
            # Enable split-screen
            if not can_bus_manager or len(can_bus_manager.get_bus_names()) < 2:
                QMessageBox.warning(
                    self.parent,
                    t('warning'),
                    "Split-screen mode requires at least 2 CAN buses.\n"
                    "Please configure multiple CAN buses in Settings first."
                )
                self.is_active = False
                return False
            
            # Show channel selection dialog
            bus_names = can_bus_manager.get_bus_names()
            result = self.show_channel_selection_dialog(bus_names)
            
            if result:
                self.left_channel, self.right_channel = result
                self.logger.info(f"Split-screen enabled: {self.left_channel} | {self.right_channel}")
                return True
            else:
                self.is_active = False
                return False
        else:
            # Disable split-screen
            self.logger.info("Split-screen disabled")
            self.left_channel = None
            self.right_channel = None
            self.table_left = None
            self.table_right = None
            return False
    
    def setup_view(self, receive_container_layout, setup_table_callback) -> Tuple[QTableWidget, QTableWidget]:
        """
        Setup split-screen view with two tables
        
        Args:
            receive_container_layout: Container layout for receive panel
            setup_table_callback: Callback to setup table widget
            
        Returns:
            Tuple of (left_table, right_table)
        """
        # Clear existing layout
        while receive_container_layout.count():
            item = receive_container_layout.takeAt(0)
            if item.widget():
                item.widget().setVisible(False)
        
        # Create horizontal splitter for two tables
        split_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel
        left_panel = QGroupBox(f"Channel: {self.left_channel}")
        left_layout = QVBoxLayout(left_panel)
        
        self.table_left = QTableWidget()
        setup_table_callback(self.table_left)
        left_layout.addWidget(self.table_left)
        
        # Right panel
        right_panel = QGroupBox(f"Channel: {self.right_channel}")
        right_layout = QVBoxLayout(right_panel)
        
        self.table_right = QTableWidget()
        setup_table_callback(self.table_right)
        right_layout.addWidget(self.table_right)
        
        # Add panels to splitter
        split_splitter.addWidget(left_panel)
        split_splitter.addWidget(right_panel)
        split_splitter.setSizes([500, 500])  # Equal split
        
        # Add splitter to container
        receive_container_layout.addWidget(split_splitter)
        
        return self.table_left, self.table_right
    
    def teardown_view(self, receive_container_layout, main_receive_table):
        """
        Teardown split-screen view and restore single view
        
        Args:
            receive_container_layout: Container layout for receive panel
            main_receive_table: Main receive table widget
        """
        # Clear existing layout
        while receive_container_layout.count():
            item = receive_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Restore main receive table
        main_receive_table.setVisible(True)
        receive_container_layout.addWidget(main_receive_table)
        
        self.table_left = None
        self.table_right = None
    
    def get_table_for_channel(self, channel: str) -> Optional[QTableWidget]:
        """
        Get table widget for a specific channel
        
        Args:
            channel: Channel name
            
        Returns:
            Table widget or None
        """
        if channel == self.left_channel:
            return self.table_left
        elif channel == self.right_channel:
            return self.table_right
        return None
