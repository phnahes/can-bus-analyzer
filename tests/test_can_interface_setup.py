"""SocketCAN link discovery / command building (no root, no hardware)."""

import json

import pytest

from src import can_interface_setup as cis

IP_JSON = json.dumps(
    [
        {
            "ifindex": 3,
            "ifname": "can0",
            "flags": ["NOARP"],
            "mtu": 16,
            "operstate": "UP",
            "linkinfo": {
                "info_kind": "can",
                "info_data": {
                    "ctrlmode": [{"name": "listen-only", "state": True}],
                    "bittiming": {"bitrate": 500000, "sample-point": 0.875},
                    "clock": 8000000,
                },
            },
        },
        {
            "ifindex": 4,
            "ifname": "can1",
            "flags": ["NOARP"],
            "mtu": 72,
            "operstate": "DOWN",
            "linkinfo": {
                "info_kind": "can",
                "info_data": {
                    "ctrlmode": ["fd"],
                    "bittiming": {"bitrate": 1000000},
                    "data_bittiming": {"bitrate": 5000000},
                },
            },
        },
        {
            "ifindex": 5,
            "ifname": "vcan0",
            "flags": ["NOARP"],
            "mtu": 16,
            "operstate": "UNKNOWN",
            "linkinfo": {"info_kind": "can", "info_data": {"bittiming": {"bitrate": 250000}}},
        },
    ]
)


@pytest.fixture(autouse=True)
def _linux_and_clean_cache(monkeypatch):
    """Tests must not depend on the host platform or on a warm cache."""
    monkeypatch.setattr(cis, "sys_is_linux", lambda: True)
    cis._invalidate_cache()
    yield
    cis._invalidate_cache()


class FakeRunner:
    """Records commands and returns canned (ok, output) results."""

    def __init__(self, *results):
        self.calls = []
        self.results = list(results)

    def __call__(self, argv, timeout=20.0):
        self.calls.append(list(argv))
        if self.results:
            return self.results.pop(0)
        return True, ""


def test_parse_up_link_with_bitrate_and_listen_only():
    links = cis.parse_link_list(IP_JSON)

    assert [link.name for link in links] == ["can0", "can1", "vcan0"]
    can0 = links[0]
    assert can0.up is True
    assert can0.bitrate == 500000
    assert can0.fd is False
    assert can0.listen_only is True


def test_parse_fd_link_with_data_bitrate():
    can1 = cis.parse_link_list(IP_JSON)[1]

    assert can1.up is False
    assert can1.bitrate == 1000000
    assert can1.dbitrate == 5000000
    assert can1.fd is True


def test_parse_unknown_operstate_is_down():
    vcan0 = cis.parse_link_list(IP_JSON)[2]
    assert vcan0.up is False
    assert vcan0.bitrate == 250000


@pytest.mark.parametrize("payload", ["", "   ", "not json", "{}x", "[1,2]"])
def test_parse_tolerates_garbage(payload):
    assert cis.parse_link_list(payload) == []


def test_parse_drops_entries_without_ifname():
    assert cis.parse_link_list(json.dumps([{"flags": ["UP"]}])) == []


def test_build_up_command_classic():
    argv = cis.build_up_command("can2", 500000)

    assert argv[1:] == [
        "link", "set", "dev", "can2", "up", "type", "can", "bitrate", "500000"
    ]


def test_build_up_command_fd_and_listen_only():
    argv = cis.build_up_command("can2", 500000, dbitrate=5000000, fd=True, listen_only=True)

    assert argv[argv.index("dbitrate") + 1] == "5000000"
    assert argv[argv.index("fd") + 1] == "on"
    assert argv[argv.index("listen-only") + 1] == "on"


def test_build_up_command_fd_requires_data_bitrate():
    with pytest.raises(ValueError):
        cis.build_up_command("can2", 500000, fd=True)


def test_format_command_is_copy_pasteable():
    argv = cis.build_up_command("can2", 500000)
    assert cis.format_command(argv).startswith("sudo ")
    assert "link set dev can2 up type can bitrate 500000" in cis.format_command(argv)


def test_list_can_interfaces_uses_runner_and_caches():
    runner = FakeRunner((True, IP_JSON))

    first = cis.list_can_interfaces(runner=runner)
    second = cis.list_can_interfaces(runner=runner)

    assert len(first) == len(second) == 3
    assert len(runner.calls) == 1  # cached for ~1s


def test_list_can_interfaces_returns_empty_on_failure():
    runner = FakeRunner((False, "ip: command not found"))
    assert cis.list_can_interfaces(runner=runner) == []


def test_get_link_finds_by_name():
    runner = FakeRunner((True, IP_JSON))
    assert cis.get_link("can1", runner=runner).dbitrate == 5000000
    assert cis.get_link("can9", runner=runner) is None


def test_bring_up_runs_command_and_invalidates_cache():
    runner = FakeRunner((True, ""))

    ok, output, argv = cis.bring_up("can2", 500000, runner=runner, elevate=False)

    assert ok is True
    assert runner.calls == [argv]
    assert "can2" in argv


def test_bring_up_retries_after_busy():
    runner = FakeRunner((False, "RTNETLINK answers: Device or resource busy"), (True, ""))

    ok, _, _ = cis.bring_up("can2", 500000, runner=runner, elevate=False)

    assert ok is True
    assert len(runner.calls) == 3  # up -> down -> up
    assert "down" in runner.calls[1]


def test_bring_up_without_pkexec_reports_manual_command(monkeypatch):
    monkeypatch.setattr(cis, "_is_root", lambda: False)
    monkeypatch.setattr(cis.shutil, "which", lambda name: None)
    runner = FakeRunner((True, ""))

    ok, output, argv = cis.bring_up("can2", 500000, runner=runner)

    assert ok is False
    assert "pkexec" in output
    assert argv  # still returned so the UI can show it


@pytest.mark.parametrize(
    "channel,matches",
    [
        ("can0", True),
        ("can12", True),
        ("vcan0", True),
        ("CAN0", False),
        ("can", False),
        ("speedcan0", False),
        ("/dev/ttyUSB0", False),
    ],
)
def test_channel_regex(channel, matches):
    assert bool(cis.CAN_CHANNEL_RE.match(channel)) is matches
