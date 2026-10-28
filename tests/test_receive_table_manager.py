"""Receive table: monitor upsert index, tracer batching and ring buffer."""

import pytest
from PyQt6.QtCore import Qt

from src.ui.receive_table_manager import _RowNumberDelegate


def _pids(table):
    return [table.item(r, 3).text() for r in range(table.rowCount())]


def test_monitor_groups_by_id_and_source(make_table, make_msg, colors):
    table, manager, _, _ = make_table()

    manager.add_message_monitor(table, make_msg(can_id=0x100, data=b"\x01"), colors)
    manager.add_message_monitor(table, make_msg(can_id=0x100, data=b"\x02"), colors)

    assert table.rowCount() == 1
    assert table.item(0, 3).text() == "0x100"
    assert table.item(0, 1).text() == "2"      # count
    assert table.item(0, 5).text() == "02"     # latest data

    manager.add_message_monitor(table, make_msg(can_id=0x100, source="CAN2"), colors)
    assert table.rowCount() == 2


def test_monitor_rows_stay_sorted(make_table, make_msg, colors):
    table, manager, _, _ = make_table()

    for can_id in (0x300, 0x100, 0x200):
        manager.add_message_monitor(table, make_msg(can_id=can_id), colors)

    assert _pids(table) == ["0x100", "0x200", "0x300"]


def test_monitor_same_id_different_channel_sorted_by_channel(make_table, make_msg, colors):
    table, manager, _, _ = make_table()

    manager.add_message_monitor(table, make_msg(can_id=0x100, source="CAN2"), colors)
    manager.add_message_monitor(table, make_msg(can_id=0x100, source="CAN1"), colors)

    assert [table.item(r, 2).text() for r in range(table.rowCount())] == ["CAN1", "CAN2"]


def test_index_recovers_after_table_cleared_externally(make_table, make_msg, colors):
    table, manager, _, _ = make_table()
    manager.add_message_monitor(table, make_msg(can_id=0x100), colors)
    manager.add_message_monitor(table, make_msg(can_id=0x200), colors)

    # Some legacy paths clear the widget without telling the manager.
    table.setRowCount(0)

    manager.add_message_monitor(table, make_msg(can_id=0x200), colors)
    manager.add_message_monitor(table, make_msg(can_id=0x150), colors)

    assert table.rowCount() == 2
    assert _pids(table) == ["0x150", "0x200"]


def test_clear_table_drops_index(make_table, make_msg, colors):
    table, manager, _, _ = make_table()
    manager.add_message_monitor(table, make_msg(can_id=0x100), colors)

    manager.clear_table(table)
    manager.add_message_monitor(table, make_msg(can_id=0x100), colors)

    assert table.rowCount() == 1


def test_sequential_id_is_painted_not_stored(make_table, make_msg, colors):
    table, manager, _, _ = make_table()
    manager.add_message_monitor(table, make_msg(can_id=0x100), colors)
    manager.add_message_monitor(table, make_msg(can_id=0x200), colors)

    assert isinstance(table.itemDelegateForColumn(0), _RowNumberDelegate)
    # No text stored, so inserting rows never requires renumbering.
    assert table.item(1, 0) is None or table.item(1, 0).text() == ""


def test_tracer_single_message_appends(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)

    manager.add_message_tracer(table, make_msg(can_id=0x123, data=b"\xAA\xBB"))

    assert table.rowCount() == 1
    assert table.item(0, 3).text() == "0x123"
    assert table.item(0, 5).text() == "AA BB"


def test_tracer_batch_inserts_once(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)

    insert_events = []
    table.model().rowsInserted.connect(
        lambda parent, first, last: insert_events.append(last - first + 1)
    )

    manager.begin_batch()
    for i in range(10):
        manager.add_message_tracer(table, make_msg(can_id=0x100 + i))
    manager.end_batch()

    assert table.rowCount() == 10
    assert insert_events == [10]  # one rowsInserted, not ten


