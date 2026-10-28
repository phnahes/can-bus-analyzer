"""
Interface Setup Dialog

Shown when a SocketCAN interface is down (or not configured as requested).
Offers the exact ``ip link`` command, a copy button, and an opt-in
"bring it up now" that runs through pkexec so the user gets the desktop
authorization prompt instead of the app running sudo behind their back.
"""

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..can_interface_setup import bring_up
from ..i18n import t


class InterfaceSetupDialog(QDialog):
    """Let the user configure/bring up one or more CAN interfaces."""

    def __init__(self, requests: List[Dict], parent=None):
        """
        Args:
            requests: list of dicts with channel, bitrate, command, detail and
                optional dbitrate/fd/listen_only.
        """
        super().__init__(parent)
        self.requests = requests or []
        self.configured = False

        self.setWindowTitle(t('iface_setup_title'))
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)

        info = QLabel(t('iface_setup_info'))
        info.setWordWrap(True)
        layout.addWidget(info)

        for request in self.requests:
            layout.addWidget(self._build_request_widget(request))

        root_note = QLabel(t('iface_setup_needs_root'))
        root_note.setWordWrap(True)
        root_note.setStyleSheet("color: palette(mid);")
        layout.addWidget(root_note)

        buttons = QDialogButtonBox()
        self.btn_copy = QPushButton(t('iface_setup_copy'))
        self.btn_copy.clicked.connect(self._copy_commands)
        buttons.addButton(self.btn_copy, QDialogButtonBox.ButtonRole.ActionRole)

        self.btn_up = QPushButton(t('iface_setup_bring_up'))
        self.btn_up.clicked.connect(self._bring_up)
        buttons.addButton(self.btn_up, QDialogButtonBox.ButtonRole.AcceptRole)

        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_request_widget(self, request: Dict) -> QWidget:
        container = QWidget()
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 8, 0, 8)

        title = QLabel(f"<b>{request.get('channel', 'CAN')}</b>")
        box.addWidget(title)

        detail = request.get('detail') or ''
        if detail:
            detail_label = QLabel(detail)
            detail_label.setWordWrap(True)
            box.addWidget(detail_label)

        command = request.get('command') or ''
        if command:
            command_box = QPlainTextEdit(command)
            command_box.setReadOnly(True)
            command_box.setFixedHeight(48)
            command_box.setFont(QFont("Courier New", 11))
            command_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            box.addWidget(command_box)

        return container

    def _copy_commands(self):
        text = "\n".join(
            request.get('command', '') for request in self.requests if request.get('command')
        )
        QGuiApplication.clipboard().setText(text)

    def _bring_up(self):
        failures = []
        for request in self.requests:
            ok, output, argv = bring_up(
                request['channel'],
                int(request.get('bitrate') or 500000),
                dbitrate=request.get('dbitrate') or None,
                fd=bool(request.get('fd')),
                listen_only=bool(request.get('listen_only')),
            )
            if not ok:
                request['detail'] = output or t('iface_setup_failed', channel=request['channel'],
                                                 detail='unknown error')
                failures.append(request)

        if failures:
            details = "\n\n".join(
                f"{item['channel']}: {item.get('detail', '')}" for item in failures
            )
            QMessageBox.warning(
                self,
                t('iface_setup_title'),
                f"{t('iface_setup_failed_hint')}\n\n{details}",
            )
            return

        self.configured = True
        self.accept()
