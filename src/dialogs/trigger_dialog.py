"""
Trigger Dialog - Configure automatic transmission triggers
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QDialogButtonBox, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QWidget, QInputDialog
)
from PyQt6.QtCore import Qt

from ..theme import get_adaptive_colors


class TriggerDialog(QDialog):
    """Dialog to configure automatic transmission triggers"""
    def __init__(self, parent=None, trigger_config=None):
        super().__init__(parent)
        # Accept either old format (list) or new format (dict with enabled + triggers)
        if isinstance(trigger_config, dict):
            self.triggers = trigger_config.get('triggers', [])
            self.triggers_enabled = trigger_config.get('enabled', False)
        else:
            self.triggers = trigger_config or []
            self.triggers_enabled = False
        
        # Get theme from parent's config if available
        theme_pref = 'system'
        if parent and hasattr(parent, 'theme_preference'):
            theme_pref = parent.theme_preference
        self.colors = get_adaptive_colors(theme_pref)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Trigger-based Transmission")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Info
        info_label = QLabel(
            "Configure automatic transmission based on received messages.\n"
            "When a trigger condition is met, the associated message is sent automatically."
        )
        info_label.setStyleSheet(f"{self.colors['info_text'].replace('10px', '11px')}; padding: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Enable triggers
        self.enable_check = QCheckBox("Enable Trigger-based Transmission")
        self.enable_check.setChecked(self.triggers_enabled)
        self.enable_check.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.enable_check)
        
        # Triggers table
        triggers_group = QGroupBox("Configured Triggers")
        triggers_layout = QVBoxLayout()
        
        self.triggers_table = QTableWidget()
        self.triggers_table.setColumnCount(8)
        self.triggers_table.setHorizontalHeaderLabels([
            'Enabled', 'RX Channel', 'Trigger ID', 'Trigger Data', 'TX Channel', 'TX ID', 'TX Data', 'Comment'
        ])
        
        # Ajustar colunas
        header = self.triggers_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 70)   # Enabled
        header.resizeSection(1, 90)   # RX Channel
        header.resizeSection(2, 80)   # Trigger ID
        header.resizeSection(3, 120)  # Trigger Data
        header.resizeSection(4, 90)   # TX Channel
        header.resizeSection(5, 80)   # TX ID
        header.resizeSection(6, 120)  # TX Data
        header.setStretchLastSection(True)  # Comment
        
        # Enable editing on all columns except Enabled (which has a checkbox)
        self.triggers_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
        
        # Connect signal to save changes when cell is edited
        self.triggers_table.itemChanged.connect(self.on_cell_edited)
        
        triggers_layout.addWidget(self.triggers_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("➕ Add Trigger")
        self.btn_add.clicked.connect(self.add_trigger)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("➖ Remove Selected")
        self.btn_remove.clicked.connect(self.remove_trigger)
        btn_layout.addWidget(self.btn_remove)
        
        btn_layout.addStretch()
        triggers_layout.addLayout(btn_layout)
        
        triggers_group.setLayout(triggers_layout)
        layout.addWidget(triggers_group)
        
        # Examples
        examples_group = QGroupBox("Examples")
        examples_layout = QVBoxLayout()
        
        example_text = QLabel(
            "<b>Example 1:</b> When ID 0x280 is received, send ID 0x300<br>"
            "<b>Example 2:</b> When ID 0x284 with byte[0]=0xFF, send ID 0x301<br>"
            "<b>Example 3:</b> Simulate ECU response to diagnostic requests"
        )
        example_text.setStyleSheet(self.colors['info_text'])
        examples_layout.addWidget(example_text)
        
        examples_group.setLayout(examples_layout)
        layout.addWidget(examples_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Connect Apply button
        apply_button = button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button:
            apply_button.clicked.connect(self.apply_triggers)
        
        layout.addWidget(button_box)
        
        # Carregar triggers existentes
        self.load_triggers_to_table()
    
    def load_triggers_to_table(self):
        """Carrega triggers na tabela"""
        # Temporarily disconnect signal to avoid triggering during load
        self.triggers_table.itemChanged.disconnect(self.on_cell_edited)
        
        self.triggers_table.setRowCount(0)
        
        for trigger in self.triggers:
            row = self.triggers_table.rowCount()
            self.triggers_table.insertRow(row)
            
            # Enabled checkbox
            enabled_check = QCheckBox()
            enabled_check.setChecked(trigger.get('enabled', True))
            enabled_widget = QWidget()
            enabled_layout = QHBoxLayout(enabled_widget)
            enabled_layout.addWidget(enabled_check)
            enabled_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            enabled_layout.setContentsMargins(0, 0, 0, 0)
            self.triggers_table.setCellWidget(row, 0, enabled_widget)
            
            # RX Channel
            rx_channel = trigger.get('rx_channel', 'ANY')
            self.triggers_table.setItem(row, 1, QTableWidgetItem(rx_channel))
            
            # Trigger ID
            self.triggers_table.setItem(row, 2, QTableWidgetItem(trigger.get('trigger_id', '0x000')))
            
            # Trigger Data (opcional)
            trigger_data = trigger.get('trigger_data', '')
            self.triggers_table.setItem(row, 3, QTableWidgetItem(trigger_data if trigger_data else 'Any'))
            
            # TX Channel
            tx_channel = trigger.get('tx_channel', 'ALL')
            self.triggers_table.setItem(row, 4, QTableWidgetItem(tx_channel))
            
            # TX ID
            self.triggers_table.setItem(row, 5, QTableWidgetItem(trigger.get('tx_id', '0x000')))
            
            # TX Data
            self.triggers_table.setItem(row, 6, QTableWidgetItem(trigger.get('tx_data', '00 00 00 00 00 00 00 00')))
            
            # Comment
            self.triggers_table.setItem(row, 7, QTableWidgetItem(trigger.get('comment', '')))
        
        # Reconnect signal after loading
        self.triggers_table.itemChanged.connect(self.on_cell_edited)
    
    def add_trigger(self):
        """Adiciona novo trigger"""
        # Get connected channels from parent
        connected_channels = []
        if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
            if self.parent().can_bus_manager.buses:
                # Only list connected buses
                for bus_name, bus_instance in self.parent().can_bus_manager.buses.items():
                    if bus_instance.connected:
                        connected_channels.append(bus_name)
        
        # RX Channel options: ANY or connected channels
        rx_channel_options = ['ANY'] + connected_channels
        if not connected_channels:
            QMessageBox.warning(self, "No Connection", "Please connect to CAN bus first!")
            return
        
        # RX Channel
        rx_channel, ok0 = QInputDialog.getItem(
            self, "Add Trigger", "RX Channel (receive trigger from):",
            rx_channel_options, 0, False
        )
        if not ok0:
            return
        
        # Dialog simples para adicionar trigger
        trigger_id, ok1 = QInputDialog.getText(self, "Add Trigger", "Trigger ID (hex):", text="0x280")
        if not ok1:
            return
        
        # TX Channel options: ALL or connected channels
        tx_channel_options = ['ALL'] + connected_channels
        tx_channel, ok1_5 = QInputDialog.getItem(
            self, "Add Trigger", "TX Channel (send message to):",
            tx_channel_options, 0, False
        )
        if not ok1_5:
            return
        
        tx_id, ok2 = QInputDialog.getText(self, "Add Trigger", "TX ID (hex):", text="0x300")
        if not ok2:
            return
        
        tx_data, ok3 = QInputDialog.getText(self, "Add Trigger", "TX Data (hex):", text="00 00 00 00 00 00 00 00")
        if not ok3:
            return
        
        comment, ok4 = QInputDialog.getText(self, "Add Trigger", "Comment (optional):")
        
        # Add to list
        new_trigger = {
            'enabled': True,
            'rx_channel': rx_channel,
            'trigger_id': trigger_id,
            'trigger_data': '',  # Any data
            'tx_channel': tx_channel,
            'tx_id': tx_id,
            'tx_data': tx_data,
            'comment': comment if ok4 else ''
        }
        
        self.triggers.append(new_trigger)
        self.load_triggers_to_table()
    
    def on_cell_edited(self, item):
        """Called when a cell is edited - updates the internal triggers list"""
        if not item:
            return
        
        row = item.row()
        col = item.column()
        
        # Update the triggers list based on current table content
        # This will be done automatically when get_triggers() is called
        # No need to do anything here, just let the user edit
        pass
    
    def remove_trigger(self):
        """Remove trigger selecionado"""
        current_row = self.triggers_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Remove Trigger", "Select a trigger to remove!")
            return
        
        reply = QMessageBox.question(
            self,
            "Remove Trigger",
            "Are you sure you want to remove this trigger?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.triggers.pop(current_row)
            self.load_triggers_to_table()
    
    def apply_triggers(self):
        """Apply triggers without closing dialog"""
        if self.parent():
            trigger_config = self.get_triggers()
            self.parent().triggers_enabled = trigger_config['enabled']
            self.parent().triggers = trigger_config['triggers']
            
            if trigger_config['enabled']:
                self.parent().show_notification(
                    f"⚡ Triggers aplicados: {len(trigger_config['triggers'])} configurado(s)",
                    2000
                )
            else:
                self.parent().show_notification("Triggers desativados", 2000)
    
    def get_triggers(self):
        """Retorna lista de triggers configurados"""
        triggers = []
        
        for row in range(self.triggers_table.rowCount()):
            # Get enabled state
            enabled_widget = self.triggers_table.cellWidget(row, 0)
            enabled_check = enabled_widget.findChild(QCheckBox)
            enabled = enabled_check.isChecked() if enabled_check else True
            
            trigger = {
                'enabled': enabled,
                'rx_channel': self.triggers_table.item(row, 1).text() if self.triggers_table.item(row, 1) else 'ANY',
                'trigger_id': self.triggers_table.item(row, 2).text(),
                'trigger_data': self.triggers_table.item(row, 3).text(),
                'tx_channel': self.triggers_table.item(row, 4).text() if self.triggers_table.item(row, 4) else 'ALL',
                'tx_id': self.triggers_table.item(row, 5).text(),
                'tx_data': self.triggers_table.item(row, 6).text(),
                'comment': self.triggers_table.item(row, 7).text() if self.triggers_table.item(row, 7) else ''
            }
            triggers.append(trigger)
        
        return {
            'enabled': self.enable_check.isChecked(),
            'triggers': triggers
        }
