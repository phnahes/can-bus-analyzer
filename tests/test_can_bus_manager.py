"""CANBusInstance/CANBusManager: backend selection, errors, send/receive."""

import time

import pytest

from src import can_bus_manager as cbm
from src.can_interface_setup import CanLink, InterfaceDownError
from src.models import CANMessage


class FakeBus:
    """Minimal stand-in for a python-can bus."""

    def __init__(self, messages=(), on_empty=None):
        self._messages = list(messages)
        self.sent = []
        self.shutdown_called = False
        self.on_empty = on_empty

    def recv(self, timeout=None):
        if self._messages:
            return self._messages.pop(0)
        if self.on_empty is not None:
            self.on_empty()
        time.sleep(0.005)
        return None

    def send(self, msg):
        self.sent.append(msg)

    def shutdown(self):
        self.shutdown_called = True


def make_instance(**overrides):
    config = cbm.CANBusConfig(
        name="CAN1",
        channel=overrides.pop("channel", "can0"),
        baudrate=overrides.pop("baudrate", 500000),
        **overrides,
    )
    return cbm.CANBusInstance(config)


# ---------------------------------------------------------------------------
# Interface resolution / backend kwargs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "channel,configured,expected",
    [
        ("can0", "socketcan", "socketcan"),
        ("can7", "socketcan", "socketcan"),
        ("vcan3", "socketcan", "socketcan"),
        ("/dev/ttyUSB0", "socketcan", "slcan"),
        ("/dev/cu.usbserial-1", "socketcan", "slcan"),
        ("COM4", "socketcan", "slcan"),
        ("0", "gs_usb", "gs_usb"),
        ("can0", "slcan", "socketcan"),  # channel wins over a stale interface
    ],
)
def test_resolve_interface(channel, configured, expected):
    instance = make_instance(channel=channel, interface=configured)
    assert instance._resolve_interface() == expected


def test_socketcan_kwargs_do_not_pass_bitrate():
    instance = make_instance()
    kwargs = instance._bus_kwargs("socketcan")

    assert kwargs["interface"] == "socketcan"
    assert "bitrate" not in kwargs  # silently ignored by python-can
    assert kwargs["receive_own_messages"] is True


def test_socketcan_fd_kwarg():
    instance = make_instance(fd=True)
    assert instance._bus_kwargs("socketcan")["fd"] is True


def test_slcan_kwargs_include_bitrate_and_listen_only():
    instance = make_instance(channel="/dev/ttyUSB0", listen_only=True, tty_baudrate=115200)
    kwargs = instance._bus_kwargs("slcan")

    assert kwargs["bitrate"] == 500000
    assert kwargs["listen_only"] is True
    assert kwargs["tty_baudrate"] == 115200


def test_slcan_without_tty_baudrate_keeps_backend_default():
    instance = make_instance(channel="/dev/ttyUSB0")
    assert "tty_baudrate" not in instance._bus_kwargs("slcan")


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


@pytest.fixture
def no_ip(monkeypatch):
    """Pretend we are not on Linux so no `ip` command is executed."""
    monkeypatch.setattr(cbm, "sys_is_linux", lambda: False)


def test_connect_opens_bus_with_backend_kwargs(monkeypatch, no_ip):
    created = {}

    def fake_bus_factory(**kwargs):
        created.update(kwargs)
        return FakeBus()

    monkeypatch.setattr(cbm.can.interface, "Bus", fake_bus_factory)

    instance = make_instance()
    assert instance.connect() is True

    try:
        assert created["interface"] == "socketcan"
        assert "bitrate" not in created
        assert instance.connected is True
    finally:
        instance.disconnect()


def test_connect_failure_is_kept_for_the_caller(monkeypatch, no_ip):
    def failing_prepare(self):
        raise InterfaceDownError("can0", command="sudo ip link ...", reason="down")

    monkeypatch.setattr(cbm.CANBusInstance, "_prepare_socketcan", failing_prepare)

    instance = make_instance()
    assert instance.connect() is False
    assert isinstance(instance.last_error, InterfaceDownError)


