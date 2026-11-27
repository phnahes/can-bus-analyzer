"""Shared CandleBus sessions: one USB device, many channel proxies."""

import queue
import time

import can
import pytest

from src import candle_session as cs


class FakeBus:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.queue = queue.Queue()
        self.sent = []
        self.shutdown_called = False

    def recv(self, timeout=None):
        try:
            return self.queue.get(timeout=timeout if timeout is not None else 0.05)
        except queue.Empty:
            return None

    def send(self, msg, timeout=None):
        self.sent.append(msg)

    def shutdown(self):
        self.shutdown_called = True


@pytest.fixture
def fake_buses(monkeypatch):
    created = []

    def factory(**kwargs):
        bus = FakeBus(**kwargs)
        created.append(bus)
        return bus

    monkeypatch.setattr(cs.can.interface, "Bus", factory)
    cs.reset_sessions()
    yield created
    cs.reset_sessions()


def test_parse_channel():
    assert cs.parse_channel("ABC123:1") == ("ABC123", 1)
    assert cs.parse_channel(0) == ("", 0)


def test_first_channel_opens_the_whole_device(fake_buses):
    proxy = cs.acquire_channel("ABC:0", {"bitrate": 500000})

    assert len(fake_buses) == 1
    assert fake_buses[0].kwargs["channel"] == [0]
    assert fake_buses[0].kwargs["serial_number"] == "ABC"

    msg = can.Message(arbitration_id=0x100, data=b"\x01")
    proxy.send(msg)
    assert fake_buses[0].sent[0].channel == 0

    proxy.shutdown()
    assert fake_buses[0].shutdown_called is True


def test_second_channel_reopens_the_device_with_both_channels(fake_buses):
    p0 = cs.acquire_channel("ABC:0", {"bitrate": 500000, "fd": True,
                                      "data_bitrate": 5_000_000})
    p1 = cs.acquire_channel("ABC:1", {"bitrate": 500000, "fd": True,
                                      "data_bitrate": 5_000_000,
                                      "listen_only": True})

    assert len(fake_buses) == 2
    assert fake_buses[-1].kwargs["channel"] == [0, 1]
    configs = fake_buses[-1].kwargs["channel_configs"]
    assert configs[0]["fd"] is True
    assert configs[1]["listen_only"] is True

    p1.send(can.Message(arbitration_id=0x101, data=b"\x02"))
    assert fake_buses[-1].sent[0].channel == 1

    p0.shutdown()
    p1.shutdown()


def test_incoming_frames_are_dispatched_by_channel(fake_buses):
    p0 = cs.acquire_channel("ABC:0", {"bitrate": 500000})
    p1 = cs.acquire_channel("ABC:1", {"bitrate": 500000})
    bus = fake_buses[-1]

    incoming = can.Message(arbitration_id=0x200, data=b"\xAA" * 8,
                           channel=1, is_rx=True)
    bus.queue.put(incoming)

    got = p1.recv(timeout=0.5)
    assert got is incoming
    assert p0.recv(timeout=0.05) is None

    p0.shutdown()
    p1.shutdown()


def test_tx_echoes_are_dropped(fake_buses):
    proxy = cs.acquire_channel("ABC:0", {"bitrate": 500000})
    fake_buses[-1].queue.put(
        can.Message(arbitration_id=0x300, data=b"\x01", channel=0, is_rx=False)
    )

    time.sleep(0.1)
    assert proxy.recv(timeout=0.05) is None

    proxy.shutdown()


def test_last_channel_closes_the_device(fake_buses):
    p0 = cs.acquire_channel("ABC:0", {"bitrate": 500000})
    p1 = cs.acquire_channel("ABC:1", {"bitrate": 500000})

    p0.shutdown()
    reopened = fake_buses[-1]
    assert reopened.kwargs["channel"] == [1]
    assert reopened.shutdown_called is False

    p1.shutdown()
    assert reopened.shutdown_called is True
