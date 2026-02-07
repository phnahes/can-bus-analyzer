"""
Baudrate Detection Dialog - Interface gráfica para detecção automática de baudrate
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Optional
from .baudrate_detector import BaudrateDetector, BaudrateDetectionResult


class DetectionThread(QThread):
    """Thread for baudrate detection in background"""
    
    progress = pyqtSignal(int, str)  # baudrate, status
    finished = pyqtSignal(object)  # BaudrateDetectionResult
    
    def __init__(self, channel: str, interface: str, quick: bool = False):
        super().__init__()
        self.channel = channel
        self.interface = interface
        self.quick = quick
    
    def run(self):
        """Run detection"""
        detector = BaudrateDetector(self.channel, self.interface)
        
        def callback(baudrate, status):
            self.progress.emit(baudrate, status)
        
        if self.quick:
            result = detector.detect(
                baudrates=[500000, 1000000, 250000],
                timeout_per_baudrate=1.5,
                min_messages=3,
                callback=callback
            )
        else:
            result = detector.detect(callback=callback)
        
        self.finished.emit(result)


class BaudrateDetectDialog(QDialog):
    """Dialog for automatic baudrate detection"""
    
    def __init__(self, parent=None, channel: str = 'can0', interface: str = 'socketcan'):
        super().__init__(parent)
        self.setWindowTitle("Auto-Detect Baudrate")
        self.resize(600, 500)
        
        self.channel = channel
        self.interface = interface
        self.detected_baudrate: Optional[int] = None
        self.detection_thread: Optional[DetectionThread] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura interface"""
        layout = QVBoxLayout()
        
        # Informações
        info_group = QGroupBox("Detection Settings")
        info_layout = QVBoxLayout()
        
        # Channel
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("<b>Channel:</b>"))
        self.channel_label = QLabel(self.channel)
        channel_layout.addWidget(self.channel_label)
        channel_layout.addStretch()
        info_layout.addLayout(channel_layout)
        
        # Interface
        interface_layout = QHBoxLayout()
        interface_layout.addWidget(QLabel("<b>Interface:</b>"))
        self.interface_label = QLabel(self.interface)
        interface_layout.addWidget(self.interface_label)
        interface_layout.addStretch()
        info_layout.addLayout(interface_layout)
        
        # Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("<b>Mode:</b>"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Quick (3 common baudrates)", "Full (7 baudrates)"])
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        info_layout.addLayout(mode_layout)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Status
        status_group = QGroupBox("Detection Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready to start detection")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 7)  # Máximo 7 baudrates
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Log
        log_group = QGroupBox("Detection Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 10))
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Resultado
        self.result_group = QGroupBox("Detection Result")
        result_layout = QVBoxLayout()
        
        self.result_label = QLabel("No detection performed yet")
        self.result_label.setWordWrap(True)
        self.result_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        result_layout.addWidget(self.result_label)
        
        self.result_group.setLayout(result_layout)
        self.result_group.setVisible(False)
        layout.addWidget(self.result_group)
        
        # Botões
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🔍 Start Detection")
        self.start_btn.clicked.connect(self._start_detection)
        buttons_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel_detection)
        self.cancel_btn.setEnabled(False)
        buttons_layout.addWidget(self.cancel_btn)
        
        buttons_layout.addStretch()
        
        self.use_btn = QPushButton("✅ Use This Baudrate")
        self.use_btn.clicked.connect(self.accept)
        self.use_btn.setEnabled(False)
        buttons_layout.addWidget(self.use_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _start_detection(self):
        """Start detection"""
        # Limpa log
        self.log_text.clear()
        self.result_group.setVisible(False)
        
        # Atualiza UI
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.use_btn.setEnabled(False)
        self.mode_combo.setEnabled(False)
        
        # Determina modo
        quick = self.mode_combo.currentIndex() == 0
        max_baudrates = 3 if quick else 7
        self.progress_bar.setRange(0, max_baudrates)
        self.progress_bar.setValue(0)
        
        self._log("🚀 Starting baudrate detection...")
        self._log(f"   Channel: {self.channel}")
        self._log(f"   Interface: {self.interface}")
        self._log(f"   Mode: {'Quick' if quick else 'Full'}")
        self._log("")
        
        # Inicia thread de detecção
        self.detection_thread = DetectionThread(self.channel, self.interface, quick)
        self.detection_thread.progress.connect(self._on_progress)
        self.detection_thread.finished.connect(self._on_finished)
        self.detection_thread.start()
    
    def _cancel_detection(self):
        """Cancel detection"""
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.terminate()
            self.detection_thread.wait()
            
            self._log("")
            self._log("❌ Detection cancelled by user")
            
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.mode_combo.setEnabled(True)
            self.status_label.setText("Detection cancelled")
    
    def _on_progress(self, baudrate: int, status: str):
        """Atualiza progresso"""
        if status == 'testing':
            self._log(f"🔍 Testing {baudrate:7d} bps...", end='')
            self.status_label.setText(f"Testing {baudrate} bps...")
            self.progress_bar.setValue(self.progress_bar.value() + 1)
        
        elif status == 'found':
            self._log(" ✅ FOUND!")
            self.status_label.setText(f"Baudrate found: {baudrate} bps")
        
        elif status == 'failed':
            self._log(" ❌")
    
    def _on_finished(self, result: BaudrateDetectionResult):
        """Detection finished"""
        self._log("")
        self._log("=" * 50)
        
        if result.baudrate:
            self._log(f"✅ Baudrate detected: {result.baudrate} bps")
            self._log(f"   Confidence: {result.confidence * 100:.1f}%")
            self._log(f"   Messages received: {result.messages_received}")
            self._log(f"   Detection time: {result.detection_time:.2f}s")
            
            self.detected_baudrate = result.baudrate
            
            # Atualiza resultado
            self.result_label.setText(
                f"✅ Detected: {result.baudrate:,} bps\n"
                f"Confidence: {result.confidence * 100:.1f}% "
                f"({result.messages_received} messages)"
            )
            self.result_label.setStyleSheet("color: green;")
            self.result_group.setVisible(True)
            
            self.use_btn.setEnabled(True)
            self.status_label.setText(f"✅ Detection successful: {result.baudrate} bps")
        
        else:
            self._log("❌ No baudrate detected")
            self._log(f"   Tested: {', '.join(str(b) for b in result.tested_baudrates)}")
            self._log(f"   Detection time: {result.detection_time:.2f}s")
            
            # Atualiza resultado
            self.result_label.setText(
                "❌ No baudrate detected\n"
                "Make sure the CAN bus is active and has traffic"
            )
            self.result_label.setStyleSheet("color: red;")
            self.result_group.setVisible(True)
            
            self.status_label.setText("❌ Detection failed")
        
        self._log("=" * 50)
        
        # Atualiza UI
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.mode_combo.setEnabled(True)
    
    def _log(self, message: str, end: str = '\n'):
        """Adiciona mensagem ao log"""
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message + end)
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
    
    def get_detected_baudrate(self) -> Optional[int]:
        """Retorna baudrate detectado"""
        return self.detected_baudrate
    
    @staticmethod
    def detect(parent=None, channel: str = 'can0', interface: str = 'socketcan') -> Optional[int]:
        """
        Método estático para detecção rápida
        
        Returns:
            Baudrate detectado ou None se cancelado/não detectado
        """
        dialog = BaudrateDetectDialog(parent, channel, interface)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_detected_baudrate()
        
        return None
