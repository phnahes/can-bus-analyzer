"""
VAG UDS diagnostics helpers (ISO-TP on 0x700 + logical address).

Used by tools/general/vw/read_dtc.py and the OBD-II monitor (per-module DTCs).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import can

from .vag_dtc_sae_map import VAG_EVENT_TO_ISO

VAG_PAD = 0x55
NRC_RESPONSE_PENDING = 0x78
VAG_RX_OFFSET = 0x6A
VAG_TX_BASE = 0x700

DTC_STATUS_MASKS = (
    (0x08, "pendentes / test failed"),
    (0x04, "confirmados (stored)"),
    (0x01, "test failed"),
    (0x02, "test failed this cycle"),
    (0x20, "warning indicator"),
    (0xFF, "todas as máscaras"),
)

# Ordem do log VAG-LeituraDTCPainel.json (ODIS): 19 02 04 depois 19 02 08.
DTC_STATUS_MASKS_GUI = (
    (0x04, "confirmados (stored)"),
    (0x08, "pendentes / test failed"),
)

DTC_STATUS_BITS = {
    0: "testFailed",
    1: "testFailedThisCycle",
    2: "pendingDTC",
    3: "confirmedDTC",
    4: "testNotCompletedSinceLastClear",
    5: "testFailedSinceLastClear",
    6: "testNotCompletedThisCycle",
    7: "warningIndicatorRequested",
}


@dataclass(frozen=True)
class VagModule:
    key: str
    name: str
    tx_id: int
    rx_id: int
    logical_addr: int


MODULES: dict[str, VagModule] = {
    "abs": VagModule("abs", "ABS / ESP", 0x713, 0x77D, 0x13),
    "painel": VagModule(
        "painel",
        "Instrument cluster / Painel (ODIS 0017 · CAN 0x714)",
        0x714,
        0x77E,
        0x14,
    ),
    "airbag": VagModule("airbag", "Airbag", 0x715, 0x77F, 0x15),
}

VAG_ECU_NAMES: dict[int, str] = {
    0x01: "Motor (ECM)",
    0x02: "Transmissão (TCU)",
    0x08: "HVAC / Climatronic",
    0x09: "Central elétrica (BCM)",
    0x0A: "Park Assist (PDC/PLA)",
    0x0B: "TPMS (Tire Pressure)",
    0x0C: "Steering column electronics",
    0x0D: "Central comfort / KSG",
    0x0E: "Central electrics (CentrElect)",
    0x10: "Gateway",
    0x11: "Immobilizer",
    0x12: "Steering Assist (EPS)",
    0x13: "ABS / Brake (Brake1)",
    0x14: "Instrument cluster / Painel (ODIS 0017)",
    0x15: "Airbag",
    0x16: "Active Steering",
    0x17: "Rádio / MMI",
    0x18: "Auxiliary heater (park)",
    0x19: "Gateway (alt) / Clima rear",
    0x22: "AWD / 4Motion",
    0x25: "Imobilizador",
    0x32: "Kessy / Access & Start",
    0x37: "Navegação",
    0x42: "Door elect. driver",
    0x44: "Assistência de estacionamento",
    0x46: "Air Conditioning (Clima)",
    0x4E: "Lane Change Assist",
    0x4F: "Front sensor driver assist (MFK)",
    0x52: "Door elect. passenger",
    0x57: "Adaptive Cruise Control (ACC)",
    0x5F: "Infoeletrônica (MMI)",
    0x61: "Battery regulation",
    0x65: "TPMS",
    0x73: "Information Control Unit 1",
    0x75: "Telematics",
    0x76: "Driver assistance",
}


def module_at_logical_addr(addr: int) -> VagModule:
    for mod in MODULES.values():
        if mod.logical_addr == addr:
            return mod
    name = VAG_ECU_NAMES.get(addr, f"ECU 0x{addr:02X}")
    tx = VAG_TX_BASE + addr
    return VagModule(
        key=f"0x{addr:02X}",
        name=name,
        tx_id=tx,
        rx_id=tx + VAG_RX_OFFSET,
        logical_addr=addr,
    )


def list_modules_for_ui() -> list[VagModule]:
    addrs = sorted(set(VAG_ECU_NAMES.keys()) | {m.logical_addr for m in MODULES.values()})
    return [module_at_logical_addr(a) for a in addrs]


def pad_frame(payload: bytes) -> bytes:
    if len(payload) > 8:
        raise ValueError("Frame CAN must be at most 8 bytes")
    return payload + bytes([VAG_PAD] * (8 - len(payload)))


def build_single_frame(uds: bytes) -> bytes:
    if len(uds) > 7:
        raise ValueError("Use multi-frame for UDS payloads > 7 bytes")
    return pad_frame(bytes([len(uds)]) + uds)


def build_flow_control_frame(block_size: int = 0, st_min: int = 0) -> bytes:
    """ISO-TP Flow Control PCI (not a UDS Single Frame).

    Matches ODIS/VAG logs: 30 00 00 55 55 55 55 55
    """
    return pad_frame(bytes([0x30, block_size & 0xFF, st_min & 0xFF]))


def decode_dtc_two_bytes(high_byte: int, low_byte: int) -> str:
    """SAE base code from UDS bytes 1–2 (same encoding as OBD-II 2-byte DTC)."""
    prefixes = ("P", "C", "B", "U")
    prefix = prefixes[(high_byte >> 6) & 0x03]
    code_value = ((high_byte & 0x3F) << 8) | low_byte
    return f"{prefix}{code_value:04X}"


def decode_uds_dtc_iso14229(b0: int, b1: int, b2: int) -> str:
    """ISO 14229 3-byte DTC: 2-byte SAE base + failure-type byte (not 24-bit P-code)."""
    return f"{decode_dtc_two_bytes(b0, b1)}-{b2:02X}"


def format_sae_odis_compact(iso_or_sae: str) -> str:
    """ODIS-style 7-char SAE, e.g. U1202 00 / U1202-00 → U120200."""
    s = iso_or_sae.strip().upper()
    if s.startswith("U") and len(s) == 7 and s[1:].isdigit():
        return s
    parts = s.replace("-", " ").split()
    if len(parts) == 2 and len(parts[0]) == 5 and len(parts[1]) == 2:
        return f"{parts[0]}{parts[1]}"
    if "-" in s:
        base, ftb = s.rsplit("-", 1)
        if len(ftb) == 2:
            return f"{base}{ftb}"
    return s.replace(" ", "").replace("-", "")


def resolve_sae_display(b0: int, b1: int, b2: int) -> str:
    """SAE column like ODIS: map VAG event code when known, else ISO 14229 compact."""
    key = (b0 << 16) | (b1 << 8) | b2
    mapped = VAG_EVENT_TO_ISO.get(key)
    if mapped:
        return format_sae_odis_compact(mapped)
    return format_sae_odis_compact(decode_uds_dtc_iso14229(b0, b1, b2))


def format_dtc_status(status: int) -> str:
    flags = [name for bit, name in DTC_STATUS_BITS.items() if status & (1 << bit)]
    return ", ".join(flags) if flags else f"0x{status:02X}"


def format_vag_event_code(raw: bytes) -> str:
    """ODIS-style event code (hex + decimal), e.g. FFFF3A [16777018]."""
    if len(raw) != 3:
        return raw.hex().upper()
    event_hex = f"{raw[0]:02X}{raw[1]:02X}{raw[2]:02X}"
    dec = int.from_bytes(raw, "big")
    return f"{event_hex} [{dec}]"


def format_dtc_record_line(rec: DtcRecord) -> str:
    """ODIS-like: event code + SAE code + status (4th byte is DTC status, not part of event)."""
    event = format_vag_event_code(rec.raw)
    return (
        f"{event}  SAE {rec.sae}  "
        f"(status 0x{rec.status:02X}: {rec.status_text})"
    )


@dataclass
class DtcRecord:
    raw: bytes
    event: str
    sae: str
    status: int
    status_text: str


def parse_read_dtc_response(payload: bytes) -> tuple[int | None, list[DtcRecord]]:
    if len(payload) < 3 or payload[0] != 0x59 or payload[1] != 0x02:
        return None, []

    availability = payload[2]
    records: list[DtcRecord] = []
    i = 3
    while i + 4 <= len(payload):
        b0, b1, b2 = payload[i], payload[i + 1], payload[i + 2]
        status = payload[i + 3]
        raw = bytes([b0, b1, b2])
        records.append(
            DtcRecord(
                raw=raw,
                event=format_vag_event_code(raw),
                sae=resolve_sae_display(b0, b1, b2),
                status=status,
                status_text=format_dtc_status(status),
            )
        )
        i += 4

    return availability, records


def describe_negative(payload: bytes) -> str:
    if len(payload) < 3 or payload[0] != 0x7F:
        return payload.hex()
    svc, nrc = payload[1], payload[2]
    return f"NegativeResponse service=0x{svc:02X} NRC=0x{nrc:02X}"


def summarize_uds_response(payload: bytes) -> str:
    if not payload:
        return "(vazio)"
    svc = payload[0]
    if svc == 0x7E:
        return "TesterPresent (+rsp)"
    if svc == 0x50 and len(payload) >= 2:
        return f"DiagnosticSession 0x{payload[1]:02X}"
    if svc == 0x7F and len(payload) >= 3:
        return f"NegativeResponse NRC=0x{payload[2]:02X}"
    return payload[:4].hex().upper()


def is_response_pending(payload: bytes) -> bool:
    return (
        len(payload) >= 3
        and payload[0] == 0x7F
        and payload[2] == NRC_RESPONSE_PENDING
    )


class IsotpReassembler:
    """Accumulates ISO-TP frames into one UDS payload."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._buffer = bytearray()
        self._expected_len: int | None = None

    @property
    def is_multiframe_pending(self) -> bool:
        return self._expected_len is not None

    def feed(self, data: bytes) -> bytes | None:
        if not data:
            return None
        pci = data[0]
        frame_type = pci & 0xF0

        if frame_type == 0x00:
            length = pci & 0x0F
            self.reset()
            return bytes(data[1 : 1 + length])

        if frame_type == 0x10:
            self._expected_len = ((pci & 0x0F) << 8) | data[1]
            self._buffer = bytearray(data[2:])
            if self._expected_len <= len(self._buffer):
                payload = bytes(self._buffer[: self._expected_len])
                self.reset()
                return payload
            return None

        if frame_type == 0x20 and self._expected_len is not None:
            remaining = self._expected_len - len(self._buffer)
            if remaining <= 0:
                self.reset()
                return None
            chunk = data[1 : 1 + min(7, remaining)]
            self._buffer.extend(chunk)
            if len(self._buffer) >= self._expected_len:
                payload = bytes(self._buffer[: self._expected_len])
                self.reset()
                return payload

        return None

    def needs_flow_control(self, data: bytes) -> bool:
        return len(data) >= 1 and (data[0] & 0xF0) == 0x10


