"""Save/load roundtrip tests for log files (JSON, CSV, trace)."""

import pytest

from src.handlers.file_handler import FileHandler


@pytest.fixture
def handler():
    return FileHandler(parent_window=None)


@pytest.fixture
def messages(make_msg):
    return [
        make_msg(can_id=0x100, data=b"\x01\x02", source="CAN1"),
        make_msg(
            can_id=0x18DAF110,
            data=b"\xaa\xbb\xcc",
            source="CAN2",
            is_extended=True,
            timestamp=1_700_000_001.0,
        ),
    ]


def test_json_roundtrip(handler, messages, tmp_path):
    path = tmp_path / "log.json"
    assert handler.save_log_json(str(path), messages) is True

    loaded = handler.load_log_json(str(path))

    assert loaded is not None
    assert [m.can_id for m in loaded] == [m.can_id for m in messages]
    assert [m.data for m in loaded] == [m.data for m in messages]
    assert loaded[1].is_extended is True


def test_csv_roundtrip(handler, messages, tmp_path):
    path = tmp_path / "log.csv"
    assert handler.save_log_csv(str(path), messages) is True

    loaded = handler.load_log_csv(str(path))

    assert loaded is not None
    assert [m.can_id for m in loaded] == [0x100, 0x18DAF110]
    assert loaded[1].is_extended is True
    assert loaded[0].source == "CAN1"


def test_trace_export(handler, messages, tmp_path):
    path = tmp_path / "log.asc"
    assert handler.save_log_trace(str(path), messages) is True

    text = path.read_text()
    assert "18DAF110x" in text  # extended id marker
    assert "Rx   d 2 01 02" in text


def test_load_json_rejects_broken_file(handler, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json")
    assert handler.load_log_json(str(path)) is None
