"""
Shared fixtures for the CAN Analyzer test suite.

The suite is fully headless and hardware-free:
- Qt runs with the ``offscreen`` platform plugin,
- python-can is only used through its ``virtual`` bus or injected fakes,
- shell commands (``ip link``, ``pkexec``) are always injected, never executed.
"""

import os
import sys

# Must be set before PyQt6 is imported anywhere.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pytest


@pytest.fixture(scope="session")
def qapp():
    """Single QApplication for the whole session (offscreen)."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(scope="session", autouse=True)
def _quiet_logger(tmp_path_factory):
    """Point the app logger at a temporary directory instead of ./logs."""
    from src.logger import init_logger

    log_dir = tmp_path_factory.mktemp("app-logs")
    init_logger(log_dir=str(log_dir))
    yield


@pytest.fixture
def colors():
    """Minimal color palette used by the table managers."""
    from PyQt6.QtGui import QColor

    return {
        "normal_bg": QColor("#101010"),
        "normal_text": QColor("#f0f0f0"),
        "highlight": QColor("#303030"),
    }


@pytest.fixture
def make_msg():
    """Build CANMessage objects with sensible defaults."""
    from src.models import CANMessage

    def _make(
        can_id=0x100,
        data=b"\x01\x02\x03\x04",
        source="CAN1",
        timestamp=None,
        dlc=None,
        **kwargs,
    ):
        if timestamp is None:
            timestamp = 1_700_000_000.0
        if dlc is None:
            dlc = len(data)
        return CANMessage(
            timestamp=timestamp,
            can_id=can_id,
            dlc=dlc,
            data=data,
            source=source,
            **kwargs,
        )

    return _make


class _RecordingStub:
    def __init__(self):
        self.messages = []

    def add_message(self, msg):
        self.messages.append(msg)

    def get_message_count(self):
        return len(self.messages)


class FakeParent:
    """Stand-in for CANAnalyzerWindow in handler-level tests."""

    def __init__(self):
        from collections import defaultdict
        import queue

        self.message_queue = queue.Queue()
        self.received_messages = []
        self.message_counters = defaultdict(int)
        self.message_last_timestamp = {}
        self.paused = False
        self.connected = True
        self.recording = False
        self.recording_mgr = _RecordingStub()
        self.tracer_mode = False
        self.split_screen_mode = False
        self.receive_table_left = None
        self.receive_table_right = None
        self.split_screen_left_channel = None
        self.split_screen_right_channel = None
        self.triggers_enabled = False
        self.logger = None
        self._ftcan_dialog = None
        self._bap_dialog = None
        self._obd2_dialog = None
        # Counters used by tests to assert throttling.
        self.message_count_updates = 0
        self.status_updates = 0
        self.displayed = []

    def update_message_count(self):
        self.message_count_updates += 1

    def update_consolidated_status(self):
        self.status_updates += 1

    def add_message_tracer_mode(self, msg, highlight=True):
        self.displayed.append(("tracer", msg))

    def add_message_monitor_mode(self, msg, highlight=True, target_table=None):
        self.displayed.append(("monitor", msg))

    def check_and_fire_triggers(self, msg):
        pass


@pytest.fixture
def fake_parent():
    return FakeParent()


@pytest.fixture
def make_table(qapp):
    """Factory: a QTableWidget wired to a ReceiveTableManager."""
    from PyQt6.QtWidgets import QTableWidget

    from src.handlers.message_handler import MessageHandler
    from src.ui.receive_table_manager import ReceiveTableManager

    def _make(tracer=False, parent=None):
        parent = parent or FakeParent()
        handler = MessageHandler(parent)
        manager = ReceiveTableManager(parent, handler)
        table = QTableWidget()
        manager.setup_table(table, tracer_mode=tracer)
        parent.receive_table = table
        parent.receive_table_mgr = manager
        parent.tracer_mode = tracer
        return table, manager, handler, parent

    return _make
