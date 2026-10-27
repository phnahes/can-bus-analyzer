"""
CAN interface discovery and link setup (Linux / SocketCAN).

SocketCAN owns the bit timing, so ``python-can``'s ``bitrate`` argument is
ignored for that backend and the interface has to be configured (and brought
*up*) outside the app. This module reads the kernel state via

    ip -j -d link show type can

and builds/executes the matching ``ip link set`` command, optionally elevated
with ``pkexec`` so the user gets a normal desktop authorization prompt instead
of the app running sudo silently.

Nothing here runs on macOS (SLCAN): the command runner is injectable so the
whole module is testable without root or real hardware.
"""

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

CAN_CHANNEL_RE = re.compile(r"^(v?can\d+)$")


@dataclass
class CanLink:
    """State of one SocketCAN interface."""
    name: str
    up: bool = False
    bitrate: Optional[int] = None
    dbitrate: Optional[int] = None
    fd: bool = False
    listen_only: bool = False

    @property
    def summary(self) -> str:
        parts = [f"{self.bitrate // 1000}k" if self.bitrate else "no bitrate"]
        if self.fd:
            parts.append(f"FD {self.dbitrate // 1000}k" if self.dbitrate else "FD")
        if self.listen_only:
            parts.append("listen-only")
        parts.append("UP" if self.up else "DOWN")
        return ", ".join(parts)


class InterfaceDownError(Exception):
    """Raised when a SocketCAN interface exists but is not usable."""

    def __init__(self, channel: str, command: Optional[str] = None,
                 detail: str = "", reason: str = "down"):
        self.channel = channel
        self.command = command
        self.detail = detail
        self.reason = reason
        super().__init__(detail or f"Interface {channel} is {reason}")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _ctrlmode_names(info_data: Dict) -> List[str]:
    """``ctrlmode`` may be a list of names or of {"name": ..., "state": bool}."""
    names = []
    for item in info_data.get("ctrlmode") or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            if item.get("state", True) is False:
                continue
            name = item.get("name")
            if name:
                names.append(name)
    return names


def parse_link_list(payload: str) -> List[CanLink]:
    """Parse the JSON output of ``ip -j -d link show type can``.

    Tolerant on purpose: iproute2 versions differ in how ``ctrlmode`` and the
    bit timing blocks are rendered.
    """
    if not payload or not payload.strip():
        return []

    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return []

    if isinstance(data, dict):
        data = [data]

    links: List[CanLink] = []
    for entry in data or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("ifname")
        if not name:
            continue

        flags = [str(f).upper() for f in entry.get("flags") or []]
        operstate = str(entry.get("operstate") or "").upper()
        up = operstate == "UP" or "UP" in flags

        linkinfo = entry.get("linkinfo") or {}
        info_data = linkinfo.get("info_data") or {}
        ctrl = _ctrlmode_names(info_data)

        bittiming = info_data.get("bittiming") or {}
        data_bittiming = info_data.get("data_bittiming") or {}

        bitrate = bittiming.get("bitrate")
        dbitrate = data_bittiming.get("bitrate")

        links.append(
            CanLink(
                name=str(name),
                up=up,
                bitrate=int(bitrate) if bitrate else None,
                dbitrate=int(dbitrate) if dbitrate else None,
                fd=("fd" in ctrl) or bool(data_bittiming),
                listen_only="listen-only" in ctrl,
            )
        )

    return links


# ---------------------------------------------------------------------------
# Command construction / execution
# ---------------------------------------------------------------------------

def _ip_binary() -> str:
    return shutil.which("ip") or "/sbin/ip"


def build_up_command(name: str, bitrate: int, dbitrate: Optional[int] = None,
                     fd: bool = False, listen_only: bool = False) -> List[str]:
    """Build the canonical ``ip link set ... up type can ...`` argv."""
    argv = [_ip_binary(), "link", "set", "dev", name, "up", "type", "can",
            "bitrate", str(int(bitrate))]

    if fd:
        if not dbitrate:
            raise ValueError("CAN FD needs a data bitrate")
        argv += ["dbitrate", str(int(dbitrate)), "fd", "on"]

    if listen_only:
        argv += ["listen-only", "on"]

    return argv


def build_down_command(name: str) -> List[str]:
    return [_ip_binary(), "link", "set", "dev", name, "down"]


def format_command(argv: Sequence[str]) -> str:
    """Human-readable (copy/paste) form, prefixed with sudo."""
    return "sudo " + " ".join(str(part) for part in argv)


def default_runner(argv: Sequence[str], timeout: float = 20.0) -> Tuple[bool, str]:
    """Run a command, never raising. Returns (ok, combined output)."""
    try:
        result = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        return result.returncode == 0, output
    except FileNotFoundError as exc:
        return False, f"command not found: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def list_can_interfaces(runner: Optional[Callable] = None,
                        use_cache: bool = True) -> List[CanLink]:
    """List SocketCAN interfaces, or [] when unsupported/unavailable."""
    global _CACHE
    if not sys_is_linux():
        return []

    now = _monotonic()
    if use_cache and _CACHE and (now - _CACHE[0]) < 1.0:
        return list(_CACHE[1])

    runner = runner or default_runner
    ok, output = runner([_ip_binary(), "-j", "-d", "link", "show", "type", "can"])
    links = parse_link_list(output) if ok else []

    _CACHE = (now, links)
    return list(links)


def get_link(name: str, runner: Optional[Callable] = None,
             use_cache: bool = True) -> Optional[CanLink]:
    for link in list_can_interfaces(runner=runner, use_cache=use_cache):
        if link.name == name:
            return link
    return None


def ip_available() -> bool:
    """True when the `ip` binary exists (we can read the link state)."""
    return shutil.which("ip") is not None


def bring_up(name: str, bitrate: int, dbitrate: Optional[int] = None,
             fd: bool = False, listen_only: bool = False,
             runner: Optional[Callable] = None,
             elevate: bool = True) -> Tuple[bool, str, List[str]]:
    """Bring an interface up with the requested timings.

    Returns (ok, output, argv). Runs through ``pkexec`` when available and the
    process is not already root; the argv is always returned so the UI can show
    exactly what was executed.
    """
    argv = build_up_command(
        name, bitrate, dbitrate=dbitrate, fd=fd, listen_only=listen_only
    )

    cmd = list(argv)
    if elevate and not _is_root():
        pkexec = shutil.which("pkexec")
        if not pkexec:
            return False, "pkexec not available; run the command manually", argv
        # pkexec requires an absolute program path.
        cmd = [pkexec, cmd[0]] + cmd[1:]

    runner = runner or default_runner
    ok, output = runner(cmd)

    # Reconfiguring a live interface can fail with EBUSY: retry once after down.
    if not ok and "busy" in output.lower():
        down = build_down_command(name)
        if elevate and not _is_root():
            down = [shutil.which("pkexec") or "pkexec", down[0]] + down[1:]
        runner(down)
        ok, output = runner(cmd)

    _invalidate_cache()
    return ok, output, argv


def _invalidate_cache():
    global _CACHE
    _CACHE = None


def _cache_state():
    return _CACHE


# Kept as module-level state so callers can share one 1s cache.
_CACHE = None


def _monotonic() -> float:
    import time
    return time.monotonic()


def _is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def sys_is_linux() -> bool:
    import sys
    return sys.platform.startswith("linux")
