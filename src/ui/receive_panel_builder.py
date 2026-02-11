"""
Receive Panel Builder

Builds the receive panel UI with table and controls.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QPushButton, QLabel, QWidget, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ReceivePanelBuilder:
    """Builds receive panel UI"""
    
    @staticmethod
    def create_panel(parent, colors, callbacks):
        """
        Create receive panel with table and controls
        
        Args:
            parent: Parent window
            colors: Color dictionary
            callbacks: Dictionary with callback functions
            
        Returns:
            Tuple of (group_box, table, container_layout, tracer_controls_widget)
        """
        from ..i18n import t
        
        receive_group = QGroupBox("Receive (Monitor)")
        receive_layout = QVBoxLayout()
        
        # Container for table (allows switching between single/split view)
        receive_container = QWidget()
        receive_container_layout = QVBoxLayout(receive_container)
        receive_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create table
        receive_table = ReceivePanelBuilder._create_table(parent, callbacks)
        receive_container_layout.addWidget(receive_table)
        receive_layout.addWidget(receive_container)
        
        # Tracer playback controls
        tracer_controls_widget = ReceivePanelBuilder._create_tracer_controls(parent, callbacks)
        receive_layout.addWidget(tracer_controls_widget)
        
        receive_group.setLayout(receive_layout)
        
        return receive_group, receive_table, receive_container_layout, tracer_controls_widget
    
    @staticmethod
    def _create_table(parent, callbacks):
        """Create receive table"""
        table = QTableWidget()
        
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(callbacks['show_context_menu'])
        
        font_rx = QFont("Courier New", 14)
        table.setFont(font_rx)
        
        return table
    
    @staticmethod
    def _create_tracer_controls(parent, callbacks):
        """Create tracer playback controls"""
        tracer_controls_widget = QWidget()
        tracer_controls_layout = QHBoxLayout(tracer_controls_widget)
        tracer_controls_layout.setContentsMargins(0, 5, 0, 5)
        
        # Channel selector dropdown (only visible when multiple channels are connected)
        parent.tracer_channel_label = QLabel("Channel:")
        parent.tracer_channel_label.setVisible(False)
        tracer_controls_layout.addWidget(parent.tracer_channel_label)
        
        parent.tracer_channel_combo = QComboBox()
        parent.tracer_channel_combo.setToolTip("Select channel to trace (ALL = all channels)")
        parent.tracer_channel_combo.addItem("ALL")
        parent.tracer_channel_combo.setVisible(False)
        parent.tracer_channel_combo.setMinimumWidth(100)
        tracer_controls_layout.addWidget(parent.tracer_channel_combo)
        
        tracer_controls_layout.addWidget(QLabel("|"))
        
        # Record button
        parent.btn_record = QPushButton("⏺ Record")
        parent.btn_record.setCheckable(True)
        parent.btn_record.setToolTip("Gravar mensagens para reprodução posterior")
        parent.btn_record.clicked.connect(callbacks['toggle_recording'])
        tracer_controls_layout.addWidget(parent.btn_record)
        
        # Clear button
        parent.btn_clear_tracer = QPushButton("🗑 Clear")
        parent.btn_clear_tracer.setToolTip("Limpar mensagens gravadas")
        parent.btn_clear_tracer.clicked.connect(callbacks['clear_tracer'])
        tracer_controls_layout.addWidget(parent.btn_clear_tracer)
        
        tracer_controls_layout.addWidget(QLabel("|"))
        
        # Play All button (becomes Pause during playback)
        parent.btn_play_all = QPushButton("▶ Play All")
        parent.btn_play_all.setCheckable(True)
        parent.btn_play_all.setToolTip("Reproduzir todas as mensagens gravadas")
        parent.btn_play_all.clicked.connect(callbacks['play_all'])
        parent.btn_play_all.setEnabled(False)
        tracer_controls_layout.addWidget(parent.btn_play_all)
        
        # Play Selected button
        parent.btn_play_selected = QPushButton("▶ Play Selected")
        parent.btn_play_selected.setToolTip("Reproduzir mensagens selecionadas")
        parent.btn_play_selected.clicked.connect(callbacks['play_selected'])
        parent.btn_play_selected.setEnabled(False)
        tracer_controls_layout.addWidget(parent.btn_play_selected)
        
        # Stop button
        parent.btn_stop_play = QPushButton("⏹ Stop")
        parent.btn_stop_play.setToolTip("Parar reprodução")
        parent.btn_stop_play.clicked.connect(callbacks['stop_playback'])
        parent.btn_stop_play.setEnabled(False)
        tracer_controls_layout.addWidget(parent.btn_stop_play)
        
        tracer_controls_layout.addWidget(QLabel("|"))
        
        # Save Trace button
        parent.btn_save_trace = QPushButton("💾 Save")
        parent.btn_save_trace.setToolTip("Salvar trace atual")
        parent.btn_save_trace.clicked.connect(callbacks['save_trace'])
        tracer_controls_layout.addWidget(parent.btn_save_trace)
        
        # Load Trace button
        parent.btn_load_trace = QPushButton("📂 Load")
        parent.btn_load_trace.setToolTip("Carregar trace de arquivo")
        parent.btn_load_trace.clicked.connect(callbacks['load_trace'])
        tracer_controls_layout.addWidget(parent.btn_load_trace)
        
        tracer_controls_layout.addStretch()
        
        # Playback status label
        parent.playback_label = QLabel("")
        tracer_controls_layout.addWidget(parent.playback_label)
        
        tracer_controls_widget.setVisible(False)
        
        return tracer_controls_widget
