"""
Scaling guards for the receive table.

These are ratio-based on purpose: absolute timings are meaningless on CI
machines, but the *shape* of the curve is not. A per-frame cost that grows with
the number of rows is exactly what made ``cangen`` freeze the UI.
"""

import time

import pytest

pytestmark = pytest.mark.slow

UPDATES = 300


def _rows(n, make_msg):
    return [make_msg(can_id=0x100 + i, timestamp=1_700_000_000.0 + i) for i in range(n)]


def _cost_per_update(make_table, make_msg, colors, n_rows, can_id=0x100):
    table, manager, _, _ = make_table()
    for msg in _rows(n_rows, make_msg):
        manager.add_message_monitor(table, msg, colors)

    warmup = make_msg(can_id=can_id, timestamp=1_800_000_000.0)
    for _ in range(20):
        manager.add_message_monitor(table, warmup, colors)

    start = time.perf_counter()
    for i in range(UPDATES):
        manager.add_message_monitor(
            table,
            make_msg(can_id=can_id, timestamp=1_800_000_000.0 + i * 0.01),
            colors,
        )
    return (time.perf_counter() - start) / UPDATES


def test_existing_id_update_cost_is_flat(make_table, make_msg, colors):
    """Updating one row must not depend on how many rows exist."""
    small = _cost_per_update(make_table, make_msg, colors, n_rows=300)
    large = _cost_per_update(make_table, make_msg, colors, n_rows=3000)

    # The old linear scan made this ~10x slower at 10x the rows.
    assert large < small * 4, f"per-update cost grew: {small*1e6:.1f}us -> {large*1e6:.1f}us"


def test_new_id_does_not_duplicate_items_across_rows(make_table, make_msg, colors):
    """Inserting a new ID must not (re)create QTableWidgetItems for other rows."""
    table, manager, _, _ = make_table()
    for msg in _rows(1000, make_msg):
        manager.add_message_monitor(table, msg, colors)

    manager.add_message_monitor(table, make_msg(can_id=0x010, source="CANZ"), colors)

    # Column 0 is painted from the row index, never stored.
    assert all(
        table.item(row, 0) is None or table.item(row, 0).text() == ""
        for row in range(table.rowCount())
    )
    # The new ID landed in sorted position (0x010 goes to the top).
    assert table.item(0, 3).text() == "0x010"
