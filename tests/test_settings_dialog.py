"""Settings dialog: new performance/interface options round-trip to config."""

from src.dialogs.settings_dialog import SettingsDialog

CONFIG = {
    "language": "en",
    "theme": "dark",
    "saves_base_dir": "",
    "simulation_mode": False,
    "max_tracer_rows": 15000,
    "rx_queue_size": 40000,
    "can_buses": [
        {
            "name": "CAN1",
            "channel": "can0",
            "baudrate": 500000,
            "listen_only": True,
            "interface": "socketcan",
            "bring_up": True,
            "com_baudrate": "115200 bit/s",
        }
    ],
}


def test_performance_limits_are_preserved(qapp):
    dialog = SettingsDialog(parent=None, config=CONFIG, usb_monitor=None)
    config = dialog.get_config()

    assert config["max_tracer_rows"] == 15000
    assert config["rx_queue_size"] == 40000


def test_bring_up_flag_round_trips(qapp):
    dialog = SettingsDialog(parent=None, config=CONFIG, usb_monitor=None)
    config = dialog.get_config()

    assert config["can_buses"][0]["bring_up"] is True
    assert config["can_buses"][0]["interface"] == "socketcan"


def test_serial_baudrate_is_parsed_to_int(qapp):
    dialog = SettingsDialog(parent=None, config=CONFIG, usb_monitor=None)
    config = dialog.get_config()

    assert config["can_buses"][0]["tty_baudrate"] == 115200


def test_defaults_when_keys_absent(qapp):
    dialog = SettingsDialog(parent=None, config={"language": "en"}, usb_monitor=None)
    config = dialog.get_config()

    assert config["max_tracer_rows"] == 20000
    assert config["rx_queue_size"] == 50000
    assert config["can_buses"][0]["bring_up"] is False


def test_candle_channel_is_detected_and_fd_round_trips(qapp):
    config = {
        "language": "en",
        "can_buses": [
            {
                "name": "CAN1",
                "channel": "2088339B413250013:1",
                "baudrate": 500000,
                "interface": "socketcan",  # stale value, channel wins
                "listen_only": False,
                "fd": True,
                "dbitrate": 5_000_000,
            }
        ],
    }
    dialog = SettingsDialog(parent=None, config=config, usb_monitor=None)
    bus = dialog.get_config()["can_buses"][0]

    assert bus["interface"] == "candle"
    assert bus["fd"] is True
    assert bus["dbitrate"] == 5_000_000


def _dialog_with_channel(qapp, channel):
    config = {
        "language": "en",
        "can_buses": [
            {
                "name": "CAN1",
                "channel": channel,
                "baudrate": 500000,
                "listen_only": True,
                "com_baudrate": "115200 bit/s",
            }
        ],
    }
    return SettingsDialog(parent=None, config=config, usb_monitor=None)


def test_socketcan_disables_serial_fields(qapp):
    dialog = _dialog_with_channel(qapp, "can0")
    widget = dialog.can_bus_widgets[0]

    assert "SocketCAN" in widget.driver_info.text()
    assert widget.com_baudrate_combo.isEnabled() is False
    assert widget.rts_hs_check.isEnabled() is False
    assert widget.bring_up_check.isEnabled() is True
    assert widget.serial_info.isHidden() is True
    assert widget.socketcan_info.isHidden() is False


def test_gs_usb_disables_serial_and_link_setup_fields(qapp):
    dialog = _dialog_with_channel(qapp, "2088339B413250013:0")
    widget = dialog.can_bus_widgets[0]

    assert "gs_usb" in widget.driver_info.text()
    assert widget.com_baudrate_combo.isEnabled() is False
    assert widget.rts_hs_check.isEnabled() is False
    assert widget.bring_up_check.isEnabled() is False
    assert widget.fd_check.isEnabled() is True
    assert widget.serial_info.isHidden() is True
    assert widget.socketcan_info.isHidden() is True


def test_slcan_enables_serial_fields_and_disables_fd(qapp):
    dialog = _dialog_with_channel(qapp, "/dev/cu.usbmodem123")
    widget = dialog.can_bus_widgets[0]

    assert "SLCAN" in widget.driver_info.text()
    assert widget.com_baudrate_combo.isEnabled() is True
    assert widget.rts_hs_check.isEnabled() is True
    assert widget.bring_up_check.isEnabled() is False
    assert widget.fd_check.isEnabled() is False
    assert widget.serial_info.isHidden() is False


def test_driver_fields_follow_the_channel(qapp):
    dialog = _dialog_with_channel(qapp, "can0")
    widget = dialog.can_bus_widgets[0]
    assert widget.com_baudrate_combo.isEnabled() is False

    widget.channel_input.setCurrentText("/dev/cu.usbmodem123")
    assert widget.com_baudrate_combo.isEnabled() is True
    assert "SLCAN" in widget.driver_info.text()

    widget.channel_input.setCurrentText("2088339B413250013:1")
    assert widget.com_baudrate_combo.isEnabled() is False
    assert "gs_usb" in widget.driver_info.text()


def test_baudrate_label_becomes_nominal_bitrate_in_fd(qapp):
    config = {
        "language": "en",
        "can_buses": [
            {
                "name": "CAN1",
                "channel": "2088339B413250013:0",
                "baudrate": 500000,
                "listen_only": False,
                "fd": True,
                "dbitrate": 5_000_000,
            }
        ],
    }
    dialog = SettingsDialog(parent=None, config=config, usb_monitor=None)
    widget = dialog.can_bus_widgets[0]

    assert widget.baudrate_label.text() == "Nominal bitrate:"

    widget.fd_check.setChecked(False)
    assert widget.baudrate_label.text() == "Baudrate:"

    widget.fd_check.setChecked(True)
    assert widget.baudrate_label.text() == "Nominal bitrate:"
