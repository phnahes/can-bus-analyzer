"""
Multi-channel gs_usb sessions.

python-can-candle opens the *whole* USB device, so two ``candle`` Bus objects
cannot own channel 0 and channel 1 of the same adapter at the same time.  The
app models one bus per channel, so this module multiplexes a single CandleBus
per adapter and hands each channel a small ``send``/``recv``/``shutdown`` proxy.

One reader thread per device dispatches incoming frames to the channel queue
they belong to.  TX echoes (``is_rx is False``) are dropped: the application
already logs transmissions, and they must not be re-displayed as received
frames or forwarded by the gateway.
"""

import queue
import threading
import time
from typing import Dict, Optional

import can

_SESSIONS: Dict[str, "_DeviceSession"] = {}
_REGISTRY_LOCK = threading.Lock()

# Keys accepted by python-can-candle's per-channel config.
_CHANNEL_CONFIG_KEYS = (
    "bitrate", "sample_point", "data_bitrate", "data_sample_point",
    "fd", "loop_back", "listen_only", "triple_sample", "one_shot",
    "bit_error_reporting", "termination",
)


def parse_channel(channel) -> tuple:
    """``"serial:1"`` -> ``("serial", 1)``; ``"0"`` -> ``("", 0)``."""
    text = str(channel)
    if ":" in text:
        serial, _, index = text.rpartition(":")
        return serial, int(index)
    return "", int(text)


class _ChannelProxy:
    """Per-channel view of a shared CandleBus."""

    def __init__(self, session: "_DeviceSession", index: int):
        self._session = session
        self._index = index
        self._queue: "queue.Queue" = queue.Queue()
        self.channel_info = f"{session.serial or 'candle'}:{index}"

    def recv(self, timeout: Optional[float] = None):
        try:
            return self._queue.get(timeout=timeout if timeout is not None else 0.1)
        except queue.Empty:
            return None

    def send(self, msg, timeout: Optional[float] = None) -> None:
        if getattr(msg, "channel", None) is None:
            msg.channel = self._index
        with self._session.lock:
            self._session.bus.send(msg, timeout)

    def shutdown(self) -> None:
        self._session.remove_channel(self._index)

    def clear(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return


class _DeviceSession:
    """One open CandleBus shared by all requested channels of an adapter."""

    def __init__(self, serial: str):
        self.serial = serial
        self.bus = None
        self.channels: Dict[int, _ChannelProxy] = {}
        self.configs: Dict[int, dict] = {}
        self.lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # -- lifecycle ---------------------------------------------------------

    def add_channel(self, index: int, kwargs: dict) -> _ChannelProxy:
        with self.lock:
            proxy = _ChannelProxy(self, index)
            self.channels[index] = proxy
            self.configs[index] = {
                key: kwargs[key] for key in _CHANNEL_CONFIG_KEYS if key in kwargs
            }
            try:
                self._restart()
            except Exception:
                self.channels.pop(index, None)
                self.configs.pop(index, None)
                if not self.channels:
                    self._close()
                    _SESSIONS.pop(self.serial, None)
                raise
            return proxy

    def remove_channel(self, index: int) -> None:
        with self.lock:
            if self.channels.pop(index, None) is None:
                return
            self.configs.pop(index, None)
            if self.channels:
                try:
                    self._restart()
                except Exception:
                    self._close()
            else:
                self._close()
                _SESSIONS.pop(self.serial, None)

    def _restart(self) -> None:
        self._close_bus()

        indices = sorted(self.channels)
        if not indices:
            return

        first = self.configs[indices[0]]
        kwargs = {
            "interface": "candle",
            "channel": indices,
            "bitrate": first.get("bitrate", 500_000),
            "fd": first.get("fd", False),
            "listen_only": first.get("listen_only", False),
            "ignore_config": True,
        }
        if first.get("fd"):
            kwargs["data_bitrate"] = first.get("data_bitrate", 5_000_000)
        if self.serial:
            kwargs["serial_number"] = self.serial

        if len(indices) > 1:
            kwargs["channel_configs"] = {
                index: dict(self.configs[index]) for index in indices
            }

        self.bus = can.interface.Bus(**kwargs)
        for proxy in self.channels.values():
            proxy.clear()

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._pump, daemon=True, name=f"CandleRx-{self.serial or 'dev'}"
        )
        self._thread.start()

    def _close_bus(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        if self.bus is not None:
            try:
                self.bus.shutdown()
            except Exception:
                pass
            self.bus = None

    def _close(self) -> None:
        self._close_bus()

    # -- receive pump ------------------------------------------------------

    def _pump(self) -> None:
        while not self._stop.is_set() and self.bus is not None:
            try:
                msg = self.bus.recv(timeout=0.05)
            except Exception:
                time.sleep(0.05)
                continue
            if msg is None:
                continue
            # Candle reports TX confirmations as is_rx=False; drop them.
            if msg.is_rx is False:
                continue
            proxy = self.channels.get(msg.channel)
            if proxy is not None:
                proxy._queue.put(msg)


def acquire_channel(channel, kwargs: dict) -> _ChannelProxy:
    """Open (or join) the shared session for ``serial:index``."""
    serial, index = parse_channel(channel)
    with _REGISTRY_LOCK:
        session = _SESSIONS.get(serial)
        if session is None:
            session = _DeviceSession(serial)
            _SESSIONS[serial] = session
        return session.add_channel(index, kwargs)


def reset_sessions() -> None:
    """Close every session (tests / shutdown)."""
    with _REGISTRY_LOCK:
        sessions = list(_SESSIONS.values())
        _SESSIONS.clear()
    for session in sessions:
        session._close()
