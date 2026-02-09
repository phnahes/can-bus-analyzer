#!/usr/bin/env python3
"""
FuelTech SwitchPanel Viewer and Controller

Interactive GUI tool for visualizing and controlling FuelTech SwitchPanel devices.
Displays button states and allows RGB LED control.

Usage:
    python switchpanel_viewer.py [--interface INTERFACE] [--bitrate BITRATE]

Requirements:
    - python-can
    - PyQt6
"""

import sys
import struct
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QPushButton, QLabel, QSlider, QSpinBox,
    QComboBox, QTextEdit, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

try:
    import can
except ImportError:
    print("Error: python-can not installed. Run: pip install python-can")
    sys.exit(1)


class SwitchPanelButton(QPushButton):
    """Visual representation of a SwitchPanel button"""
    
    def __init__(self, button_num: int):
        super().__init__(f"Button {button_num}")
        self.button_num = button_num
        self.is_pressed = False
        self.rgb_color = (0, 0, 0)
        
        self.setMinimumSize(100, 80)
        self.setCheckable(True)
        self.update_style()
    
    def set_pressed(self, pressed: bool):
        """Update button pressed state"""
        self.is_pressed = pressed
        self.setChecked(pressed)
        self.update_style()
    
    def set_rgb_color(self, r: int, g: int, b: int):
        """Update button LED color"""
        self.rgb_color = (r, g, b)
        self.update_style()
    
    def update_style(self):
        """Update button visual style"""
        r, g, b = self.rgb_color
        
        # Calculate brightness for text color
        brightness = (r * 0.299 + g * 0.587 + b * 0.114)
        text_color = "white" if brightness < 128 else "black"
        
        # Border style based on pressed state
        border = "3px solid yellow" if self.is_pressed else "1px solid gray"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                color: {text_color};
                border: {border};
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                border: 2px solid white;
            }}
        """)


class RGBControl(QWidget):
    """RGB color control widget"""
    
    colorChanged = pyqtSignal(int, int, int)  # r, g, b
    
    def __init__(self, label: str = "RGB"):
        super().__init__()
        self.init_ui(label)
    
    def init_ui(self, label: str):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label))
        
        # Red slider
        red_layout = QHBoxLayout()
        red_layout.addWidget(QLabel("R:"))
        self.red_slider = QSlider(Qt.Orientation.Horizontal)
        self.red_slider.setRange(0, 255)
        self.red_slider.setValue(0)
        self.red_slider.valueChanged.connect(self.on_color_changed)
        red_layout.addWidget(self.red_slider)
        self.red_spin = QSpinBox()
        self.red_spin.setRange(0, 255)
        self.red_spin.valueChanged.connect(self.red_slider.setValue)
        self.red_slider.valueChanged.connect(self.red_spin.setValue)
        red_layout.addWidget(self.red_spin)
        layout.addLayout(red_layout)
        
        # Green slider
        green_layout = QHBoxLayout()
        green_layout.addWidget(QLabel("G:"))
        self.green_slider = QSlider(Qt.Orientation.Horizontal)
        self.green_slider.setRange(0, 255)
        self.green_slider.setValue(0)
        self.green_slider.valueChanged.connect(self.on_color_changed)
        green_layout.addWidget(self.green_slider)
        self.green_spin = QSpinBox()
        self.green_spin.setRange(0, 255)
        self.green_spin.valueChanged.connect(self.green_slider.setValue)
        self.green_slider.valueChanged.connect(self.green_spin.setValue)
        green_layout.addWidget(self.green_spin)
        layout.addLayout(green_layout)
        
        # Blue slider
        blue_layout = QHBoxLayout()
        blue_layout.addWidget(QLabel("B:"))
        self.blue_slider = QSlider(Qt.Orientation.Horizontal)
        self.blue_slider.setRange(0, 255)
        self.blue_slider.setValue(0)
        self.blue_slider.valueChanged.connect(self.on_color_changed)
        blue_layout.addWidget(self.blue_slider)
        self.blue_spin = QSpinBox()
        self.blue_spin.setRange(0, 255)
        self.blue_spin.valueChanged.connect(self.blue_slider.setValue)
        self.blue_slider.valueChanged.connect(self.blue_spin.setValue)
        blue_layout.addWidget(self.blue_spin)
        layout.addLayout(blue_layout)
        
        # Color preview
        self.preview = QLabel()
        self.preview.setMinimumHeight(30)
        self.preview.setAutoFillBackground(True)
        layout.addWidget(self.preview)
        
        self.setLayout(layout)
        self.update_preview()
    
    def on_color_changed(self):
        """Handle color change"""
        self.update_preview()
        r = self.red_slider.value()
        g = self.green_slider.value()
        b = self.blue_slider.value()
        self.colorChanged.emit(r, g, b)
    
    def update_preview(self):
        """Update color preview"""
        r = self.red_slider.value()
        g = self.green_slider.value()
        b = self.blue_slider.value()
        
        palette = self.preview.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(r, g, b))
        self.preview.setPalette(palette)
    
    def get_rgb(self) -> tuple:
        """Get current RGB values"""
        return (
            self.red_slider.value(),
            self.green_slider.value(),
            self.blue_slider.value()
        )
    
    def set_rgb(self, r: int, g: int, b: int):
        """Set RGB values"""
        self.red_slider.setValue(r)
        self.green_slider.setValue(g)
        self.blue_slider.setValue(b)


class SwitchPanelViewer(QMainWindow):
    """Main SwitchPanel viewer window"""
    
    def __init__(self):
        super().__init__()
        self.bus: Optional[can.Bus] = None
        self.buttons: Dict[int, SwitchPanelButton] = {}
        self.panel_product_id = 0x12200320  # Default: Big 8-button
        self.init_ui()
        self.setup_can()
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("FuelTech SwitchPanel Viewer")
        self.setMinimumSize(900, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Top controls
        top_layout = QHBoxLayout()
        
        # Panel variant selector
        top_layout.addWidget(QLabel("Panel Type:"))
        self.panel_combo = QComboBox()
        self.panel_combo.addItem("Big 8-button", 0x12200320)
        self.panel_combo.addItem("Mini 4-button", 0x12210320)
        self.panel_combo.addItem("Mini 5-button", 0x12218320)
        self.panel_combo.addItem("Mini 8-button", 0x12228320)
        self.panel_combo.currentIndexChanged.connect(self.on_panel_changed)
        top_layout.addWidget(self.panel_combo)
        
        top_layout.addStretch()
        
        # Connection status
        self.status_label = QLabel("Status: Disconnected")
        top_layout.addWidget(self.status_label)
        
        main_layout.addLayout(top_layout)
        
        # Button grid
        button_group = QGroupBox("Button States (RX from Panel)")
        button_layout = QGridLayout()
        
        for i in range(8):
            btn = SwitchPanelButton(i + 1)
            self.buttons[i + 1] = btn
            row = i // 4
            col = i % 4
            button_layout.addWidget(btn, row, col)
        
        button_group.setLayout(button_layout)
        main_layout.addWidget(button_group)
        
        # RGB Control
        rgb_group = QGroupBox("LED Control (TX to Panel)")
        rgb_layout = QHBoxLayout()
        
        self.rgb_control = RGBControl("Global Color")
        self.rgb_control.colorChanged.connect(self.on_rgb_changed)
        rgb_layout.addWidget(self.rgb_control)
        
        # Quick color buttons
        quick_layout = QVBoxLayout()
        quick_layout.addWidget(QLabel("Quick Colors:"))
        
        colors = [
            ("Red", 255, 0, 0),
            ("Green", 0, 255, 0),
            ("Blue", 0, 0, 255),
            ("Yellow", 255, 255, 0),
            ("Cyan", 0, 255, 255),
            ("Magenta", 255, 0, 255),
            ("White", 255, 255, 255),
            ("Off", 0, 0, 0),
        ]
        
        for name, r, g, b in colors:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, r=r, g=g, b=b: self.rgb_control.set_rgb(r, g, b))
            btn.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); color: {'white' if r+g+b < 384 else 'black'};")
            quick_layout.addWidget(btn)
        
        rgb_layout.addLayout(quick_layout)
        rgb_group.setLayout(rgb_layout)
        main_layout.addWidget(rgb_group)
        
        # Log
        log_group = QGroupBox("Message Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_btn)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def setup_can(self):
        """Setup CAN bus connection"""
        try:
            # Try to connect to virtual CAN
            self.bus = can.Bus(interface='socketcan', channel='vcan0', bitrate=1000000)
            self.status_label.setText("Status: Connected (vcan0)")
            self.log("Connected to vcan0")
            
            # Start receiving timer
            self.rx_timer = QTimer()
            self.rx_timer.timeout.connect(self.receive_messages)
            self.rx_timer.start(50)  # 20 Hz
            
        except Exception as e:
            self.status_label.setText(f"Status: Error - {str(e)}")
            self.log(f"CAN Error: {str(e)}")
    
    def on_panel_changed(self, index: int):
        """Handle panel type change"""
        self.panel_product_id = self.panel_combo.currentData()
        self.log(f"Panel type changed to: {self.panel_combo.currentText()} (0x{self.panel_product_id:08X})")
    
    def on_rgb_changed(self, r: int, g: int, b: int):
        """Handle RGB color change"""
        # Update all button previews
        for btn in self.buttons.values():
            btn.set_rgb_color(r, g, b)
        
        # Send LED control message
        self.send_led_control(r, g, b)
    
    def send_led_control(self, r: int, g: int, b: int):
        """Send LED control message to panel (MessageID 0x321)"""
        if not self.bus:
            return
        
        try:
            # CAN ID: ProductID + MessageID 0x321
            can_id = self.panel_product_id | 0x321
            
            # Data: [State1, Dim1, State2, Dim2, R, G, B, R, ...]
            data = [
                0xFF,  # State 1st row (all on)
                0xFF,  # Dimming 1st row (full)
                0xFF,  # State 2nd row (all on)
                0xFF,  # Dimming 2nd row (full)
                r,     # Red button 1
                g,     # Green button 1
                b,     # Blue button 1
                r,     # Red button 2 (simplified - same color for all)
            ]
            
            msg = can.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=True
            )
            
            self.bus.send(msg)
            self.log(f"TX LED Control: RGB({r}, {g}, {b})")
            
        except Exception as e:
            self.log(f"Send error: {str(e)}")
    
    def receive_messages(self):
        """Receive and process CAN messages"""
        if not self.bus:
            return
        
        try:
            msg = self.bus.recv(timeout=0)
            if msg:
                self.process_message(msg)
        except Exception as e:
            pass  # Timeout is normal
    
    def process_message(self, msg: can.Message):
        """Process received CAN message"""
        # Check if it's a SwitchPanel button message (MessageID 0x320)
        message_id = msg.arbitration_id & 0x7FF
        
        if message_id == 0x320:
            self.process_button_states(msg.data)
    
    def process_button_states(self, data: bytes):
        """Process button state message"""
        if len(data) < 8:
            return
        
        # Decode button states
        row1_state = data[0]
        row2_state = data[1]
        
        # Update button 1-4 (row 1)
        for i in range(4):
            button_num = i + 1
            pressed = bool(row1_state & (1 << i))
            if button_num in self.buttons:
                self.buttons[button_num].set_pressed(pressed)
        
        # Update buttons 5-8 (row 2)
        for i in range(4):
            button_num = i + 5
            pressed = bool(row2_state & (1 << i))
            if button_num in self.buttons:
                self.buttons[button_num].set_pressed(pressed)
        
        self.log(f"RX Button States: Row1=0x{row1_state:02X}, Row2=0x{row2_state:02X}")
    
    def log(self, message: str):
        """Add message to log"""
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.bus:
            self.bus.shutdown()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    viewer = SwitchPanelViewer()
    viewer.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
