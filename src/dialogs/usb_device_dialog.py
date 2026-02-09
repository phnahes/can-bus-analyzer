"""
USB Device Selection Dialog - Select USB/Serial device
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt

from ..i18n import t
from ..usb_device_monitor import USBDeviceInfo


class USBDeviceSelectionDialog(QDialog):
    """Dialog for USB/Serial device selection"""
    
    def __init__(self, parent=None, usb_monitor=None):
        super().__init__(parent)
        self.usb_monitor = usb_monitor
        self.selected_device = None
        self.init_ui()
        self.refresh_devices()
    
    def init_ui(self):
        self.setWindowTitle(t('dialog_usb_device_title'))
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Information
        info_label = QLabel(t('dialog_usb_device_info'))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Tabela de dispositivos
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(3)
        self.devices_table.setHorizontalHeaderLabels([
            t('label_device_name'),
            t('label_device_path'),
            t('label_device_description')
        ])
        self.devices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.devices_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.devices_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.devices_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.devices_table.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.devices_table)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton(t('btn_refresh'))
        self.refresh_btn.clicked.connect(self.refresh_devices)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.select_btn = QPushButton(t('btn_select'))
        self.select_btn.clicked.connect(self.accept)
        self.select_btn.setEnabled(False)
        button_layout.addWidget(self.select_btn)
        
        self.cancel_btn = QPushButton(t('btn_cancel'))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Connect selection signal
        self.devices_table.itemSelectionChanged.connect(self.on_selection_changed)
    
    def refresh_devices(self):
        """Atualiza a lista de dispositivos"""
        self.devices_table.setRowCount(0)
        
        if not self.usb_monitor:
            self.status_label.setText(t('msg_usb_monitor_not_available'))
            return
        
        # Get available devices
        devices = self.usb_monitor.get_available_devices()
        
        if not devices:
            self.status_label.setText(t('msg_no_usb_devices_found'))
            return
        
        # Preencher tabela
        self.devices_table.setRowCount(len(devices))
        for row, device in enumerate(devices):
            # Nome
            name_item = QTableWidgetItem(device.name)
            self.devices_table.setItem(row, 0, name_item)
            
            # Caminho
            path_item = QTableWidgetItem(device.path)
            self.devices_table.setItem(row, 1, path_item)
            
            # Description
            desc_item = QTableWidgetItem(device.description)
            self.devices_table.setItem(row, 2, desc_item)
        
        self.status_label.setText(t('msg_usb_devices_found').format(count=len(devices)))
    
    def on_selection_changed(self):
        """Callback when selection changes"""
        has_selection = len(self.devices_table.selectedItems()) > 0
        self.select_btn.setEnabled(has_selection)
    
    def get_selected_device(self):
        """Retorna o dispositivo selecionado"""
        selected_rows = self.devices_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        path = self.devices_table.item(row, 1).text()
        name = self.devices_table.item(row, 0).text()
        
        # Criar objeto de dispositivo
        return USBDeviceInfo(path, name)
    
    def accept(self):
        """Accept the selection"""
        self.selected_device = self.get_selected_device()
        if self.selected_device:
            super().accept()
        else:
            QMessageBox.warning(self, t('warning'), t('msg_select_device'))
