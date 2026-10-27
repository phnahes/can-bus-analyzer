"""Interface setup dialog (headless)."""

from PyQt6.QtGui import QGuiApplication

from src.dialogs.interface_setup_dialog import InterfaceSetupDialog

REQUEST = {
    "channel": "can2",
    "bitrate": 500000,
    "dbitrate": 0,
    "fd": False,
    "listen_only": False,
    "command": "sudo ip link set dev can2 up type can bitrate 500000",
    "detail": "can2 is DOWN",
}


def test_dialog_shows_command_and_starts_unconfigured(qapp):
    dialog = InterfaceSetupDialog([REQUEST], parent=None)

    assert dialog.configured is False
    assert dialog.btn_up.text()  # button rendered with an i18n label


def test_copy_puts_command_on_the_clipboard(qapp):
    dialog = InterfaceSetupDialog([REQUEST], parent=None)

    dialog._copy_commands()

    assert "ip link set dev can2 up" in QGuiApplication.clipboard().text()


def test_bring_up_reports_failures_without_closing(qapp, monkeypatch):
    dialog = InterfaceSetupDialog([REQUEST], parent=None)

    monkeypatch.setattr(
        "src.dialogs.interface_setup_dialog.bring_up",
        lambda *a, **kw: (False, "permission denied", ["ip", "link"]),
    )
    monkeypatch.setattr(
        "src.dialogs.interface_setup_dialog.QMessageBox.warning",
        lambda *a, **kw: None,
    )

    dialog._bring_up()

    assert dialog.configured is False


def test_bring_up_marks_configured_on_success(qapp, monkeypatch):
    dialog = InterfaceSetupDialog([REQUEST], parent=None)

    monkeypatch.setattr(
        "src.dialogs.interface_setup_dialog.bring_up",
        lambda *a, **kw: (True, "", ["ip", "link"]),
    )

    dialog._bring_up()

    assert dialog.configured is True
