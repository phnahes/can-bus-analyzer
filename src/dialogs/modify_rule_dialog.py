"""
Modify Rule Dialog - Configure message modification rule with bit mask
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QGroupBox, QScrollArea, QWidget, QDialogButtonBox, QGridLayout
)
from PyQt6.QtCore import Qt

from ..config import DEFAULT_CAN_ID_STR, DEFAULT_CHANNEL
from ..models import GatewayModifyRule
from ..i18n import get_i18n, t
from ..theme import get_adaptive_colors


class ModifyRuleDialog(QDialog):
    """Dialog to configure message modification rule with bit mask"""
    def __init__(self, parent=None, channel=None, can_id=None, existing_rule=None):
        super().__init__(parent)
        self.channel = channel or DEFAULT_CHANNEL
        self.can_id = can_id or 0x000
        self.existing_rule = existing_rule
        self.i18n = get_i18n()
        
        # Initialize data
        if existing_rule:
            self.new_id = existing_rule.new_id
            self.data_mask = existing_rule.data_mask.copy()
            self.new_data = bytearray(existing_rule.new_data)
        else:
            self.new_id = None
            self.data_mask = [False] * 8
            self.new_data = bytearray([0x00] * 8)
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(t('gateway_modify_rule_title'))
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        
        # Get theme
        colors = get_adaptive_colors('system')
        
        # ===== Message Info =====
        info_group = QGroupBox(t('gateway_message_info'))
        info_layout = QGridLayout()
        
        info_layout.addWidget(QLabel(t('gateway_channel') + ":"), 0, 0)
        info_layout.addWidget(QLabel(f"<b>{self.channel}</b>"), 0, 1)
        
        info_layout.addWidget(QLabel(t('gateway_id') + ":"), 1, 0)
        info_layout.addWidget(QLabel(f"<b>0x{self.can_id:03X}</b>"), 1, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # ===== ID Modification =====
        id_group = QGroupBox(t('gateway_id_modification'))
        id_layout = QHBoxLayout()
        
        self.modify_id_check = QCheckBox(t('gateway_change_id'))
        self.modify_id_check.setChecked(self.new_id is not None)
        self.modify_id_check.toggled.connect(self.on_modify_id_toggled)
        id_layout.addWidget(self.modify_id_check)
        
        id_layout.addWidget(QLabel(t('gateway_new_id') + ":"))
        self.new_id_input = QLineEdit()
        self.new_id_input.setPlaceholderText(DEFAULT_CAN_ID_STR)
        self.new_id_input.setMaximumWidth(100)
        self.new_id_input.setEnabled(self.new_id is not None)
        if self.new_id is not None:
            self.new_id_input.setText(f"0x{self.new_id:03X}")
        id_layout.addWidget(self.new_id_input)
        
        id_layout.addStretch()
        id_group.setLayout(id_layout)
        layout.addWidget(id_group)
        
        # ===== Data Modification with Bit Masks =====
        data_group = QGroupBox(t('gateway_data_modification'))
        data_layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel(t('gateway_data_modification_info'))
        info_label.setWordWrap(True)
        info_label.setStyleSheet(colors['info_text'])
        data_layout.addWidget(info_label)
        
        # Create byte editors (8 bytes)
        self.byte_editors = []
        
        for byte_idx in range(8):
            byte_widget = QWidget()
            byte_layout = QVBoxLayout(byte_widget)
            byte_layout.setContentsMargins(5, 5, 5, 5)
            
            # Byte header
            byte_header = QLabel(f"<b>Byte {byte_idx} (D{byte_idx})</b>")
            byte_layout.addWidget(byte_header)
            
            # Enable checkbox
            enable_check = QCheckBox(t('gateway_modify_this_byte'))
            enable_check.setChecked(self.data_mask[byte_idx])
            enable_check.toggled.connect(lambda checked, idx=byte_idx: self.on_byte_enabled(idx, checked))
            byte_layout.addWidget(enable_check)
            
            # Hex value input
            hex_layout = QHBoxLayout()
            hex_layout.addWidget(QLabel("Hex:"))
            hex_input = QLineEdit(f"{self.new_data[byte_idx]:02X}")
            hex_input.setMaximumWidth(50)
            hex_input.setMaxLength(2)
            hex_input.setInputMask("HH")
            hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hex_input.setEnabled(self.data_mask[byte_idx])
            hex_input.textChanged.connect(lambda text, idx=byte_idx: self.on_hex_changed(idx, text))
            hex_layout.addWidget(hex_input)
            hex_layout.addStretch()
            byte_layout.addLayout(hex_layout)
            
            # Bit checkboxes (8 bits per byte)
            bits_label = QLabel(t('gateway_bits') + ":")
            byte_layout.addWidget(bits_label)
            
            bits_layout = QHBoxLayout()
            bit_checks = []
            for bit_idx in range(7, -1, -1):  # MSB to LSB (7→0)
                bit_check = QCheckBox(f"{bit_idx}")
                bit_value = (self.new_data[byte_idx] >> bit_idx) & 1
                bit_check.setChecked(bool(bit_value))
                bit_check.setEnabled(self.data_mask[byte_idx])
                bit_check.toggled.connect(lambda checked, b_idx=byte_idx, bit=bit_idx: self.on_bit_toggled(b_idx, bit, checked))
                bit_checks.append(bit_check)
                bits_layout.addWidget(bit_check)
            bits_layout.addStretch()
            byte_layout.addLayout(bits_layout)
            
            # Decimal value display
            dec_label = QLabel(f"Dec: {self.new_data[byte_idx]}")
            dec_label.setStyleSheet("color: gray; font-size: 10px;")
            byte_layout.addWidget(dec_label)
            
            # Store references
            self.byte_editors.append({
                'widget': byte_widget,
                'enable_check': enable_check,
                'hex_input': hex_input,
                'bit_checks': bit_checks,
                'dec_label': dec_label
            })
        
        # Arrange bytes in grid (2 rows x 4 columns)
        bytes_grid = QWidget()
        bytes_grid_layout = QGridLayout(bytes_grid)
        
        for i, editor in enumerate(self.byte_editors):
            row = i // 4
            col = i % 4
            bytes_grid_layout.addWidget(editor['widget'], row, col)
        
        # Add to scrollable area
        scroll = QScrollArea()
        scroll.setWidget(bytes_grid)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(300)
        data_layout.addWidget(scroll)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # ===== Preview =====
        preview_group = QGroupBox(t('gateway_preview'))
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.update_preview()
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # ===== Buttons =====
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_modify_id_toggled(self, checked):
        """Handle ID modification toggle"""
        self.new_id_input.setEnabled(checked)
        if not checked:
            self.new_id = None
        self.update_preview()
    
    def on_byte_enabled(self, byte_idx, checked):
        """Handle byte enable/disable"""
        self.data_mask[byte_idx] = checked
        
        # Enable/disable controls
        editor = self.byte_editors[byte_idx]
        editor['hex_input'].setEnabled(checked)
        for bit_check in editor['bit_checks']:
            bit_check.setEnabled(checked)
        
        self.update_preview()
    
    def on_hex_changed(self, byte_idx, text):
        """Handle hex value change"""
        if len(text) == 2:
            try:
                value = int(text, 16)
                self.new_data[byte_idx] = value
                
                # Update bit checkboxes
                editor = self.byte_editors[byte_idx]
                for bit_idx in range(8):
                    bit_value = (value >> bit_idx) & 1
                    # Temporarily disconnect to avoid recursion
                    editor['bit_checks'][7 - bit_idx].blockSignals(True)
                    editor['bit_checks'][7 - bit_idx].setChecked(bool(bit_value))
                    editor['bit_checks'][7 - bit_idx].blockSignals(False)
                
                # Update decimal label
                editor['dec_label'].setText(f"Dec: {value}")
                
                self.update_preview()
            except ValueError:
                pass
    
    def on_bit_toggled(self, byte_idx, bit_idx, checked):
        """Handle individual bit toggle"""
        if checked:
            self.new_data[byte_idx] |= (1 << bit_idx)
        else:
            self.new_data[byte_idx] &= ~(1 << bit_idx)
        
        # Update hex input
        editor = self.byte_editors[byte_idx]
        editor['hex_input'].blockSignals(True)
        editor['hex_input'].setText(f"{self.new_data[byte_idx]:02X}")
        editor['hex_input'].blockSignals(False)
        
        # Update decimal label
        editor['dec_label'].setText(f"Dec: {self.new_data[byte_idx]}")
        
        self.update_preview()
    
    def update_preview(self):
        """Update preview of modifications"""
        preview_text = f"<b>{t('gateway_original')}:</b> ID=0x{self.can_id:03X}, Data=[Original]<br>"
        
        # ID modification
        if self.modify_id_check.isChecked() and self.new_id_input.text():
            try:
                id_text = self.new_id_input.text().strip()
                if id_text.startswith('0x'):
                    new_id = int(id_text, 16)
                else:
                    new_id = int(id_text)
                self.new_id = new_id
                preview_text += f"<b>{t('gateway_modified')}:</b> ID=<span style='color: orange;'>0x{new_id:03X}</span>"
            except ValueError:
                preview_text += f"<b>{t('gateway_modified')}:</b> ID=0x{self.can_id:03X}"
        else:
            self.new_id = None
            preview_text += f"<b>{t('gateway_modified')}:</b> ID=0x{self.can_id:03X}"
        
        # Data modification
        modified_bytes = []
        for i in range(8):
            if self.data_mask[i]:
                modified_bytes.append(f"<span style='color: orange;'>{self.new_data[i]:02X}</span>")
            else:
                modified_bytes.append("--")
        
        preview_text += f", Data=[{' '.join(modified_bytes)}]"
        
        # Summary
        mask_count = sum(self.data_mask)
        if mask_count > 0:
            preview_text += f"<br><br><i>{t('gateway_bytes_modified')}: {mask_count}</i>"
        
        self.preview_label.setText(preview_text)
    
    def get_rule(self) -> GatewayModifyRule:
        """Get the configured modify rule"""
        return GatewayModifyRule(
            can_id=self.can_id,
            channel=self.channel,
            enabled=True,
            new_id=self.new_id,
            data_mask=self.data_mask.copy(),
            new_data=bytes(self.new_data)
        )
