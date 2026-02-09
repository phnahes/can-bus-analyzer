"""
Status Bar Builder
Builds the status bar with connection and message counters
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt


class StatusBarBuilder:
    """Builds the status bar"""
    
    @staticmethod
    def create_status_bar(parent) -> QHBoxLayout:
        """Create status bar with connection and message counters
        
        Args:
            parent: The parent window (main_window)
            
        Returns:
            QHBoxLayout: The status bar layout
        """
        status_layout = QHBoxLayout()
        
        # Single consolidated status label
        # Format: CAN1: 500k, /dev/cu..., Normal, Connected | CAN2: ... | Filter: Off | Trigger: Off | Messages: 0
        parent.connection_status = QLabel("Not Connected")
        status_layout.addWidget(parent.connection_status)
        
        # Keep these for backward compatibility (hidden or used internally)
        parent.device_label = QLabel()
        parent.device_label.setVisible(False)
        
        parent.mode_label = QLabel()
        parent.mode_label.setVisible(False)
        
        parent.filter_status_label = QLabel("Filter: Off")
        parent.filter_status_label.setVisible(False)
        
        parent.msg_count_label = QLabel("Messages: 0")
        parent.msg_count_label.setVisible(False)
        
        status_layout.addStretch()
        
        # Notification label (right-aligned)
        parent.notification_label = QLabel("")
        parent.notification_label.setStyleSheet(parent.colors['notification'])
        parent.notification_label.setWordWrap(True)
        parent.notification_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        parent.notification_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        status_layout.addWidget(parent.notification_label)
        
        return status_layout
