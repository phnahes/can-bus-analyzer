"""
Diff Mode Dialog - Configure message difference detection settings
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QGroupBox, QPushButton, QDialogButtonBox, QSpinBox,
    QDoubleSpinBox, QComboBox, QLineEdit, QWidget, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..theme import get_adaptive_colors
from ..handlers import DiffConfig


class DiffDialog(QDialog):
    """Dialog for configuring Diff Mode settings"""
    
    def __init__(self, parent=None, current_config: DiffConfig = None):
        super().__init__(parent)
        self.current_config = current_config or DiffConfig()
        self._autosave_timer = None
        
        # Get theme from parent's config if available
        self.theme_pref = 'system'
        if parent and hasattr(parent, 'theme_preference'):
            self.theme_pref = parent.theme_preference
        
        # Store statistics if parent has diff_manager
        self.statistics = None
        if parent and hasattr(parent, 'receive_table_mgr'):
            if parent.receive_table_mgr.diff_manager:
                self.statistics = parent.receive_table_mgr.diff_manager.get_statistics()
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle("Diff Mode Configuration")
        self.setModal(True)
        self.setMinimumSize(550, 600)
        
        layout = QVBoxLayout(self)
        colors = get_adaptive_colors(self.theme_pref)
        
        # Title and description
        title_label = QLabel("🔍 Diff Mode Settings")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "Filter repeated messages in Monitor mode to show only changes.\n"
            "Messages with low frequency are always displayed."
        )
        desc_label.setStyleSheet(colors['info_text'])
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addSpacing(10)
        
        # Enable/Disable
        self.enable_check = QCheckBox("Enable Diff Mode")
        self.enable_check.setChecked(self.current_config.enabled)
        self.enable_check.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        layout.addWidget(self.enable_check)
        
        layout.addSpacing(10)
        
        # Filtering Criteria Group
        criteria_group = QGroupBox("Filtering Criteria")
        criteria_layout = QFormLayout()

        # Mode
        mode_layout = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Filter (hide repeated)",
            "Highlight only",
            "Both",
        ])
        self.mode_combo.setMinimumWidth(220)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        mode_help = QLabel("How Diff affects display")
        mode_help.setStyleSheet("color: gray; font-size: 10px;")
        mode_layout.addWidget(mode_help)
        criteria_layout.addRow("Mode:", mode_layout)
        
        # Min Message Rate
        rate_layout = QHBoxLayout()
        self.min_rate_spin = QDoubleSpinBox()
        self.min_rate_spin.setRange(0.1, 1000.0)
        self.min_rate_spin.setSingleStep(1.0)
        self.min_rate_spin.setValue(self.current_config.min_message_rate)
        self.min_rate_spin.setSuffix(" msgs/s")
        self.min_rate_spin.setMinimumWidth(150)
        rate_layout.addWidget(self.min_rate_spin)
        rate_layout.addStretch()
        
        rate_help = QLabel("Only filter messages above this rate")
        rate_help.setStyleSheet("color: gray; font-size: 10px;")
        rate_layout.addWidget(rate_help)
        
        criteria_layout.addRow("Min Message Rate:", rate_layout)
        
        # Min Bytes Changed
        bytes_layout = QHBoxLayout()
        self.min_bytes_spin = QSpinBox()
        self.min_bytes_spin.setRange(1, 8)
        self.min_bytes_spin.setValue(self.current_config.min_bytes_changed)
        self.min_bytes_spin.setSuffix(" byte(s)")
        self.min_bytes_spin.setMinimumWidth(150)
        bytes_layout.addWidget(self.min_bytes_spin)
        bytes_layout.addStretch()
        
        bytes_help = QLabel("Minimum bytes that must change")
        bytes_help.setStyleSheet("color: gray; font-size: 10px;")
        bytes_layout.addWidget(bytes_help)
        
        criteria_layout.addRow("Min Bytes Changed:", bytes_layout)

        # Rate window (sliding)
        window_layout = QHBoxLayout()
        self.time_window_spin = QSpinBox()
        self.time_window_spin.setRange(50, 5000)
        self.time_window_spin.setSingleStep(50)
        self.time_window_spin.setValue(getattr(self.current_config, 'time_window_ms', 500))
        self.time_window_spin.setSuffix(" ms")
        self.time_window_spin.setMinimumWidth(150)
        window_layout.addWidget(self.time_window_spin)
        window_layout.addStretch()

        window_help = QLabel("Rate is computed over this sliding window")
        window_help.setStyleSheet("color: gray; font-size: 10px;")
        window_layout.addWidget(window_help)
        criteria_layout.addRow("Rate Window:", window_layout)

        # Heartbeat (max suppress time)
        hb_layout = QHBoxLayout()
        self.max_suppress_spin = QSpinBox()
        self.max_suppress_spin.setRange(0, 30000)
        self.max_suppress_spin.setSingleStep(100)
        self.max_suppress_spin.setValue(getattr(self.current_config, 'max_suppress_ms', 1000))
        self.max_suppress_spin.setSuffix(" ms")
        self.max_suppress_spin.setMinimumWidth(150)
        hb_layout.addWidget(self.max_suppress_spin)
        hb_layout.addStretch()

        hb_help = QLabel("Show at least 1 frame per ID within this interval (0 = off)")
        hb_help.setStyleSheet("color: gray; font-size: 10px;")
        hb_layout.addWidget(hb_help)
        criteria_layout.addRow("Heartbeat:", hb_layout)
        
        # Compare by Channel
        channel_layout = QHBoxLayout()
        self.compare_channel_check = QCheckBox()
        self.compare_channel_check.setChecked(self.current_config.compare_by_channel)
        channel_layout.addWidget(self.compare_channel_check)
        channel_layout.addStretch()
        
        channel_help = QLabel("Compare messages by ID + Channel (recommended)")
        channel_help.setStyleSheet("color: gray; font-size: 10px;")
        channel_layout.addWidget(channel_help)
        
        criteria_layout.addRow("Compare by Channel:", channel_layout)
        
        # Byte Mask
        mask_layout = QVBoxLayout()
        
        mask_input_layout = QHBoxLayout()
        self.byte_mask_combo = QComboBox()
        self.byte_mask_combo.addItems([
            "all",
            "0-3 (first 4 bytes)",
            "0-7 (all 8 bytes)",
            "custom"
        ])
        self.byte_mask_combo.setMinimumWidth(200)
        self.byte_mask_combo.currentTextChanged.connect(self._on_mask_changed)
        mask_input_layout.addWidget(self.byte_mask_combo)
        mask_input_layout.addStretch()
        
        mask_layout.addLayout(mask_input_layout)
        
        # Custom mask input
        self.custom_mask_widget = QWidget()
        custom_mask_layout = QHBoxLayout(self.custom_mask_widget)
        custom_mask_layout.setContentsMargins(0, 5, 0, 0)
        
        custom_mask_label = QLabel("Custom mask:")
        custom_mask_layout.addWidget(custom_mask_label)
        
        self.custom_mask_input = QLineEdit()
        self.custom_mask_input.setPlaceholderText("e.g., 0,1,2 or 0-3,5,7")
        self.custom_mask_input.setMinimumWidth(200)
        custom_mask_layout.addWidget(self.custom_mask_input)
        custom_mask_layout.addStretch()
        
        mask_layout.addWidget(self.custom_mask_widget)
        self.custom_mask_widget.setVisible(False)
        
        mask_help = QLabel("Which bytes to compare for changes")
        mask_help.setStyleSheet("color: gray; font-size: 10px;")
        mask_layout.addWidget(mask_help)
        
        criteria_layout.addRow("Byte Mask:", mask_layout)
        
        # Set initial byte mask value
        self._set_initial_byte_mask()
        
        criteria_group.setLayout(criteria_layout)
        layout.addWidget(criteria_group)

        # Statistics Group (always visible)
        stats_group = QGroupBox("Current Statistics")
        stats_layout = QVBoxLayout()

        if self.statistics:
            total_received = self.statistics.get('total_received', 0)
            total_displayed = self.statistics.get('total_displayed', 0)
            total_hidden = self.statistics.get('total_hidden', 0)
            hidden_percent = self.statistics.get('hidden_percent', 0.0)
            unique_ids = self.statistics.get('unique_ids', 0)

            total_label = QLabel(f"📊 Total Received: {total_received:,}")
            stats_layout.addWidget(total_label)

            displayed_label = QLabel(
                f"✅ Displayed: {total_displayed:,} ({100 - float(hidden_percent):.1f}%)"
            )
            displayed_label.setStyleSheet("color: #4CAF50;")
            stats_layout.addWidget(displayed_label)

            hidden_label = QLabel(
                f"🚫 Hidden: {total_hidden:,} ({float(hidden_percent):.1f}%)"
            )
            hidden_label.setStyleSheet("color: #FF9800;")
            stats_layout.addWidget(hidden_label)

            unique_label = QLabel(f"🔢 Unique IDs: {unique_ids}")
            stats_layout.addWidget(unique_label)
        else:
            stats_layout.addWidget(QLabel("No statistics yet (enable Diff and receive traffic)."))

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self._restore_defaults
        )
        layout.addWidget(button_box)
        
        # Initial state
        self._on_enable_changed()

        # Set initial mode selection
        mode = (getattr(self.current_config, 'mode', 'filter') or 'filter').strip().lower()
        if mode == 'highlight':
            self.mode_combo.setCurrentText("Highlight only")
        elif mode == 'both':
            self.mode_combo.setCurrentText("Both")
        else:
            self.mode_combo.setCurrentText("Filter (hide repeated)")

        # Auto-save changes to config.json (keeps "normal" defaults, but persists manual tweaks).
        self._connect_autosave_signals()
    
    def _set_initial_byte_mask(self):
        """Set initial byte mask combo value based on config"""
        mask = self.current_config.byte_mask
        
        if mask == "all":
            self.byte_mask_combo.setCurrentText("all")
        elif mask == "0-3":
            self.byte_mask_combo.setCurrentText("0-3 (first 4 bytes)")
        elif mask == "0-7":
            self.byte_mask_combo.setCurrentText("0-7 (all 8 bytes)")
        else:
            self.byte_mask_combo.setCurrentText("custom")
            self.custom_mask_input.setText(mask)
            self.custom_mask_widget.setVisible(True)
    
    def _on_enable_changed(self):
        """Handle enable checkbox state change"""
        enabled = self.enable_check.isChecked()
        
        # Enable/disable all controls
        self.mode_combo.setEnabled(enabled)
        self.min_rate_spin.setEnabled(enabled)
        self.min_bytes_spin.setEnabled(enabled)
        self.time_window_spin.setEnabled(enabled)
        self.max_suppress_spin.setEnabled(enabled)
        self.compare_channel_check.setEnabled(enabled)
        self.byte_mask_combo.setEnabled(enabled)
        self.custom_mask_input.setEnabled(enabled)
        self._schedule_autosave()
    
    def _on_mask_changed(self, text: str):
        """Handle byte mask combo change"""
        is_custom = text == "custom"
        self.custom_mask_widget.setVisible(is_custom)
        self._schedule_autosave()
    
    def _restore_defaults(self):
        """Restore default settings"""
        default_config = DiffConfig()
        self.enable_check.setChecked(default_config.enabled)
        self.mode_combo.setCurrentText("Filter (hide repeated)")
        self.min_rate_spin.setValue(default_config.min_message_rate)
        self.min_bytes_spin.setValue(default_config.min_bytes_changed)
        self.time_window_spin.setValue(getattr(default_config, 'time_window_ms', 500))
        self.max_suppress_spin.setValue(getattr(default_config, 'max_suppress_ms', 1000))
        self.compare_channel_check.setChecked(default_config.compare_by_channel)
        self.byte_mask_combo.setCurrentText("all")
        self.custom_mask_input.setText("")
        self._schedule_autosave()

    def _save_custom_preset(self):
        # Preset system removed by request. Kept as no-op for compatibility if called.
        return

    def _connect_autosave_signals(self):
        """Connect UI signals that should persist config automatically."""
        from PyQt6.QtCore import QTimer
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._persist_to_parent_config)

        self.enable_check.stateChanged.connect(lambda *_: self._schedule_autosave())
        self.mode_combo.currentTextChanged.connect(lambda *_: self._schedule_autosave())
        self.min_rate_spin.valueChanged.connect(lambda *_: self._schedule_autosave())
        self.min_bytes_spin.valueChanged.connect(lambda *_: self._schedule_autosave())
        self.time_window_spin.valueChanged.connect(lambda *_: self._schedule_autosave())
        self.max_suppress_spin.valueChanged.connect(lambda *_: self._schedule_autosave())
        self.compare_channel_check.stateChanged.connect(lambda *_: self._schedule_autosave())
        self.byte_mask_combo.currentTextChanged.connect(lambda *_: self._schedule_autosave())
        self.custom_mask_input.textChanged.connect(lambda *_: self._schedule_autosave())

    def _schedule_autosave(self):
        """Debounced autosave to avoid saving on every keystroke."""
        if self._autosave_timer:
            self._autosave_timer.start(250)

    def _persist_to_parent_config(self):
        """Persist current dialog settings into parent.config['diff_mode']."""
        parent = self.parent()
        cfg = getattr(parent, 'config', None) if parent else None
        cfg_mgr = getattr(parent, 'config_manager', None) if parent else None
        if not isinstance(cfg, dict) or cfg_mgr is None:
            return

        cfg['diff_mode'] = self.get_config().to_dict()
        cfg_mgr.save(cfg)

    
    def get_config(self) -> DiffConfig:
        """
        Get the configured DiffConfig
        
        Returns:
            DiffConfig with user settings
        """
        config = DiffConfig()
        config.enabled = self.enable_check.isChecked()
        mode_text = self.mode_combo.currentText()
        if mode_text == "Highlight only":
            config.mode = "highlight"
        elif mode_text == "Both":
            config.mode = "both"
        else:
            config.mode = "filter"
        config.min_message_rate = self.min_rate_spin.value()
        config.min_bytes_changed = self.min_bytes_spin.value()
        config.time_window_ms = self.time_window_spin.value()
        config.max_suppress_ms = self.max_suppress_spin.value()
        config.compare_by_channel = self.compare_channel_check.isChecked()
        
        # Get byte mask
        mask_text = self.byte_mask_combo.currentText()
        if mask_text == "all":
            config.byte_mask = "all"
        elif mask_text == "0-3 (first 4 bytes)":
            config.byte_mask = "0-3"
        elif mask_text == "0-7 (all 8 bytes)":
            config.byte_mask = "0-7"
        elif mask_text == "custom":
            config.byte_mask = self.custom_mask_input.text().strip() or "all"
        else:
            config.byte_mask = "all"
        
        return config
