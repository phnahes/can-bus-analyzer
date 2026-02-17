"""
Toolbar Builder
Builds the main toolbar with connection and mode controls
"""

from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QLabel


class ToolbarBuilder:
    """Builds the main application toolbar"""
    
    @staticmethod
    def create_toolbar(parent) -> QHBoxLayout:
        """Create toolbar with connection and mode controls
        
        Args:
            parent: The parent window (main_window)
            
        Returns:
            QHBoxLayout: The toolbar layout with all buttons configured
        """
        toolbar_layout = QHBoxLayout()
        
        # Connect button
        parent.btn_connect = QPushButton()
        parent.btn_connect.clicked.connect(parent.toggle_connection)
        toolbar_layout.addWidget(parent.btn_connect)
        
        # Disconnect button
        parent.btn_disconnect = QPushButton()
        parent.btn_disconnect.clicked.connect(parent.disconnect)
        parent.btn_disconnect.setEnabled(False)
        toolbar_layout.addWidget(parent.btn_disconnect)
        
        # Reset button
        parent.btn_reset = QPushButton()
        parent.btn_reset.clicked.connect(parent.reset)
        toolbar_layout.addWidget(parent.btn_reset)
        
        toolbar_layout.addWidget(QLabel("|"))
        
        # Pause button (hidden for now)
        parent.btn_pause = QPushButton()
        parent.btn_pause.clicked.connect(parent.toggle_pause)
        parent.btn_pause.setEnabled(False)
        parent.btn_pause.setVisible(False)
        toolbar_layout.addWidget(parent.btn_pause)
        
        # Tracer mode toggle
        parent.btn_tracer = QPushButton()
        parent.btn_tracer.setCheckable(True)
        parent.btn_tracer.clicked.connect(parent.toggle_tracer_mode)
        toolbar_layout.addWidget(parent.btn_tracer)
        
        toolbar_layout.addWidget(QLabel("|"))
        
        # Gateway toggle
        parent.btn_gateway = QPushButton("🌉 Gateway: OFF")
        parent.btn_gateway.setCheckable(True)
        parent.btn_gateway.setToolTip("Enable/Disable CAN Gateway")
        parent.btn_gateway.clicked.connect(parent.toggle_gateway_from_toolbar)
        parent.btn_gateway.setEnabled(False)
        toolbar_layout.addWidget(parent.btn_gateway)
        
        # Diff Mode toggle (Monitor mode only)
        parent.btn_diff = QPushButton("🔍 Diff: OFF")
        parent.btn_diff.setCheckable(True)
        parent.btn_diff.setToolTip("Enable/Disable Diff Mode (Monitor only - hides repeated messages)")
        parent.btn_diff.clicked.connect(parent.toggle_diff_mode)
        parent.btn_diff.setEnabled(False)  # Enabled only in Monitor mode
        toolbar_layout.addWidget(parent.btn_diff)
        
        toolbar_layout.addStretch()
        
        # Toggle transmit panel visibility
        parent.btn_toggle_transmit = QPushButton("📤 Hide TX")
        parent.btn_toggle_transmit.setToolTip("Mostrar/Ocultar painel de Transmissão")
        parent.btn_toggle_transmit.clicked.connect(parent.toggle_transmit_panel)
        toolbar_layout.addWidget(parent.btn_toggle_transmit)
        parent.transmit_panel_visible = True
        
        return toolbar_layout
