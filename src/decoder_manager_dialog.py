"""
Decoder Manager Dialog - Interface para gerenciar protocol decoders
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView, QCheckBox, QTextEdit,
    QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from .protocol_decoder import get_decoder_manager


class DecoderManagerDialog(QDialog):
    """Dialog to manage protocol decoders"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Protocol Decoder Manager")
        self.resize(800, 600)
        
        self.decoder_manager = get_decoder_manager()
        
        self._setup_ui()
        self._load_decoders()
        self._refresh_stats()  # Carrega stats iniciais
    
    def _setup_ui(self):
        """Configura interface"""
        layout = QVBoxLayout()
        
        # Informação
        info_label = QLabel(
            "Manage protocol decoders to automatically decode CAN messages.\n"
            "Enable/disable decoders based on the protocols you're working with."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Tabela de decoders
        decoders_group = QGroupBox("Available Protocol Decoders")
        decoders_layout = QVBoxLayout()
        
        self.decoders_table = QTableWidget()
        self.decoders_table.setColumnCount(5)
        self.decoders_table.setHorizontalHeaderLabels([
            "Enabled", "Protocol", "Description", "Priority", "Stats"
        ])
        
        header = self.decoders_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.decoders_table.itemChanged.connect(self._on_table_changed)
        decoders_layout.addWidget(self.decoders_table)
        
        decoders_group.setLayout(decoders_layout)
        layout.addWidget(decoders_group)
        
        # Estatísticas
        stats_group = QGroupBox("Decoder Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)
        stats_layout.addWidget(self.stats_text)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Botões
        buttons_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Stats")
        refresh_btn.clicked.connect(self._refresh_stats)
        buttons_layout.addWidget(refresh_btn)
        
        reset_btn = QPushButton("Reset Stats")
        reset_btn.clicked.connect(self._reset_stats)
        buttons_layout.addWidget(reset_btn)
        
        buttons_layout.addStretch()
        
        enable_all_btn = QPushButton("Enable All")
        enable_all_btn.clicked.connect(lambda: self._toggle_all(True))
        buttons_layout.addWidget(enable_all_btn)
        
        disable_all_btn = QPushButton("Disable All")
        disable_all_btn.clicked.connect(lambda: self._toggle_all(False))
        buttons_layout.addWidget(disable_all_btn)
        
        buttons_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _load_decoders(self):
        """Carrega lista de decoders"""
        decoders = self.decoder_manager.get_all_decoders()
        stats = self.decoder_manager.get_stats()
        
        self.decoders_table.setRowCount(len(decoders))
        
        # Bloqueia sinais temporariamente
        self.decoders_table.blockSignals(True)
        
        for row, decoder in enumerate(decoders):
            # Checkbox para enabled
            checkbox = QCheckBox()
            checkbox.setChecked(decoder.is_enabled())
            checkbox.stateChanged.connect(lambda state, d=decoder: d.set_enabled(state == Qt.CheckState.Checked.value))
            
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            
            self.decoders_table.setCellWidget(row, 0, checkbox_widget)
            
            # Nome
            name_item = QTableWidgetItem(decoder.get_name())
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.decoders_table.setItem(row, 1, name_item)
            
            # Descrição
            desc_item = QTableWidgetItem(decoder.get_description())
            desc_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.decoders_table.setItem(row, 2, desc_item)
            
            # Prioridade
            priority_item = QTableWidgetItem(decoder.get_priority().name)
            priority_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.decoders_table.setItem(row, 3, priority_item)
            
            # Estatísticas
            decoder_stats = stats.get(decoder.get_name(), {})
            decoded = decoder_stats.get('decoded', 0)
            total = decoder_stats.get('total', 0)
            success_rate = decoder_stats.get('success_rate', 0.0)
            
            stats_str = f"{decoded}/{total} ({success_rate:.1f}%)"
            stats_item = QTableWidgetItem(stats_str)
            stats_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            # Cor baseada na taxa de sucesso
            if success_rate >= 80:
                stats_item.setForeground(QColor(0, 150, 0))
            elif success_rate >= 50:
                stats_item.setForeground(QColor(200, 150, 0))
            elif total > 0:
                stats_item.setForeground(QColor(200, 0, 0))
            
            self.decoders_table.setItem(row, 4, stats_item)
        
        # Reativa sinais
        self.decoders_table.blockSignals(False)
    
    def _refresh_stats(self):
        """Update detailed statistics"""
        stats = self.decoder_manager.get_stats()
        
        lines = []
        lines.append("=== Decoder Statistics ===\n")
        
        for name, decoder_stats in stats.items():
            decoded = decoder_stats['decoded']
            failed = decoder_stats['failed']
            total = decoder_stats['total']
            success_rate = decoder_stats['success_rate']
            avg_confidence = decoder_stats['avg_confidence']
            
            lines.append(f"{name}:")
            lines.append(f"  • Messages decoded: {decoded}")
            lines.append(f"  • Messages failed: {failed}")
            lines.append(f"  • Total attempts: {total}")
            lines.append(f"  • Success rate: {success_rate:.1f}%")
            lines.append(f"  • Avg confidence: {avg_confidence:.2f}")
            lines.append("")
        
        if not stats:
            lines.append("No statistics available yet.")
        
        self.stats_text.setText("\n".join(lines))
    
    def _reset_stats(self):
        """Reset statistics"""
        self.decoder_manager.reset_stats()
        self._refresh_stats()
    
    def _toggle_all(self, enabled: bool):
        """Habilita/desabilita todos os decoders"""
        for decoder in self.decoder_manager.get_all_decoders():
            decoder.set_enabled(enabled)
        
        # Atualiza apenas os checkboxes
        for row in range(self.decoders_table.rowCount()):
            checkbox_widget = self.decoders_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(enabled)
                    checkbox.blockSignals(False)
    
    def _on_table_changed(self, item):
        """Callback quando tabela muda"""
        # Atualiza estatísticas se necessário
        pass
