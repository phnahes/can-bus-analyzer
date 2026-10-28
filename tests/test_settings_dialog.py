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
