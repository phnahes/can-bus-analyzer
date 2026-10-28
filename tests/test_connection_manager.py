"""ConnectionManager: interface errors become a setup dialog, not a dead end."""

import pytest

from src.can_bus_manager import CANBusManager, CANBusConfig
from src.can_interface_setup import InterfaceDownError
from src.handlers.connection_manager import ConnectionManager
from src.logger import get_logger


@pytest.fixture
def manager():
    return ConnectionManager(
        message_callback=lambda *_: None,
        logger=get_logger(),
        config={},
        config_manager=None,
    )


def _buses():
    return [
        {"name": "CAN1", "channel": "can0", "baudrate": 500000, "listen_only": True},
        {"name": "CAN2", "channel": "can1", "baudrate": 250000, "listen_only": False},
    ]


def test_requests_only_for_interface_errors(manager):
    manager.can_bus_manager = CANBusManager()
    manager.can_bus_manager.connect_errors = {
        "CAN1": InterfaceDownError("can0", command="sudo ip link ...", reason="down"),
        "CAN2": RuntimeError("boom"),
    }

    requests = manager._interface_setup_requests(_buses())

    assert len(requests) == 1
    assert requests[0]["channel"] == "can0"
    assert requests[0]["bitrate"] == 500000
    assert requests[0]["listen_only"] is True
    assert requests[0]["command"] == "sudo ip link ..."


def test_requests_empty_without_errors(manager):
    manager.can_bus_manager = CANBusManager()
    assert manager._interface_setup_requests(_buses()) == []


def test_offer_returns_false_without_parent(manager):
    manager.can_bus_manager = CANBusManager()
    manager.can_bus_manager.connect_errors = {"CAN1": InterfaceDownError("can0")}

    assert manager._offer_interface_setup(_buses(), parent_widget=None) is False


def test_offer_returns_false_when_nothing_to_fix(manager):
    manager.can_bus_manager = CANBusManager()
    assert manager._offer_interface_setup(_buses(), parent_widget=object()) is False


def test_status_message_uses_kernel_bitrate(manager, monkeypatch):
    manager.can_bus_manager = CANBusManager()
    manager.can_bus_manager.add_bus(
        CANBusConfig(name="CAN1", channel="can0", baudrate=500000)
    )
    manager.can_bus_manager.buses["CAN1"].connected = True
    manager.can_bus_manager.buses["CAN1"].actual_bitrate = 1000000

    status = manager._format_status_message(_buses()[:1], ["CAN1"], is_simulation=False)

    assert "500k→1000k" in status


def test_status_message_falls_back_to_config_bitrate(manager):
    manager.can_bus_manager = CANBusManager()
    manager.can_bus_manager.add_bus(
        CANBusConfig(name="CAN1", channel="can0", baudrate=500000)
    )

    status = manager._format_status_message(_buses()[:1], [], is_simulation=True)

    assert "SIM" in status
    assert "500k" in status
    assert "kk" not in status
