"""Save/load roundtrip tests for log files (JSON, CSV, trace)."""

import json

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


def test_json_writes_one_message_per_line(handler, messages, tmp_path):
    path = tmp_path / "lines.json"
    assert handler.save_log_json(str(path), messages) is True

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines[0] == "{"
    assert '"messages": [' in text

    message_lines = [line for line in lines if '"can_id"' in line]
    assert len(message_lines) == len(messages)
    assert message_lines[0].strip().startswith("{")
    assert message_lines[0].strip().endswith("},")
    assert message_lines[-1].strip().endswith("}")

    loaded = handler.load_log_json(str(path))
    assert [m.can_id for m in loaded] == [m.can_id for m in messages]


def test_json_one_line_preserves_fd_flags(handler, make_msg, tmp_path):
    path = tmp_path / "fd.json"
    msg = make_msg(can_id=0x200, data=bytes(range(64)), dlc=64,
                   is_fd=True, bitrate_switch=True)
    assert handler.save_log_json(str(path), [msg]) is True

    fd_lines = [line for line in path.read_text().splitlines() if '"can_id"' in line]
    assert len(fd_lines) == 1
    assert '"is_fd": true' in fd_lines[0]
    assert '"bitrate_switch": true' in fd_lines[0]

    loaded = handler.load_log_json(str(path))
    assert loaded[0].is_fd is True
    assert loaded[0].bitrate_switch is True


def test_load_legacy_json_without_fd_fields(handler, tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({
        "version": "1.0",
        "message_count": 1,
        "messages": [
            {"timestamp": 1.0, "can_id": 0x100, "dlc": 2, "data": "0102",
             "source": "CAN1"}
        ],
    }))

    loaded = handler.load_log_json(str(path))

    assert loaded is not None and len(loaded) == 1
    assert loaded[0].is_fd is False
    assert loaded[0].bitrate_switch is False


def test_load_legacy_csv_without_fd_columns(handler, tmp_path):
    path = tmp_path / "legacy.csv"
    path.write_text(
        "Timestamp,CAN ID,DLC,Data,Extended,RTR,Source\n"
        "1.0,0x100,2,01 02,False,False,CAN1\n"
    )

    loaded = handler.load_log_csv(str(path))

    assert loaded is not None and len(loaded) == 1
    assert loaded[0].is_fd is False
    assert loaded[0].bitrate_switch is False


def test_csv_roundtrip(handler, messages, tmp_path):
    path = tmp_path / "log.csv"
    assert handler.save_log_csv(str(path), messages) is True

    loaded = handler.load_log_csv(str(path))

    assert loaded is not None
    assert [m.can_id for m in loaded] == [0x100, 0x18DAF110]
    assert loaded[1].is_extended is True
    assert loaded[0].source == "CAN1"


def test_csv_preserves_fd_and_brs(handler, make_msg, tmp_path):
    path = tmp_path / "fd.csv"
    msg = make_msg(can_id=0x200, data=bytes(range(64)), dlc=64,
                   is_fd=True, bitrate_switch=True)

    assert handler.save_log_csv(str(path), [msg]) is True
    loaded = handler.load_log_csv(str(path))

    assert loaded is not None and len(loaded) == 1
    assert loaded[0].is_fd is True
    assert loaded[0].bitrate_switch is True
    assert loaded[0].dlc == 64


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


def test_loaded_messages_can_fill_the_playback_buffer(handler, messages, tmp_path):
    from src.handlers.recording_handler import RecordingHandler

    path = tmp_path / "log.json"
    assert handler.save_log_json(str(path), messages) is True
    loaded = handler.load_log_json(str(path))

    recording = RecordingHandler(logger=None)
    recording.set_recorded_messages(loaded)

    assert recording.get_message_count() == len(messages)
    assert recording.get_recorded_messages()[0].can_id == 0x100
