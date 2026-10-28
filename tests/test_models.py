"""Tests for the core message/filter models."""

import pytest

from src.models import CANFilter, CANMessage


def test_can_message_dict_roundtrip(make_msg):
    msg = make_msg(can_id=0x18DAF110, data=b"\xde\xad\xbe\xef", is_extended=True)
    restored = CANMessage.from_dict(msg.to_dict())

    assert restored.can_id == msg.can_id
    assert restored.data == msg.data
    assert restored.dlc == msg.dlc
    assert restored.is_extended is True
    assert restored.source == msg.source


def test_can_message_from_dict_tolerates_legacy_fields():
    """Files saved by older versions must keep loading."""
    restored = CANMessage.from_dict(
        {
            "timestamp": 1.0,
            "can_id": 0x123,
            "dlc": 2,
            "data": "0102",
        }
    )

    assert restored.can_id == 0x123
    assert restored.source  # default populated
    assert restored.comment == ""


def test_ascii_renders_printable_bytes_and_dots(make_msg):
    msg = make_msg(data=b"A\x00B\x7fC")
    assert msg.to_ascii() == "A.B.C"


def test_hex_string_and_bits(make_msg):
    msg = make_msg(data=b"\x01\xff")
    assert msg.to_hex_string() == "01 FF"
    assert msg.get_bits_string() == "00000001 11111111"


def test_get_bit_out_of_range_is_zero(make_msg):
    msg = make_msg(data=b"\x01")
    assert msg.get_bit(0, 0) == 1
    assert msg.get_bit(5, 0) == 0


@pytest.mark.parametrize(
    "enabled,filter_id,mask,can_id,expected",
    [
        (False, 0x100, 0x7FF, 0x200, True),   # disabled filter matches everything
        (True, 0x100, 0x7FF, 0x100, True),
        (True, 0x100, 0x7FF, 0x101, False),
        (True, 0x100, 0x700, 0x1FF, True),    # mask ignores low bits
    ],
)
def test_filter_matches(enabled, filter_id, mask, can_id, expected):
    f = CANFilter(filter_id=filter_id, mask=mask, enabled=enabled)
    assert f.matches(can_id) is expected
