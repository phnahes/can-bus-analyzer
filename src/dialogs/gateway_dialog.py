"""
Gateway Dialog - CAN Gateway configuration
"""

import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QDialogButtonBox, QWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt

from ..models import GatewayConfig, GatewayBlockRule, GatewayDynamicBlock, GatewayModifyRule, GatewayRoute
from ..i18n import get_i18n, t
from ..theme import get_adaptive_colors

from .modify_rule_dialog import ModifyRuleDialog


class GatewayDialog(QDialog):
    """CAN Gateway configuration dialog"""
    def __init__(self, parent=None, config=None, bus_names=None):
        super().__init__(parent)
        self.config = config or GatewayConfig()
        self.bus_names = bus_names or ["CAN1", "CAN2"]
        self.i18n = get_i18n()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(t('gateway_title'))
        self.setModal(True)
        self.setMinimumWidth(900)
        self.setMinimumHeight(750)
        
        layout = QVBoxLayout(self)
        
        # Get theme preference
        colors = get_adaptive_colors('system')
        
        # ===== Transmission Control =====
        transmission_group = QGroupBox(t('gateway_transmission'))
        transmission_layout = QVBoxLayout()
        
        # Enable Gateway
        self.enable_gateway_check = QCheckBox(t('gateway_enable'))
        self.enable_gateway_check.setChecked(self.config.enabled)
        transmission_layout.addWidget(self.enable_gateway_check)
        
        # Route selection - simple horizontal layout
        route_layout = QHBoxLayout()
        
        route_layout.addWidget(QLabel(t('gateway_from') + ":"))
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(100)
        for bus_name in self.bus_names:
            self.source_combo.addItem(bus_name)
        route_layout.addWidget(self.source_combo)
        
        route_layout.addWidget(QLabel("→"))
        
        route_layout.addWidget(QLabel(t('gateway_to') + ":"))
        self.dest_combo = QComboBox()
        self.dest_combo.setMinimumWidth(100)
        for bus_name in self.bus_names:
            self.dest_combo.addItem(bus_name)
        if len(self.bus_names) > 1:
            self.dest_combo.setCurrentIndex(1)  # Default to second bus
        route_layout.addWidget(self.dest_combo)
        
        self.add_route_btn = QPushButton("➕ " + t('btn_add_route'))
        self.add_route_btn.clicked.connect(self.add_route)
        route_layout.addWidget(self.add_route_btn)
        
        self.remove_route_btn = QPushButton("➖ " + t('btn_remove'))
        self.remove_route_btn.clicked.connect(self.remove_route)
        route_layout.addWidget(self.remove_route_btn)
        
        route_layout.addStretch()
        transmission_layout.addLayout(route_layout)
        
        # Routes table
        self.routes_table = QTableWidget()
        self.routes_table.setColumnCount(3)
        self.routes_table.setHorizontalHeaderLabels([
            t('gateway_from'),
            t('gateway_to'),
            t('gateway_enabled')
        ])
        # Adjust column widths
        header = self.routes_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)
        self.routes_table.setColumnWidth(2, 80)  # Fixed width for Enabled column
        self.routes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.routes_table.setMaximumHeight(150)
        transmission_layout.addWidget(self.routes_table)
        
        transmission_group.setLayout(transmission_layout)
        layout.addWidget(transmission_group)
        
        # Info label explaining channel logic
        info_label = QLabel(t('gateway_channel_info'))
        info_label.setWordWrap(True)
        info_label.setStyleSheet(colors['info_text'])
        layout.addWidget(info_label)
        
        # ===== Static Blocking Rules =====
        blocking_group = QGroupBox(t('gateway_blocking'))
        blocking_layout = QVBoxLayout()
        
        # Add rule controls
        add_block_layout = QHBoxLayout()
        
        add_block_layout.addWidget(QLabel(t('gateway_block_id') + ":"))
        self.block_id_input = QLineEdit()
        self.block_id_input.setPlaceholderText("0x000")
        self.block_id_input.setMaximumWidth(100)
        add_block_layout.addWidget(self.block_id_input)
        
        self.add_block_btn = QPushButton("➕ " + t('btn_add'))
        self.add_block_btn.clicked.connect(self.add_block_rule)
        add_block_layout.addWidget(self.add_block_btn)
        
        self.remove_block_btn = QPushButton("➖ " + t('btn_remove'))
        self.remove_block_btn.clicked.connect(self.remove_block_rule)
        add_block_layout.addWidget(self.remove_block_btn)
        
        add_block_layout.addStretch()
        blocking_layout.addLayout(add_block_layout)
        
        # Block rules table
        self.block_table = QTableWidget()
        self.block_table.setColumnCount(3)
        self.block_table.setHorizontalHeaderLabels([
            t('gateway_source_channel'),
            t('gateway_id'),
            t('gateway_enabled')
        ])
        # Adjust column widths
        header = self.block_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)
        self.block_table.setColumnWidth(2, 80)  # Fixed width for Enabled column
        self.block_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        blocking_layout.addWidget(self.block_table)
        
        blocking_group.setLayout(blocking_layout)
        layout.addWidget(blocking_group)
        
        # ===== Dynamic Blocking =====
        dynamic_group = QGroupBox(t('gateway_dynamic_blocking'))
        dynamic_layout = QVBoxLayout()
        
        # Dynamic block controls
        dyn_control_layout = QHBoxLayout()
        
        dyn_control_layout.addWidget(QLabel(t('gateway_id_from') + ":"))
        self.dyn_id_from_input = QLineEdit()
        self.dyn_id_from_input.setPlaceholderText("0x000")
        self.dyn_id_from_input.setMaximumWidth(100)
        dyn_control_layout.addWidget(self.dyn_id_from_input)
        
        dyn_control_layout.addWidget(QLabel(t('gateway_id_to') + ":"))
        self.dyn_id_to_input = QLineEdit()
        self.dyn_id_to_input.setPlaceholderText("0x7FF")
        self.dyn_id_to_input.setMaximumWidth(100)
        dyn_control_layout.addWidget(self.dyn_id_to_input)
        
        dyn_control_layout.addWidget(QLabel(t('gateway_period') + ":"))
        self.dyn_period_input = QLineEdit()
        self.dyn_period_input.setPlaceholderText("1000")
        self.dyn_period_input.setMaximumWidth(80)
        dyn_control_layout.addWidget(self.dyn_period_input)
        dyn_control_layout.addWidget(QLabel("ms"))
        
        self.add_dyn_btn = QPushButton("➕ " + t('btn_add'))
        self.add_dyn_btn.clicked.connect(self.add_dynamic_block)
        dyn_control_layout.addWidget(self.add_dyn_btn)
        
        self.remove_dyn_btn = QPushButton("➖ " + t('btn_remove'))
        self.remove_dyn_btn.clicked.connect(self.remove_dynamic_block)
        dyn_control_layout.addWidget(self.remove_dyn_btn)
        
        dyn_control_layout.addStretch()
        dynamic_layout.addLayout(dyn_control_layout)
        
        # Dynamic block table
        self.dynamic_table = QTableWidget()
        self.dynamic_table.setColumnCount(5)
        self.dynamic_table.setHorizontalHeaderLabels([
            t('gateway_source_channel'),
            t('gateway_id_from'),
            t('gateway_id_to'),
            t('gateway_period'),
            t('gateway_enabled')
        ])
        # Adjust column widths
        header = self.dynamic_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)
        header.setSectionResizeMode(3, header.ResizeMode.Stretch)
        header.setSectionResizeMode(4, header.ResizeMode.Fixed)
        self.dynamic_table.setColumnWidth(4, 80)  # Fixed width for Enabled column
        self.dynamic_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        dynamic_layout.addWidget(self.dynamic_table)
        
        dynamic_group.setLayout(dynamic_layout)
        layout.addWidget(dynamic_group)
        
        # ===== Message Modification =====
        modify_group = QGroupBox(t('gateway_modification'))
        modify_layout = QVBoxLayout()
        
        # Modify controls
        modify_control_layout = QHBoxLayout()
        
        modify_control_layout.addWidget(QLabel(t('gateway_modify_id') + ":"))
        self.modify_id_input = QLineEdit()
        self.modify_id_input.setPlaceholderText("0x000")
        self.modify_id_input.setMaximumWidth(100)
        modify_control_layout.addWidget(self.modify_id_input)
        
        self.add_modify_btn = QPushButton("✏️ " + t('gateway_add_modify'))
        self.add_modify_btn.clicked.connect(self.show_modify_dialog)
        modify_control_layout.addWidget(self.add_modify_btn)
        
        self.remove_modify_btn = QPushButton("➖ " + t('btn_remove'))
        self.remove_modify_btn.clicked.connect(self.remove_modify_rule)
        modify_control_layout.addWidget(self.remove_modify_btn)
        
        modify_control_layout.addStretch()
        modify_layout.addLayout(modify_control_layout)
        
        # Modify rules table
        self.modify_table = QTableWidget()
        self.modify_table.setColumnCount(5)
        self.modify_table.setHorizontalHeaderLabels([
            t('gateway_source_channel'),
            t('gateway_id'),
            t('gateway_new_id'),
            t('gateway_data_mask'),
            t('gateway_enabled')
        ])
        # Adjust column widths
        header = self.modify_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)
        header.setSectionResizeMode(3, header.ResizeMode.Stretch)
        header.setSectionResizeMode(4, header.ResizeMode.Fixed)
        self.modify_table.setColumnWidth(4, 80)  # Fixed width for Enabled column
        self.modify_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.modify_table.itemDoubleClicked.connect(self.edit_modify_rule)
        modify_layout.addWidget(self.modify_table)
        
        modify_group.setLayout(modify_layout)
        layout.addWidget(modify_group)
        
        # ===== Statistics =====
        stats_group = QGroupBox(t('gateway_statistics'))
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel(t('gateway_stats_template').format(
            forwarded=0, blocked=0, modified=0
        ))
        stats_layout.addWidget(self.stats_label)
        
        self.reset_stats_btn = QPushButton(t('gateway_reset_stats'))
        self.reset_stats_btn.clicked.connect(self.reset_stats)
        stats_layout.addWidget(self.reset_stats_btn)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # ===== Save/Load Configuration =====
        config_layout = QHBoxLayout()
        
        self.save_config_btn = QPushButton(t('gateway_save_config'))
        self.save_config_btn.clicked.connect(self.save_gateway_config)
        config_layout.addWidget(self.save_config_btn)
        
        self.load_config_btn = QPushButton(t('gateway_load_config'))
        self.load_config_btn.clicked.connect(self.load_gateway_config)
        config_layout.addWidget(self.load_config_btn)
        
        config_layout.addStretch()
        layout.addLayout(config_layout)
        
        # ===== Buttons =====
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
            apply_button.clicked.connect(self.apply_changes)
        
        layout.addWidget(button_box)
        
        # Load existing rules and routes
        self.load_routes()
        self.load_rules()
    
    def _create_centered_checkbox(self, checked=True):
        """Create a centered checkbox widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget, checkbox
    
    def load_routes(self):
        """Load existing routes into table"""
        self.routes_table.setRowCount(len(self.config.routes))
        for row, route in enumerate(self.config.routes):
            self.routes_table.setItem(row, 0, QTableWidgetItem(route.source))
            self.routes_table.setItem(row, 1, QTableWidgetItem(route.destination))
            
            widget, enabled_check = self._create_centered_checkbox(route.enabled)
            # Connect to apply changes immediately
            enabled_check.stateChanged.connect(lambda state, r=row: self._on_route_enabled_changed(r, state))
            self.routes_table.setCellWidget(row, 2, widget)
    
    def _on_route_enabled_changed(self, row, state):
        """Apply route enable/disable immediately"""
        if row < len(self.config.routes):
            self.config.routes[row].enabled = (state == Qt.CheckState.Checked.value)
            # Apply to parent if dialog has parent with can_bus_manager
            if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
                if self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(self.config)
    
    def add_route(self):
        """Add a new route"""
        source = self.source_combo.currentText()
        dest = self.dest_combo.currentText()
        
        # Validate
        if source == dest:
            QMessageBox.warning(
                self,
                t('warning'),
                t('gateway_same_source_dest')
            )
            return
        
        # Check if route already exists
        for route in self.config.routes:
            if route.source == source and route.destination == dest:
                QMessageBox.warning(
                    self,
                    t('warning'),
                    t('gateway_route_exists')
                )
                return
        
        # Add route
        route = GatewayRoute(source=source, destination=dest, enabled=True)
        self.config.routes.append(route)
        
        # Add to table
        row = self.routes_table.rowCount()
        self.routes_table.insertRow(row)
        self.routes_table.setItem(row, 0, QTableWidgetItem(source))
        self.routes_table.setItem(row, 1, QTableWidgetItem(dest))
        
        widget, enabled_check = self._create_centered_checkbox(True)
        # Connect to apply changes immediately
        enabled_check.stateChanged.connect(lambda state, r=row: self._on_route_enabled_changed(r, state))
        self.routes_table.setCellWidget(row, 2, widget)
    
    def remove_route(self):
        """Remove selected route"""
        selected_rows = self.routes_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, t('warning'), t('gateway_select_route'))
            return
        
        row = selected_rows[0].row()
        self.config.routes.pop(row)
        self.routes_table.removeRow(row)
    
    def load_rules(self):
        """Load existing rules into tables"""
        # Load block rules
        self.block_table.setRowCount(len(self.config.block_rules))
        for row, rule in enumerate(self.config.block_rules):
            self.block_table.setItem(row, 0, QTableWidgetItem(rule.channel))
            self.block_table.setItem(row, 1, QTableWidgetItem(f"0x{rule.can_id:03X}"))
            
            widget, enabled_check = self._create_centered_checkbox(rule.enabled)
            # Connect to apply changes immediately
            enabled_check.stateChanged.connect(lambda state, r=row: self._on_block_enabled_changed(r, state))
            self.block_table.setCellWidget(row, 2, widget)
        
        # Load dynamic blocks
        self.dynamic_table.setRowCount(len(self.config.dynamic_blocks))
        for row, dyn_block in enumerate(self.config.dynamic_blocks):
            self.dynamic_table.setItem(row, 0, QTableWidgetItem(dyn_block.channel))
            self.dynamic_table.setItem(row, 1, QTableWidgetItem(f"0x{dyn_block.id_from:03X}"))
            self.dynamic_table.setItem(row, 2, QTableWidgetItem(f"0x{dyn_block.id_to:03X}"))
            self.dynamic_table.setItem(row, 3, QTableWidgetItem(f"{dyn_block.period}"))
            
            widget, enabled_check = self._create_centered_checkbox(dyn_block.enabled)
            # Connect to apply changes immediately
            enabled_check.stateChanged.connect(lambda state, r=row: self._on_dynamic_enabled_changed(r, state))
            self.dynamic_table.setCellWidget(row, 4, widget)
        
        # Load modify rules
        self.modify_table.setRowCount(len(self.config.modify_rules))
        for row, rule in enumerate(self.config.modify_rules):
            self.modify_table.setItem(row, 0, QTableWidgetItem(rule.channel))
            self.modify_table.setItem(row, 1, QTableWidgetItem(f"0x{rule.can_id:03X}"))
            
            # New ID
            new_id_str = f"0x{rule.new_id:03X}" if rule.new_id is not None else "-"
            self.modify_table.setItem(row, 2, QTableWidgetItem(new_id_str))
            
            # Data mask summary
            mask_count = sum(rule.data_mask)
            mask_str = f"{mask_count} bytes" if mask_count > 0 else "-"
            self.modify_table.setItem(row, 3, QTableWidgetItem(mask_str))
            
            widget, enabled_check = self._create_centered_checkbox(rule.enabled)
            # Connect to apply changes immediately
            enabled_check.stateChanged.connect(lambda state, r=row: self._on_modify_enabled_changed(r, state))
            self.modify_table.setCellWidget(row, 4, widget)
    
    def _on_block_enabled_changed(self, row, state):
        """Apply block rule enable/disable immediately"""
        if row < len(self.config.block_rules):
            self.config.block_rules[row].enabled = (state == Qt.CheckState.Checked.value)
            # Apply to parent if dialog has parent with can_bus_manager
            if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
                if self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(self.config)
    
    def _on_dynamic_enabled_changed(self, row, state):
        """Apply dynamic block enable/disable immediately"""
        if row < len(self.config.dynamic_blocks):
            self.config.dynamic_blocks[row].enabled = (state == Qt.CheckState.Checked.value)
            # Apply to parent if dialog has parent with can_bus_manager
            if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
                if self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(self.config)
    
    def _on_modify_enabled_changed(self, row, state):
        """Apply modify rule enable/disable immediately"""
        if row < len(self.config.modify_rules):
            self.config.modify_rules[row].enabled = (state == Qt.CheckState.Checked.value)
            # Apply to parent if dialog has parent with can_bus_manager
            if self.parent() and hasattr(self.parent(), 'can_bus_manager'):
                if self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(self.config)
    
    def _get_source_channels(self):
        """Get list of source channels based on active routes"""
        channels = []
        for row in range(self.routes_table.rowCount()):
            widget = self.routes_table.cellWidget(row, 2)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    source = self.routes_table.item(row, 0).text()
                    if source not in channels:
                        channels.append(source)
        return channels
    
    def add_block_rule(self):
        """Add a new blocking rule (auto-detects channel from transmission direction)"""
        try:
            id_text = self.block_id_input.text().strip()
            
            if not id_text:
                QMessageBox.warning(self, t('warning'), t('gateway_enter_id'))
                return
            
            # Check if transmission is configured
            source_channels = self._get_source_channels()
            if not source_channels:
                QMessageBox.warning(
                    self,
                    t('warning'),
                    t('gateway_configure_transmission_first')
                )
                return
            
            # Parse ID (support hex with 0x prefix)
            if id_text.startswith('0x') or id_text.startswith('0X'):
                can_id = int(id_text, 16)
            else:
                can_id = int(id_text)
            
            # Add rule for each active source channel
            for channel in source_channels:
                rule = GatewayBlockRule(can_id=can_id, channel=channel, enabled=True)
                self.config.block_rules.append(rule)
                
                # Add to table
                row = self.block_table.rowCount()
                self.block_table.insertRow(row)
                self.block_table.setItem(row, 0, QTableWidgetItem(channel))
                self.block_table.setItem(row, 1, QTableWidgetItem(f"0x{can_id:03X}"))
                
                widget, enabled_check = self._create_centered_checkbox(True)
                # Connect to apply changes immediately
                enabled_check.stateChanged.connect(lambda state, r=row: self._on_block_enabled_changed(r, state))
                self.block_table.setCellWidget(row, 2, widget)
            
            # Clear input
            self.block_id_input.clear()
            
        except ValueError:
            QMessageBox.warning(self, t('error'), t('gateway_invalid_id'))
    
    def remove_block_rule(self):
        """Remove selected blocking rule"""
        selected_rows = self.block_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, t('warning'), t('gateway_select_rule'))
            return
        
        row = selected_rows[0].row()
        self.config.block_rules.pop(row)
        self.block_table.removeRow(row)
    
    def add_dynamic_block(self):
        """Add a new dynamic blocking rule (auto-detects channel)"""
        try:
            id_from_text = self.dyn_id_from_input.text().strip()
            id_to_text = self.dyn_id_to_input.text().strip()
            period_text = self.dyn_period_input.text().strip()
            
            if not all([id_from_text, id_to_text, period_text]):
                QMessageBox.warning(self, t('warning'), t('gateway_fill_all_fields'))
                return
            
            # Check if transmission is configured
            source_channels = self._get_source_channels()
            if not source_channels:
                QMessageBox.warning(
                    self,
                    t('warning'),
                    t('gateway_configure_transmission_first')
                )
                return
            
            # Parse values
            if id_from_text.startswith('0x'):
                id_from = int(id_from_text, 16)
            else:
                id_from = int(id_from_text)
            
            if id_to_text.startswith('0x'):
                id_to = int(id_to_text, 16)
            else:
                id_to = int(id_to_text)
            
            period = int(period_text)
            
            # Add dynamic block for each active source channel
            for channel in source_channels:
                dyn_block = GatewayDynamicBlock(
                    id_from=id_from,
                    id_to=id_to,
                    channel=channel,
                    period=period,
                    enabled=True
                )
                self.config.dynamic_blocks.append(dyn_block)
                
                # Add to table
                row = self.dynamic_table.rowCount()
                self.dynamic_table.insertRow(row)
                self.dynamic_table.setItem(row, 0, QTableWidgetItem(channel))
                self.dynamic_table.setItem(row, 1, QTableWidgetItem(f"0x{id_from:03X}"))
                self.dynamic_table.setItem(row, 2, QTableWidgetItem(f"0x{id_to:03X}"))
                self.dynamic_table.setItem(row, 3, QTableWidgetItem(f"{period}"))
                
                widget, enabled_check = self._create_centered_checkbox(True)
                # Connect to apply changes immediately
                enabled_check.stateChanged.connect(lambda state, r=row: self._on_dynamic_enabled_changed(r, state))
                self.dynamic_table.setCellWidget(row, 4, widget)
            
            # Clear inputs
            self.dyn_id_from_input.clear()
            self.dyn_id_to_input.clear()
            self.dyn_period_input.clear()
            
        except ValueError:
            QMessageBox.warning(self, t('error'), t('gateway_invalid_values'))
    
    def remove_dynamic_block(self):
        """Remove selected dynamic blocking rule"""
        selected_rows = self.dynamic_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, t('warning'), t('gateway_select_rule'))
            return
        
        row = selected_rows[0].row()
        self.config.dynamic_blocks.pop(row)
        self.dynamic_table.removeRow(row)
    
    def reset_stats(self):
        """Reset statistics (signal to parent)"""
        self.stats_label.setText(t('gateway_stats_template').format(
            forwarded=0, blocked=0, modified=0
        ))
    
    def update_stats(self, stats):
        """Update statistics display"""
        self.stats_label.setText(t('gateway_stats_template').format(
            forwarded=stats.get('forwarded', 0),
            blocked=stats.get('blocked', 0),
            modified=stats.get('modified', 0)
        ))
    
    def show_modify_dialog(self):
        """Show dialog to add/edit modify rule (auto-detects channel)"""
        id_text = self.modify_id_input.text().strip()
        
        if not id_text:
            QMessageBox.warning(self, t('warning'), t('gateway_enter_id'))
            return
        
        # Check if transmission is configured
        source_channels = self._get_source_channels()
        if not source_channels:
            QMessageBox.warning(
                self,
                t('warning'),
                t('gateway_configure_transmission_first')
            )
            return
        
        try:
            # Parse ID
            if id_text.startswith('0x') or id_text.startswith('0X'):
                can_id = int(id_text, 16)
            else:
                can_id = int(id_text)
            
            # Add rule for each active source channel
            for channel in source_channels:
                # Show modify rule editor dialog
                dialog = ModifyRuleDialog(self, channel, can_id)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    rule = dialog.get_rule()
                    self.config.modify_rules.append(rule)
                    
                    # Add to table
                    row = self.modify_table.rowCount()
                    self.modify_table.insertRow(row)
                    self.modify_table.setItem(row, 0, QTableWidgetItem(rule.channel))
                    self.modify_table.setItem(row, 1, QTableWidgetItem(f"0x{rule.can_id:03X}"))
                    
                    new_id_str = f"0x{rule.new_id:03X}" if rule.new_id is not None else "-"
                    self.modify_table.setItem(row, 2, QTableWidgetItem(new_id_str))
                    
                    mask_count = sum(rule.data_mask)
                    mask_str = f"{mask_count} bytes" if mask_count > 0 else "-"
                    self.modify_table.setItem(row, 3, QTableWidgetItem(mask_str))
                    
                    widget, enabled_check = self._create_centered_checkbox(True)
                    # Connect to apply changes immediately
                    enabled_check.stateChanged.connect(lambda state, r=row: self._on_modify_enabled_changed(r, state))
                    self.modify_table.setCellWidget(row, 4, widget)
            
            # Clear input
            self.modify_id_input.clear()
                
        except ValueError:
            QMessageBox.warning(self, t('error'), t('gateway_invalid_id'))
    
    def edit_modify_rule(self, item):
        """Edit existing modify rule"""
        row = item.row()
        if row >= len(self.config.modify_rules):
            return
        
        rule = self.config.modify_rules[row]
        
        # Show modify rule editor dialog with existing rule
        dialog = ModifyRuleDialog(self, rule.channel, rule.can_id, rule)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_rule = dialog.get_rule()
            self.config.modify_rules[row] = updated_rule
            
            # Update table
            self.modify_table.setItem(row, 0, QTableWidgetItem(updated_rule.channel))
            self.modify_table.setItem(row, 1, QTableWidgetItem(f"0x{updated_rule.can_id:03X}"))
            
            new_id_str = f"0x{updated_rule.new_id:03X}" if updated_rule.new_id is not None else "-"
            self.modify_table.setItem(row, 2, QTableWidgetItem(new_id_str))
            
            mask_count = sum(updated_rule.data_mask)
            mask_str = f"{mask_count} bytes" if mask_count > 0 else "-"
            self.modify_table.setItem(row, 3, QTableWidgetItem(mask_str))
    
    def remove_modify_rule(self):
        """Remove selected modify rule"""
        selected_rows = self.modify_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, t('warning'), t('gateway_select_rule'))
            return
        
        row = selected_rows[0].row()
        self.config.modify_rules.pop(row)
        self.modify_table.removeRow(row)
    
    def save_gateway_config(self):
        """Save gateway configuration to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            t('gateway_save_config'),
            "",
            "Gateway Config (*.gwcfg);;JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                # Get current config from UI
                current_config = self.get_config()
                
                # Create save data with file type
                data = {
                    'version': '1.0',
                    'file_type': 'gateway',
                    'gateway_config': current_config.to_dict()
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                filename_short = os.path.basename(filename)
                QMessageBox.information(
                    self,
                    t('success'),
                    t('gateway_config_saved').format(filename=filename_short)
                )
                
            except Exception as e:
                QMessageBox.critical(self, t('error'), f"Error saving: {str(e)}")
    
    def load_gateway_config(self):
        """Load gateway configuration from file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            t('gateway_load_config'),
            "",
            "Gateway Config (*.gwcfg);;JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                # Validate file type
                file_type = data.get('file_type', None)
                if file_type and file_type != 'gateway':
                    filename_short = os.path.basename(filename)
                    
                    type_names = {
                        'tracer': t('file_type_tracer'),
                        'monitor': t('file_type_monitor'),
                        'transmit': t('file_type_transmit'),
                        'gateway': t('file_type_gateway')
                    }
                    
                    QMessageBox.warning(
                        self,
                        t('warning'),
                        t('msg_wrong_file_type').format(
                            filename=filename_short,
                            expected=type_names['gateway'],
                            found=type_names.get(file_type, file_type)
                        )
                    )
                    return
                
                # Load configuration
                gateway_data = data.get('gateway_config', {})
                self.config = GatewayConfig.from_dict(gateway_data)
                
                # Reload UI
                self.enable_gateway_check.setChecked(self.config.enabled)
                
                # Clear and reload tables
                self.routes_table.setRowCount(0)
                self.block_table.setRowCount(0)
                self.dynamic_table.setRowCount(0)
                self.modify_table.setRowCount(0)
                self.load_routes()
                self.load_rules()
                
                filename_short = os.path.basename(filename)
                QMessageBox.information(
                    self,
                    t('success'),
                    t('gateway_config_loaded').format(filename=filename_short)
                )
                
            except Exception as e:
                QMessageBox.critical(self, t('error'), f"Error loading: {str(e)}")
    
    def apply_changes(self):
        """Apply changes without closing the dialog"""
        # Get current config
        config = self.get_config()
        
        # Notify parent to apply the configuration
        if self.parent():
            try:
                # Update parent's gateway config
                self.parent().gateway_config = config
                
                # Apply to CAN bus manager if available
                if hasattr(self.parent(), 'can_bus_manager') and self.parent().can_bus_manager:
                    self.parent().can_bus_manager.set_gateway_config(config)
                
                # Update gateway button state
                if hasattr(self.parent(), 'update_gateway_button_state'):
                    self.parent().update_gateway_button_state()
                
                # Show notification
                if hasattr(self.parent(), 'show_notification'):
                    if config.enabled:
                        self.parent().show_notification("Gateway configuration applied", 2000)
                    else:
                        self.parent().show_notification("Gateway disabled", 2000)
                
                # Show success message in dialog
                QMessageBox.information(
                    self,
                    "Applied",
                    "Gateway configuration has been applied successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to apply configuration: {str(e)}"
                )
    
    def get_config(self):
        """Get the configured gateway settings"""
        # Update config from UI
        self.config.enabled = self.enable_gateway_check.isChecked()
        
        # Update routes enabled status
        for row in range(self.routes_table.rowCount()):
            widget = self.routes_table.cellWidget(row, 2)
            if widget and row < len(self.config.routes):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    self.config.routes[row].enabled = checkbox.isChecked()
        
        # Update enabled status from checkboxes
        for row in range(self.block_table.rowCount()):
            widget = self.block_table.cellWidget(row, 2)
            if widget and row < len(self.config.block_rules):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    self.config.block_rules[row].enabled = checkbox.isChecked()
        
        for row in range(self.dynamic_table.rowCount()):
            widget = self.dynamic_table.cellWidget(row, 4)
            if widget and row < len(self.config.dynamic_blocks):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    self.config.dynamic_blocks[row].enabled = checkbox.isChecked()
        
        for row in range(self.modify_table.rowCount()):
            widget = self.modify_table.cellWidget(row, 4)
            if widget and row < len(self.config.modify_rules):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    self.config.modify_rules[row].enabled = checkbox.isChecked()
        
        return self.config
