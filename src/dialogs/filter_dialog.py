"""
Filter Dialog - Configure message filters
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QDialogButtonBox, QWidget
)
from PyQt6.QtCore import Qt

from ..theme import get_adaptive_colors
from ..i18n import t


class FilterDialog(QDialog):
    """Dialog para configurar filtros de mensagens"""
    def __init__(self, parent=None, current_filters=None):
        super().__init__(parent)
        self.current_filters = current_filters or {
            'enabled': False,
            'id_filters': [],
            'data_filters': [],
            'show_only': True
        }
        # Get theme from parent's config if available
        self.theme_pref = 'system'
        if parent and hasattr(parent, 'theme_preference'):
            self.theme_pref = parent.theme_preference
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Message Filters")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Enable/Disable filters
        self.enable_check = QCheckBox("Enable Filters")
        self.enable_check.setChecked(self.current_filters.get('enabled', False))
        self.enable_check.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.enable_check)
        
        # Channel-specific ID Filters
        colors = get_adaptive_colors(self.theme_pref)
        channel_group = QGroupBox("Channel ID Filters")
        channel_layout = QVBoxLayout()
        
        channel_help = QLabel("Filter CAN IDs per channel. Use Whitelist/Blacklist toggle for each channel.\nExample: 0x280, 0x284, 0x300-0x310")
        channel_help.setStyleSheet(colors['info_text'])
        channel_layout.addWidget(channel_help)
        
        # Table for channel filters
        self.channel_filter_table = QTableWidget()
        self.channel_filter_table.setColumnCount(3)
        self.channel_filter_table.setHorizontalHeaderLabels(['Channel', 'IDs (hex)', 'Mode'])
        self.channel_filter_table.horizontalHeader().setStretchLastSection(False)
        self.channel_filter_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.channel_filter_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.channel_filter_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.channel_filter_table.setColumnWidth(0, 100)
        self.channel_filter_table.setColumnWidth(2, 120)
        self.channel_filter_table.setMaximumHeight(250)
        channel_layout.addWidget(self.channel_filter_table)
        
        # Get available channels from parent
        self.channel_filter_inputs = {}
        available_channels = ['ALL']  # ALL = applies to all channels
        parent_window = self.parent()
        if parent_window and hasattr(parent_window, 'can_bus_manager'):
            can_bus_mgr = parent_window.can_bus_manager
            if can_bus_mgr:
                available_channels.extend(can_bus_mgr.get_bus_names())
        
        # Populate table with channels
        self.channel_filter_table.setRowCount(len(available_channels))
        channel_filters = self.current_filters.get('channel_filters', {})
        
        for row, channel in enumerate(available_channels):
            # Channel name (read-only)
            channel_item = QTableWidgetItem(channel)
            channel_item.setFlags(channel_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_filter_table.setItem(row, 0, channel_item)
            
            # IDs input (editable)
            ids_text = ""
            if channel in channel_filters:
                channel_ids = channel_filters[channel].get('ids', [])
                if channel_ids:
                    ids_text = ", ".join([f"0x{id:03X}" for id in channel_ids])
            ids_item = QTableWidgetItem(ids_text)
            self.channel_filter_table.setItem(row, 1, ids_item)
            
            # Mode toggle button (Whitelist/Blacklist)
            mode_widget = QWidget()
            mode_layout = QHBoxLayout(mode_widget)
            mode_layout.setContentsMargins(5, 0, 5, 0)
            
            mode_btn = QPushButton()
            # Default to Whitelist (show_only = True)
            is_whitelist = True
            if channel in channel_filters:
                is_whitelist = channel_filters[channel].get('show_only', True)
            
            mode_btn.setText("Whitelist" if is_whitelist else "Blacklist")
            mode_btn.setCheckable(True)
            mode_btn.setChecked(not is_whitelist)  # checked = blacklist
            mode_btn.setStyleSheet("""
                QPushButton { min-width: 100px; }
                QPushButton:checked { background-color: #d9534f; color: white; }
            """)
            mode_btn.clicked.connect(lambda checked, btn=mode_btn: 
                btn.setText("Blacklist" if checked else "Whitelist"))
            
            mode_layout.addWidget(mode_btn)
            self.channel_filter_table.setCellWidget(row, 2, mode_widget)
            
            self.channel_filter_inputs[channel] = {'row': row, 'mode_btn': mode_btn}
        
        channel_group.setLayout(channel_layout)
        layout.addWidget(channel_group)
        
        # Data Filters
        data_group = QGroupBox("Data Filters (Advanced)")
        data_layout = QVBoxLayout()
        
        data_help = QLabel("Filter by data content (hex)\nExample: Byte 0 = FF, Byte 2 = 00")
        data_help.setStyleSheet(colors['info_text'])
        data_layout.addWidget(data_help)
        
        self.data_filter_table = QTableWidget()
        self.data_filter_table.setColumnCount(3)
        self.data_filter_table.setHorizontalHeaderLabels(['Byte Index', 'Value (Hex)', 'Mask (Hex)'])
        self.data_filter_table.setMaximumHeight(150)
        data_layout.addWidget(self.data_filter_table)
        
        data_btn_layout = QHBoxLayout()
        self.btn_add_data_filter = QPushButton("+ Add Data Filter")
        self.btn_add_data_filter.clicked.connect(self.add_data_filter_row)
        data_btn_layout.addWidget(self.btn_add_data_filter)
        
        self.btn_remove_data_filter = QPushButton("- Remove Selected")
        self.btn_remove_data_filter.clicked.connect(self.remove_data_filter_row)
        data_btn_layout.addWidget(self.btn_remove_data_filter)
        data_btn_layout.addStretch()
        data_layout.addLayout(data_btn_layout)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # Quick filters
        quick_group = QGroupBox("Quick Filters")
        quick_layout = QHBoxLayout()
        
        self.btn_clear_filters = QPushButton("🗑 Clear All")
        self.btn_clear_filters.clicked.connect(self.clear_all_filters)
        quick_layout.addWidget(self.btn_clear_filters)
        
        quick_layout.addStretch()
        quick_group.setLayout(quick_layout)
        layout.addWidget(quick_group)
        
        layout.addStretch()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_filters)
        layout.addWidget(button_box)
        
        # Carregar filtros de dados existentes
        for data_filter in self.current_filters.get('data_filters', []):
            self.add_data_filter_row(data_filter)
    
    def add_data_filter_row(self, data=None):
        """Adiciona linha para filtro de dados"""
        row = self.data_filter_table.rowCount()
        self.data_filter_table.insertRow(row)
        
        if data:
            self.data_filter_table.setItem(row, 0, QTableWidgetItem(str(data.get('byte_index', 0))))
            self.data_filter_table.setItem(row, 1, QTableWidgetItem(data.get('value', 'FF')))
            self.data_filter_table.setItem(row, 2, QTableWidgetItem(data.get('mask', 'FF')))
        else:
            self.data_filter_table.setItem(row, 0, QTableWidgetItem("0"))
            self.data_filter_table.setItem(row, 1, QTableWidgetItem("FF"))
            self.data_filter_table.setItem(row, 2, QTableWidgetItem("FF"))
    
    def remove_data_filter_row(self):
        """Remove linha selecionada"""
        current_row = self.data_filter_table.currentRow()
        if current_row >= 0:
            self.data_filter_table.removeRow(current_row)
    
    def clear_all_filters(self):
        """Limpa todos os filtros"""
        # Clear channel filters
        for row in range(self.channel_filter_table.rowCount()):
            ids_item = self.channel_filter_table.item(row, 1)
            if ids_item:
                ids_item.setText("")
        
        # Clear data filters
        self.data_filter_table.setRowCount(0)
        self.enable_check.setChecked(False)
    
    def apply_filters(self):
        """Aplica filtros sem fechar dialog"""
        # Get current filters
        filters = self.get_filters()
        
        # Apply to parent window
        parent_window = self.parent()
        if parent_window and hasattr(parent_window, 'message_filters'):
            parent_window.message_filters = filters
            parent_window.apply_message_filters()
            
            # Show notification
            if filters['enabled']:
                filter_count = len(filters['id_filters'])
                parent_window.show_notification(
                    t('notif_filters_enabled', count=filter_count),
                    3000
                )
            else:
                parent_window.show_notification(t('notif_filters_disabled'), 2000)
    
    def get_filters(self):
        """Return filter configuration"""
        # Parse channel-specific filters from table
        channel_filters = {}
        for row in range(self.channel_filter_table.rowCount()):
            channel_item = self.channel_filter_table.item(row, 0)
            ids_item = self.channel_filter_table.item(row, 1)
            
            if not channel_item or not ids_item:
                continue
            
            channel = channel_item.text()
            ids_text = ids_item.text().strip()
            
            if not ids_text:
                continue
            
            # Parse IDs
            channel_ids = []
            parts = ids_text.replace(',', ' ').split()
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Range: 0x300-0x310
                    try:
                        start, end = part.split('-')
                        start_id = int(start.strip(), 16)
                        end_id = int(end.strip(), 16)
                        channel_ids.extend(range(start_id, end_id + 1))
                    except:
                        pass
                else:
                    # Single ID
                    try:
                        channel_ids.append(int(part, 16))
                    except:
                        pass
            
            if channel_ids:
                # Get mode from button
                mode_btn = self.channel_filter_inputs[channel]['mode_btn']
                is_blacklist = mode_btn.isChecked()
                
                channel_filters[channel] = {
                    'ids': channel_ids,
                    'show_only': not is_blacklist  # Inverted: checked = blacklist, unchecked = whitelist
                }
        
        # Parse data filters
        data_filters = []
        for row in range(self.data_filter_table.rowCount()):
            try:
                byte_index = int(self.data_filter_table.item(row, 0).text())
                value = self.data_filter_table.item(row, 1).text()
                mask = self.data_filter_table.item(row, 2).text()
                data_filters.append({
                    'byte_index': byte_index,
                    'value': value,
                    'mask': mask
                })
            except:
                pass
        
        return {
            'enabled': self.enable_check.isChecked(),
            'id_filters': [],  # No longer used (kept for compatibility)
            'data_filters': data_filters,
            'show_only': True,  # No longer used (kept for compatibility)
            'channel_filters': channel_filters
        }