def test_tracer_ring_buffer_keeps_newest(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)
    manager.max_tracer_rows = 5

    manager.begin_batch()
    for i in range(8):
        manager.add_message_tracer(table, make_msg(can_id=0x100, data=bytes([i])))
    manager.end_batch()

    assert table.rowCount() == 5
    # Rows 0..7 arrived; the oldest three (0,1,2) were dropped.
    assert [table.item(r, 5).text() for r in range(5)] == ["03", "04", "05", "06", "07"]


def test_tracer_zero_means_unlimited(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)
    manager.max_tracer_rows = 0

    for i in range(20):
        manager.add_message_tracer(table, make_msg(can_id=0x100 + i))

    assert table.rowCount() == 20


def test_tracer_records_msg_index_for_playback(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)

    manager.add_message_tracer(table, make_msg(), msg_index=7)

    assert table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 7


def test_repopulate_respects_cap(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)
    manager.max_tracer_rows = 10

    manager.repopulate_tracer(table, [make_msg(can_id=0x100 + i) for i in range(25)])

    assert table.rowCount() == 10


@pytest.mark.parametrize("tracer", [False, True])
def test_setup_table_resets_index(make_table, make_msg, colors, tracer):
    table, manager, _, _ = make_table(tracer=tracer)
    if tracer:
        manager.add_message_tracer(table, make_msg())
    else:
        manager.add_message_monitor(table, make_msg(), colors)

    manager.setup_table(table, tracer_mode=tracer)

    if not tracer:
        # Index is rebuilt from the widget, so it must match the rows on screen.
        state = manager._table_state(table)
        assert state["index"] == {(0x100, "CAN1"): 0}


# ---------------------------------------------------------------------------
# ID column: one number only (Qt vertical header hidden) and absolute counting
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tracer", [False, True])
def test_vertical_header_is_hidden(make_table, tracer):
    table, _, _, _ = make_table(tracer=tracer)

    # Qt's row numbers would duplicate the ID column on the left.
    assert table.verticalHeader().isHidden() is True


def test_id_column_counter_is_absolute_after_ring_buffer(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)
    manager.max_tracer_rows = 5

    manager.begin_batch()
    for i in range(8):
        manager.add_message_tracer(table, make_msg(can_id=0x100, data=bytes([i])))
    manager.end_batch()

    assert table.rowCount() == 5
    assert manager.row_label_offset(table) == 3
    assert manager.frame_count(table) == 8

    # What the delegate paints for the first visible row is frame 4, not 1.
    delegate = table.itemDelegateForColumn(0)
    assert delegate._label(0) == "4"
    assert delegate._label(4) == "8"


def test_clear_table_resets_the_counter(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)
    manager.max_tracer_rows = 2
    for i in range(5):
        manager.add_message_tracer(table, make_msg())

    manager.clear_table(table)

    assert manager.row_label_offset(table) == 0
    assert manager.frame_count(table) == 0


def test_reload_resets_the_counter(make_table, make_msg):
    table, manager, _, _ = make_table(tracer=True)
    manager.max_tracer_rows = 2
    for i in range(5):
        manager.add_message_tracer(table, make_msg())

    manager.repopulate_tracer(table, [make_msg(), make_msg()])

    assert manager.row_label_offset(table) == 0
    assert manager.frame_count(table) == 2


@pytest.mark.parametrize("tracer,columns", [(True, 8), (False, 9)])
def test_split_screen_table_uses_the_same_columns(make_table, tracer, columns):
    """Split-screen tables must not drift from the main table config."""
    from PyQt6.QtWidgets import QTableWidget

    from src.main_window import CANAnalyzerWindow

    _, _, _, parent = make_table(tracer=tracer)
    parent.tracer_mode = tracer
    table = QTableWidget()

    CANAnalyzerWindow.setup_receive_table_for_widget(parent, table)

    assert table.columnCount() == columns
    assert table.horizontalHeaderItem(0).text() == "ID"
    assert table.verticalHeader().isHidden() is True
    assert isinstance(table.itemDelegateForColumn(0), _RowNumberDelegate)