class IsotpVagClient:
    """Blocking UDS client (CLI tools)."""

    def __init__(self, bus: can.BusABC, module: VagModule):
        self.bus = bus
        self.module = module

    def send(self, uds: bytes) -> None:
        if len(uds) <= 7:
            self.bus.send(
                can.Message(
                    arbitration_id=self.module.tx_id,
                    data=build_single_frame(uds),
                    is_extended_id=False,
                )
            )
            return

        total = len(uds)
        ff = bytearray([0x10 | ((total >> 8) & 0x0F), total & 0xFF])
        ff.extend(uds[:6])
        self.bus.send(
            can.Message(
                arbitration_id=self.module.tx_id,
                data=pad_frame(bytes(ff)),
                is_extended_id=False,
            )
        )

        offset = 6
        seq = 1
        while offset < total:
            chunk = uds[offset : offset + 7]
            cf = bytes([0x20 | (seq & 0x0F)]) + chunk
            self.bus.send(
                can.Message(
                    arbitration_id=self.module.tx_id,
                    data=pad_frame(cf),
                    is_extended_id=False,
                )
            )
            offset += 7
            seq += 1
            time.sleep(0.005)

    def _send_flow_control(self) -> None:
        self.bus.send(
            can.Message(
                arbitration_id=self.module.tx_id,
                data=build_flow_control_frame(),
                is_extended_id=False,
            )
        )

    def receive_uds(self, timeout: float = 3.0) -> bytes | None:
        reasm = IsotpReassembler()
        deadline = time.time() + timeout

        while time.time() < deadline:
            msg = self.bus.recv(timeout=0.05)
            if msg is None or msg.arbitration_id != self.module.rx_id:
                continue
            data = bytes(msg.data)
            if reasm.needs_flow_control(data):
                self._send_flow_control()
            payload = reasm.feed(data)
            if payload is not None:
                return payload

        return None

    def transceive(self, uds: bytes, timeout: float = 3.0) -> bytes | None:
        self.send(uds)
        end = time.time() + timeout

        while time.time() < end:
            remaining = end - time.time()
            if remaining <= 0:
                break
            payload = self.receive_uds(timeout=min(remaining, 2.0))
            if payload is None:
                continue
            if is_response_pending(payload):
                continue
            return payload

        return None


