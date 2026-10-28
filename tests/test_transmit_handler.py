"""Listen Only must never look like a successful transmission."""

import types

import pytest

from src import can_bus_manager as cbm
from src.handlers.transmit_handler import TransmitHandler
from src.logger import get_logger


class FakeBus:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)

    def recv(self, timeout=None):
        return None

    def shutdown(self):
        pass


def make_manager(buses):
    """buses: [(name, listen_only)]"""
    manager = cbm.CANBusManager()
    for name, listen_only in buses:
        manager.add_bus(
            cbm.CANBusConfig(name=name, channel="can0", baudrate=500000, listen_only=listen_only)
        )
        instance = manager.buses[name]
        instance.connected = True
        instance.bus = FakeBus()
    return manager


def make_handler(buses):
    return TransmitHandler(parent_window=None, can_bus_manager=make_manager(buses))


MESSAGE = {"id": 0x100, "dlc": 1, "data": b"\x01", "extended": False, "is_rtr": False}


@pytest.fixture
def warned(monkeypatch):
    """Record logger.warning calls without touching the real log file."""
    calls = []

    def fake_warning(message, *args, **kwargs):
        calls.append(message)

    logger = get_logger()
    monkeypatch.setattr(logger, "warning", fake_warning)
    return calls


def test_send_all_buses_listen_only_is_refused(warned):
    handler = make_handler([("CAN1", True), ("CAN2", True)])

    assert handler.send_single(MESSAGE) is False
    assert handler.last_send_error == "listen-only"
    assert handler.last_blocked_buses == ["CAN1", "CAN2"]
    assert handler.can_bus_manager.buses["CAN1"].bus.sent == []
    assert handler.can_bus_manager.buses["CAN2"].bus.sent == []


def test_send_targeting_listen_only_bus_is_refused(warned):
    handler = make_handler([("CAN1", True), ("CAN2", False)])

    assert handler.send_single(MESSAGE, target_bus="CAN1") is False
    assert handler.last_send_error == "listen-only"
    assert handler.can_bus_manager.buses["CAN2"].bus.sent == []


def test_mixed_buses_send_only_on_the_normal_one(warned):
    handler = make_handler([("CAN1", True), ("CAN2", False)])

    assert handler.send_single(MESSAGE) is True
    assert handler.last_send_error is None
    assert handler.last_blocked_buses == ["CAN1"]
    assert handler.can_bus_manager.buses["CAN1"].bus.sent == []
    assert len(handler.can_bus_manager.buses["CAN2"].bus.sent) == 1


def test_blocked_warning_is_rate_limited(warned):
    handler = make_handler([("CAN1", True)])

    for _ in range(5):
        handler.send_single(MESSAGE)

    assert len(warned) == 1  # not one line per periodic frame


def test_periodic_is_refused_when_all_buses_listen_only(warned):
    handler = make_handler([("CAN1", True)])

    assert handler.start_periodic(0, 100, dict(MESSAGE)) is False
    assert handler.last_send_error == "listen-only"
    assert handler.periodic_threads == {}


def test_periodic_runs_with_one_normal_bus(warned):
    handler = make_handler([("CAN1", True), ("CAN2", False)])

    assert handler.start_periodic(0, 50, dict(MESSAGE)) is True
    try:
        assert 0 in handler.periodic_threads
    finally:
        handler.stop_periodic(0)


# ---------------------------------------------------------------------------
# UI reporting helpers (no Qt window needed)
# ---------------------------------------------------------------------------


class WindowStub:
    def __init__(self):
        self.notifications = []
        self._lo_notified = set()
        self.transmit_handler = types.SimpleNamespace(
            last_blocked_buses=[], last_send_error=None
        )

    def show_notification(self, text, duration=0):
        self.notifications.append(text)

    def _notify_listen_only_blocked(self, buses):
        # Mirrors the real method so _handle_send_result can call it.
        from src.main_window import CANAnalyzerWindow

        CANAnalyzerWindow._notify_listen_only_blocked(self, buses)


def test_listen_only_notification_is_sent_once_per_bus():
    from src.main_window import CANAnalyzerWindow

    window = WindowStub()

    CANAnalyzerWindow._notify_listen_only_blocked(window, ["CAN1"])
    CANAnalyzerWindow._notify_listen_only_blocked(window, ["CAN1"])
    CANAnalyzerWindow._notify_listen_only_blocked(window, ["CAN1", "CAN2"])

    assert len(window.notifications) == 2
    assert "CAN1" in window.notifications[0]
    assert "CAN2" in window.notifications[1]


def test_send_result_reports_blocked_without_generic_error():
    from src.main_window import CANAnalyzerWindow

    window = WindowStub()
    window.transmit_handler.last_send_error = "listen-only"
    window.transmit_handler.last_blocked_buses = ["CAN1"]

    assert CANAnalyzerWindow._handle_send_result(window, False) == "blocked"
    assert len(window.notifications) == 1


def test_send_result_reports_partial_success():
    from src.main_window import CANAnalyzerWindow

    window = WindowStub()
    window.transmit_handler.last_blocked_buses = ["CAN1"]

    assert CANAnalyzerWindow._handle_send_result(window, True) == "partial"


def test_send_result_plain_failure_has_no_notification():
    from src.main_window import CANAnalyzerWindow

    window = WindowStub()

    assert CANAnalyzerWindow._handle_send_result(window, False) is None
    assert window.notifications == []
