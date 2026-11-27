"""gs_usb / candleLight channel discovery (no hardware)."""

from src import candle_backend as cb


class FakeDevice:
    def __init__(self, serial="ABC123", channels=2, product="CANable 2.5",
                 manufacturer="ElmueSoft", sw=0x260304, hw=0x0200):
        self.serial_number = serial
        self.channel_count = channels
        self.product = product
        self.manufacturer = manufacturer
        self.software_version = sw
        self.hardware_version = hw


def test_is_candle_channel():
    assert cb.is_candle_channel("2088339B413250013:0")
    assert cb.is_candle_channel("ABC:12")
    assert not cb.is_candle_channel("can0")
    assert not cb.is_candle_channel("/dev/cu.usbmodem1")
    assert not cb.is_candle_channel("COM4")
    assert not cb.is_candle_channel("ABC:")


def test_list_channels_expands_all_channels_of_a_device():
    channels = cb.list_channels(lambda: [FakeDevice(channels=2)])

    assert [ch.channel for ch in channels] == ["ABC123:0", "ABC123:1"]
    assert all(ch.serial == "ABC123" for ch in channels)
    assert channels[0].label == "CANable 2.5 ch0"
    assert "2 channels" in channels[0].description
    assert "FW 38.3.4" in channels[0].description


def test_list_channels_multiple_devices():
    devices = [FakeDevice(serial="A", channels=1), FakeDevice(serial="B", channels=2)]
    channels = cb.list_channels(lambda: devices)

    assert [ch.channel for ch in channels] == ["A:0", "B:0", "B:1"]


def test_list_channels_survives_missing_libusb_or_broken_device():
    def broken_lister():
        raise RuntimeError("libusb not found")

    assert cb.list_channels(broken_lister) == []

    class Broken:
        @property
        def serial_number(self):
            raise RuntimeError("descriptor error")

    assert cb.list_channels(lambda: [Broken(), FakeDevice(serial="OK", channels=1)]) == [
        cb.CandleChannel(channel="OK:0", serial="OK", index=0,
                         product="CANable 2.5", manufacturer="ElmueSoft",
                         channel_count=1, software_version=0x260304, hardware_version=0x0200)
    ]


def test_find_channel():
    lister = lambda: [FakeDevice(serial="ABC", channels=2)]  # noqa: E731

    assert cb.find_channel("ABC:1", lister).index == 1
    assert cb.find_channel("ABC:9", lister) is None


def test_format_version():
    assert cb.format_version(0x260304) == "38.3.4"
    assert cb.format_version(0) == ""
