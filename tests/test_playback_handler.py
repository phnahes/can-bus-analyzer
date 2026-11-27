"""Playback must fail fast instead of blocking on a dead/ACK-less bus."""

import threading

from src.handlers.playback_handler import PlaybackHandler
from src.models import CANMessage


class _Logger:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def _messages(count):
    return [
        CANMessage(timestamp=float(i), can_id=0x100, dlc=1, data=b"\x01")
        for i in range(count)
    ]


def test_playback_aborts_after_consecutive_failures():
    sent = []
    errors = []
    completed = []
    abort_event = threading.Event()

    def send(msg):
        sent.append(msg)
        return False

    handler = PlaybackHandler(send_callback=send, logger=_Logger())
    handler.on_playback_error = lambda error: (errors.append(error), abort_event.set())
    handler.on_playback_complete = lambda: completed.append(True)

    handler.play_all(_messages(20), respect_timing=False)
    assert abort_event.wait(timeout=2.0) is True

    assert len(sent) == handler.MAX_CONSECUTIVE_FAILURES
    assert len(errors) == 1
    assert "Listen Only" in errors[0]
    assert completed == []
    assert handler.is_playing is False


def test_playback_completes_when_sends_succeed():
    sent = []
    completed = []
    done = threading.Event()

    def send(msg):
        sent.append(msg)
        return True

    handler = PlaybackHandler(send_callback=send, logger=_Logger())
    handler.on_playback_error = lambda error: (_ for _ in ()).throw(AssertionError(error))
    handler.on_playback_complete = lambda: (completed.append(True), done.set())

    handler.play_all(_messages(3), respect_timing=False)
    assert done.wait(timeout=2.0) is True

    assert len(sent) == 3
    assert completed == [True]
    assert handler.is_playing is False


def test_exception_in_send_counts_as_failure():
    sent = []
    event = threading.Event()

    def send(msg):
        sent.append(msg)
        raise RuntimeError("boom")

    handler = PlaybackHandler(send_callback=send, logger=_Logger())
    handler.on_playback_error = lambda error: event.set()

    handler.play_all(_messages(10), respect_timing=False)
    assert event.wait(timeout=2.0) is True
    assert len(sent) == handler.MAX_CONSECUTIVE_FAILURES