def test_connect_all_records_errors(monkeypatch, no_ip):
    def failing_prepare(self):
        raise InterfaceDownError(self.config.channel, reason="down")

    monkeypatch.setattr(cbm.CANBusInstance, "_prepare_socketcan", failing_prepare)

    manager = cbm.CANBusManager()
    manager.add_bus(cbm.CANBusConfig(name="CAN1", channel="can0", baudrate=500000))

    results = manager.connect_all(simulation=False)

    assert results == {"CAN1": False}
    assert isinstance(manager.connect_errors["CAN1"], InterfaceDownError)


# ---------------------------------------------------------------------------
# SocketCAN link preparation (the "Connect does not bring the interface up" fix)
# ---------------------------------------------------------------------------


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(cbm, "sys_is_linux", lambda: True)
    monkeypatch.setattr(cbm, "ip_available", lambda: True)


def _patch_link(monkeypatch, link):
    monkeypatch.setattr(cbm, "get_link", lambda name, use_cache=True: link)


def test_down_link_without_bring_up_raises_with_command(monkeypatch, linux):
    _patch_link(monkeypatch, CanLink(name="can2", up=False, bitrate=500000))
    instance = make_instance(channel="can2")

    with pytest.raises(InterfaceDownError) as excinfo:
        instance._prepare_socketcan()

    assert "up type can bitrate 500000" in excinfo.value.command
    assert excinfo.value.channel == "can2"


def test_missing_interface_reports_not_found(monkeypatch, linux):
    _patch_link(monkeypatch, None)
    instance = make_instance(channel="can9")

    with pytest.raises(InterfaceDownError) as excinfo:
        instance._prepare_socketcan()

    assert excinfo.value.reason == "not found"


def test_down_link_with_bring_up_configures_it(monkeypatch, linux):
    calls = {}
    links = [
        CanLink(name="can2", up=False, bitrate=500000),
        CanLink(name="can2", up=True, bitrate=500000),
    ]

    def fake_get_link(name, use_cache=True):
        return links.pop(0) if links else CanLink(name="can2", up=True, bitrate=500000)

    def fake_bring_up(name, bitrate, dbitrate=None, fd=False, listen_only=False):
        calls.update(name=name, bitrate=bitrate)
        return True, "", ["ip", "link"]

    monkeypatch.setattr(cbm, "get_link", fake_get_link)
    monkeypatch.setattr(cbm, "bring_up", fake_bring_up)

    instance = make_instance(channel="can2", bring_up=True)
    instance._prepare_socketcan()

    assert calls == {"name": "can2", "bitrate": 500000}
    assert instance.actual_bitrate == 500000


def test_bring_up_failure_raises_with_output(monkeypatch, linux):
    _patch_link(monkeypatch, CanLink(name="can2", up=False, bitrate=500000))
    monkeypatch.setattr(
        cbm, "bring_up", lambda *a, **kw: (False, "permission denied", ["ip", "link"])
    )

    instance = make_instance(channel="can2", bring_up=True)

    with pytest.raises(InterfaceDownError) as excinfo:
        instance._prepare_socketcan()

    assert "permission denied" in str(excinfo.value)


def test_up_link_with_different_bitrate_only_warns(monkeypatch, linux, capsys):
    _patch_link(monkeypatch, CanLink(name="can2", up=True, bitrate=1000000))
    instance = make_instance(channel="can2", baudrate=500000)

    instance._prepare_socketcan()

    assert instance.actual_bitrate == 1000000
    assert "1000000 bps" in capsys.readouterr().out


def test_fd_requested_but_link_not_fd_raises(monkeypatch, linux):
    _patch_link(monkeypatch, CanLink(name="can2", up=True, bitrate=500000, fd=False))
    instance = make_instance(channel="can2", fd=True, dbitrate=5000000)

    with pytest.raises(InterfaceDownError) as excinfo:
        instance._prepare_socketcan()

    assert "CAN FD" in str(excinfo.value)


