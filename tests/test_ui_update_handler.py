"""UI tick bounds, batching and overload behaviour."""

import queue

import pytest

from src.handlers.ui_update_handler import UIUpdateHandler


def _fill(parent, count, make_msg):
    for i in range(count):
        parent.message_queue.put(make_msg(can_id=0x100 + (i % 50)))


def test_tick_processes_at_most_max_per_tick(fake_parent, make_msg):
    fake_parent.tracer_mode = True
    fake_parent.recording = True
    handler = UIUpdateHandler(fake_parent)
    fake_parent.message_queue = queue.Queue(maxsize=10000)
    _fill(fake_parent, 2500, make_msg)

    handler.update_ui()

    assert 0 < len(fake_parent.displayed) <= UIUpdateHandler.MAX_MESSAGES_PER_TICK
    assert not fake_parent.message_queue.empty()


def test_counters_updated_once_per_tick(fake_parent, make_msg):
    fake_parent.tracer_mode = True
    fake_parent.recording = True
    handler = UIUpdateHandler(fake_parent)
    _fill(fake_parent, 20, make_msg)

    handler.update_ui()

    assert fake_parent.message_count_updates == 1
    assert len(fake_parent.displayed) == 20


def test_empty_queue_does_not_touch_ui(fake_parent):
    handler = UIUpdateHandler(fake_parent)

    handler.update_ui()

    assert fake_parent.message_count_updates == 0


def test_zero_budget_leaves_queue_untouched(fake_parent, make_msg):
    """The tick must stop on the time budget even with messages pending."""
    fake_parent.tracer_mode = True
    fake_parent.recording = True
    handler = UIUpdateHandler(fake_parent)
    handler.TICK_BUDGET_S = 0
    _fill(fake_parent, 10, make_msg)

    handler.update_ui()

    assert fake_parent.message_queue.qsize() == 10
    assert fake_parent.displayed == []
    assert fake_parent.message_count_updates == 0


def test_paused_keeps_messages_queued(fake_parent, make_msg):
    fake_parent.paused = True
    fake_parent.tracer_mode = True
    fake_parent.recording = True
    handler = UIUpdateHandler(fake_parent)
    _fill(fake_parent, 5, make_msg)

    handler.update_ui()

    assert fake_parent.message_queue.qsize() == 5
    assert fake_parent.displayed == []

    fake_parent.paused = False
    handler.update_ui()
    assert fake_parent.message_queue.empty()
    assert len(fake_parent.displayed) == 5


def test_tracer_rows_inserted_once_per_tick(make_table, make_msg, qapp):
    table, manager, _, parent = make_table(tracer=True)
    parent.recording = True
    parent.message_queue = queue.Queue(maxsize=1000)
    # Mirror CANAnalyzerWindow.add_message_tracer_mode (the rest of the window is stubbed).
    parent.add_message_tracer_mode = lambda msg, highlight=True: manager.add_message_tracer(
        table, msg, highlight
    )
    handler = UIUpdateHandler(parent)

    insert_events = []
    table.model().rowsInserted.connect(
        lambda index, first, last: insert_events.append(last - first + 1)
    )

    for i in range(10):
        parent.message_queue.put(make_msg(can_id=0x100 + i))

    handler.update_ui()

    assert table.rowCount() == 10
    assert insert_events == [10]


def test_channel_filter_is_applied_before_display(fake_parent, make_msg):
    """Frames from a filtered channel are consumed but not displayed."""
    fake_parent.tracer_mode = True
    fake_parent.recording = True

    class Combo:
        def currentText(self):
            return "CAN2"

    fake_parent.tracer_channel_combo = Combo()
    handler = UIUpdateHandler(fake_parent)

    fake_parent.message_queue.put(make_msg(source="CAN1"))
    fake_parent.message_queue.put(make_msg(source="CAN2"))

    handler.update_ui()

    assert [msg.source for _, msg in fake_parent.displayed] == ["CAN2"]


# ---------------------------------------------------------------------------
# Overload handling in the real window (bounded queue + dropped counter)
# ---------------------------------------------------------------------------


class _WindowState:
    """Attributes _on_can_message_received touches, without building the Qt window."""


@pytest.fixture
def window_stub():
    from src.logger import get_logger

    window = _WindowState()
    window.logger = get_logger()
    window.message_queue = queue.Queue(maxsize=2)
    window._dropped_frames = 0
    window._obd2_dialog = None
    return window


def test_full_queue_counts_dropped_frames(window_stub, make_msg):
    from src.main_window import CANAnalyzerWindow

    for i in range(4):
        CANAnalyzerWindow._on_can_message_received(
            window_stub, "CAN1", make_msg(can_id=0x100 + i)
        )

    assert window_stub.message_queue.qsize() == 2
    assert window_stub._dropped_frames == 2


def test_queue_accepts_frames_below_capacity(window_stub, make_msg):
    from src.main_window import CANAnalyzerWindow

    CANAnalyzerWindow._on_can_message_received(window_stub, "CAN1", make_msg(can_id=0x100))
    CANAnalyzerWindow._on_can_message_received(window_stub, "CAN1", make_msg(can_id=0x101))

    assert window_stub.message_queue.qsize() == 2
    assert window_stub._dropped_frames == 0