def parse_isotp_single(data: bytes) -> bytes | None:
    """First frame / single frame only (ECU scan probe)."""
    if len(data) < 2:
        return None
    pci = data[0]
    if (pci & 0xF0) == 0x00:
        length = pci & 0x0F
        return bytes(data[1 : 1 + length])
    if (pci & 0xF0) == 0x10:
        return bytes(data[2:])
    return None


def probe_logical_address(
    bus: can.BusABC,
    logical_addr: int,
    timeout: float,
) -> bytes | None:
    """TesterPresent / DiagnosticSession on 0x700+addr; returns first UDS payload."""
    tx_id = VAG_TX_BASE + logical_addr
    rx_id = tx_id + VAG_RX_OFFSET

    def listen_until(deadline: float) -> bytes | None:
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            msg = bus.recv(timeout=min(0.025, remaining))
            if msg is None or msg.arbitration_id != rx_id:
                continue
            payload = parse_isotp_single(bytes(msg.data))
            if payload is not None:
                return payload
        return None

    bus.send(
        can.Message(
            arbitration_id=tx_id,
            data=build_single_frame(bytes([0x3E, 0x00])),
            is_extended_id=False,
        )
    )
    payload = listen_until(time.time() + timeout)
    if payload is not None:
        return payload

    bus.send(
        can.Message(
            arbitration_id=tx_id,
            data=build_single_frame(bytes([0x10, 0x01])),
            is_extended_id=False,
        )
    )
    return listen_until(time.time() + timeout)


def scan_responding_modules(
    bus: can.BusABC,
    addr_min: int = 0x01,
    addr_max: int = 0x7F,
    timeout: float = 0.07,
    verbose: bool = False,
) -> list[tuple[VagModule, bytes, str]]:
    found: list[tuple[VagModule, bytes, str]] = []
    total = addr_max - addr_min + 1
    for idx, addr in enumerate(range(addr_min, addr_max + 1), start=1):
        if verbose:
            print(
                f"  [{idx}/{total}] probe 0x{addr:02X} (TX 0x{VAG_TX_BASE + addr:03X})...",
                end="\r",
            )
        payload = probe_logical_address(bus, addr, timeout)
        if payload is None:
            continue
        mod = module_at_logical_addr(addr)
        found.append((mod, payload, summarize_uds_response(payload)))
    if verbose:
        print(" " * 60)
    return found


def resolve_module_key(selected: str) -> Iterable[VagModule]:
    key = selected.lower()
    if key == "all":
        return MODULES.values()
    if key in MODULES:
        return [MODULES[key]]
    if key.startswith("0x"):
        return [module_at_logical_addr(int(key, 16))]
    raise ValueError(f"Módulo desconhecido: {selected}")
