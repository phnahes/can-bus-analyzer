"""
Message Box Helper

Utility functions for common message box patterns.
Reduces code duplication across the application.
"""

from PyQt6.QtWidgets import QMessageBox
from typing import Optional


class MessageBoxHelper:
    """Helper class for common message box operations"""
    
    @staticmethod
    def show_warning(parent, title: str, message: str):
        """
        Show warning message box
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Warning message
        """
        QMessageBox.warning(parent, title, message)
    
    @staticmethod
    def show_error(parent, title: str, message: str):
        """
        Show error message box
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Error message
        """
        QMessageBox.critical(parent, title, message)
    
    @staticmethod
    def show_error_exception(parent, title: str, error: Exception):
        """
        Show error message box from exception
        
        Args:
            parent: Parent widget
            title: Dialog title
            error: Exception object
        """
        QMessageBox.critical(parent, title, f"Error: {str(error)}")
    
    @staticmethod
    def show_info(parent, title: str, message: str):
        """
        Show information message box
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Information message
        """
        QMessageBox.information(parent, title, message)
    
    @staticmethod
    def ask_yes_no(parent, title: str, question: str) -> bool:
        """
        Ask yes/no question
        
        Args:
            parent: Parent widget
            title: Dialog title
            question: Question to ask
            
        Returns:
            True if Yes was clicked, False otherwise
        """
        reply = QMessageBox.question(
            parent,
            title,
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    @staticmethod
    def ask_yes_no_cancel(parent, title: str, question: str) -> Optional[bool]:
        """
        Ask yes/no/cancel question
        
        Args:
            parent: Parent widget
            title: Dialog title
            question: Question to ask
            
        Returns:
            True if Yes, False if No, None if Cancel
        """
        reply = QMessageBox.question(
            parent,
            title,
            question,
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No | 
            QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            return True
        elif reply == QMessageBox.StandardButton.No:
            return False
        else:
            return None
    
    @staticmethod
    def ask_confirmation(parent, title: str, message: str, 
                        yes_text: str = "Yes", no_text: str = "No") -> bool:
        """
        Ask for confirmation with custom button text
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Confirmation message
            yes_text: Text for yes button
            no_text: Text for no button
            
        Returns:
            True if confirmed, False otherwise
        """
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        yes_button = msg_box.button(QMessageBox.StandardButton.Yes)
        yes_button.setText(yes_text)
        
        no_button = msg_box.button(QMessageBox.StandardButton.No)
        no_button.setText(no_text)
        
        return msg_box.exec() == QMessageBox.StandardButton.Yes