def test_listen_only_mismatch_warns_but_connects(monkeypatch, linux, capsys):
    _patch_link(monkeypatch, CanLink(name="can2", up=True, bitrate=500000, listen_only=False))
    instance = make_instance(channel="can2", listen_only=True)

    instance._prepare_socketcan()

    assert "listen-only" in capsys.readouterr().out


def test_without_ip_tool_the_check_is_skipped(monkeypatch, linux, capsys):
    monkeypatch.setattr(cbm, "ip_available", lambda: False)
    instance = make_instance(channel="can2")

    instance._prepare_socketcan()  # must not raise

    assert "'ip' not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# send / receive
# ---------------------------------------------------------------------------


def test_send_converts_app_message_to_python_can_message():
    instance = make_instance(listen_only=False)
    fake = FakeBus()
    instance.bus = fake
    instance.connected = True

    msg = CANMessage(
        timestamp=1.0, can_id=0x18DAF110, dlc=2, data=b"\x01\x02", is_extended=True
    )
    assert instance.send(msg) is True

    sent = fake.sent[0]
    assert sent.arbitration_id == 0x18DAF110
    assert sent.is_extended_id is True
    assert bytes(sent.data) == b"\x01\x02"


def test_send_accepts_python_can_message():
    import can

    instance = make_instance(listen_only=False)
    fake = FakeBus()
    instance.bus = fake
    instance.connected = True

    native = can.Message(arbitration_id=0x123, data=b"\xff", is_extended_id=False)
    assert instance.send(native) is True
    assert fake.sent[0] is native


def test_listen_only_blocks_send_by_config():
    instance = make_instance(listen_only=True)
    fake = FakeBus()
    instance.bus = fake
    instance.connected = True

    assert instance.send(CANMessage(timestamp=1.0, can_id=0x100, dlc=1, data=b"\x01")) is False
    assert instance.last_send_error == "listen-only"
    assert fake.sent == []  # nothing written to the adapter


def test_listen_only_blocks_send_by_link_state():
    """SocketCAN: the kernel link can be listen-only even if config is not."""
    instance = make_instance(listen_only=False)
    instance.link_listen_only = True
    fake = FakeBus()
    instance.bus = fake
    instance.connected = True

    assert instance.listen_only_active is True
    assert instance.send(CANMessage(timestamp=1.0, can_id=0x100, dlc=1, data=b"\x01")) is False
    assert fake.sent == []


def test_send_clears_previous_error():
    instance = make_instance(listen_only=False)
    instance.bus = FakeBus()
    instance.connected = True
    instance.last_send_error = "listen-only"

    assert instance.send(CANMessage(timestamp=1.0, can_id=0x100, dlc=1, data=b"\x01")) is True
    assert instance.last_send_error is None


def test_get_listen_only_buses_filters_by_mode():
    manager = cbm.CANBusManager()
    manager.add_bus(cbm.CANBusConfig(name="CAN1", channel="can0", baudrate=500000, listen_only=True))
    manager.add_bus(cbm.CANBusConfig(name="CAN2", channel="can1", baudrate=500000, listen_only=False))

    assert manager.get_listen_only_buses() == ["CAN1"]
    assert manager.get_listen_only_buses(["CAN2"]) == []


def test_receive_loop_forwards_with_source():
    received = []

    def on_message(bus_name, msg):
        received.append((bus_name, msg))

    instance = cbm.CANBusInstance(
        cbm.CANBusConfig(name="CAN2", channel="can1", baudrate=500000),
        message_callback=on_message,
    )

    import can as python_can

    native = python_can.Message(arbitration_id=0x321, data=b"\xde\xad", is_extended_id=True)
    instance.bus = FakeBus([native], on_empty=lambda: setattr(instance, "running", False))
    instance.running = True

    instance._receive_loop()

    bus_name, msg = received[0]
    assert bus_name == "CAN2"
    assert msg.can_id == 0x321
    assert msg.data == b"\xde\xad"
    assert msg.is_extended is True
    assert msg.source == "CAN2"
