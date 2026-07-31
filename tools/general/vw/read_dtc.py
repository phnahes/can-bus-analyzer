#!/usr/bin/env python3
"""
Leitura de DTCs em módulos VAG via UDS (ISO-TP).

Uso (venv do projeto):
  ./venv/bin/python tools/general/vw/read_dtc.py -m painel --detect
  ./venv/bin/python tools/general/vw/read_dtc.py -m airbag --detect --clear
  ./venv/bin/python tools/general/vw/read_dtc.py --scan --detect
"""

from __future__ import annotations

import argparse
import glob
import sys
import time
from pathlib import Path

try:
    import can
except ImportError:
    print("Ative o venv e instale deps: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.vag_uds import (  # noqa: E402
    DTC_STATUS_MASKS,
    DTC_STATUS_MASKS_GUI,
    VAG_ECU_NAMES,
    DtcRecord,
    IsotpVagClient,
    VagModule,
    describe_negative,
    format_dtc_record_line,
    parse_read_dtc_response,
    probe_logical_address,
    resolve_module_key,
    scan_responding_modules,
)

SLCAN_GLOBS = (
    "/dev/cu.usbmodem*",
    "/dev/cu.usbserial*",
    "/dev/cu.wchusbserial*",
    "/dev/cu.SLAB_USBtoUART*",
    "/dev/tty.usbmodem*",
    "/dev/tty.usbserial*",
    "/dev/ttyACM*",
    "/dev/ttyUSB*",
)


def detect_slcan_channel() -> str | None:
    cu_paths: list[str] = []
    other: list[str] = []
    for pattern in SLCAN_GLOBS:
        for path in glob.glob(pattern):
            if path.startswith("/dev/cu."):
                cu_paths.append(path)
            else:
                other.append(path)
    paths = sorted(set(cu_paths)) or sorted(set(other))
    return paths[0] if paths else None


def print_scan_results(results: list[tuple[VagModule, bytes, str]]) -> None:
    print(f"\n{'=' * 72}")
    print(f"Módulos que responderam: {len(results)}")
    print("=" * 72)
    if not results:
        print("Nenhum endereço respondeu no intervalo varrido.")
        return

    print(f"{'Addr':>4}  {'TX':>5}  {'RX':>5}  {'Resposta':<28}  Nome")
    print("-" * 72)
    for mod, _payload, summary in results:
        print(
            f"0x{mod.logical_addr:02X}  "
            f"0x{mod.tx_id:03X}  "
            f"0x{mod.rx_id:03X}  "
            f"{summary:<28}  {mod.name}"
        )


def print_module_header(mod: VagModule) -> None:
    print(f"\n{'=' * 60}")
    print(
        f"{mod.name}  TX=0x{mod.tx_id:03X}  RX=0x{mod.rx_id:03X}  "
        f"(addr 0x{mod.logical_addr:02X})"
    )
    print("=" * 60)


def open_extended_session(client: IsotpVagClient, verbose: bool) -> None:
    if verbose:
        print("  → 10 03 (Extended Diagnostic Session)")
    resp = client.transceive(bytes([0x10, 0x03]), timeout=2.0)
    if resp and resp[0] == 0x50:
        print("  Sessão estendida: OK")
    elif resp:
        neg = describe_negative(resp) if resp[0] == 0x7F else resp.hex()
        print(f"  Sessão estendida: {neg}")
    else:
        print("  Sessão estendida: sem resposta (continuando)")


def _vag_count_dtcs_gui_masks(client: IsotpVagClient, verbose: bool) -> dict[bytes, DtcRecord]:
    found: dict[bytes, DtcRecord] = {}
    for mask, label in DTC_STATUS_MASKS_GUI:
        req = bytes([0x19, 0x02, mask])
        if verbose:
            print(f"  → verificação 19 02 {mask:02X} ({label})")
        resp = client.transceive(req, timeout=5.0)
        if resp is None or resp[0] == 0x7F:
            continue
        if resp[0] == 0x59 and len(resp) >= 2 and resp[1] == 0x02:
            _avail, records = parse_read_dtc_response(resp)
            for rec in records:
                found[rec.raw] = rec
    return found


def clear_dtcs_for_module(
    client: IsotpVagClient,
    extended_session: bool,
    verbose: bool,
    *,
    max_attempts: int = 3,
) -> bool:
    print_module_header(client.module)
    if extended_session:
        open_extended_session(client, verbose)

    for attempt in range(1, max_attempts + 1):
        if verbose:
            print(f"  → 14 FF FF FF (ClearDiagnosticInformation) [{attempt}/{max_attempts}]")
        resp = client.transceive(bytes([0x14, 0xFF, 0xFF, 0xFF]), timeout=10.0)
        if resp is None:
            print("  Apagar DTCs: sem resposta")
            return False
        if resp[0] == 0x7F:
            print(f"  Apagar DTCs: {describe_negative(resp)}")
            return False
        if resp[0] != 0x54:
            print(f"  Apagar DTCs: resposta inesperada {resp.hex()}")
            return False

        remaining = _vag_count_dtcs_gui_masks(client, verbose)
        if not remaining:
            if attempt > 1:
                print(f"  Apagar DTCs: OK ({attempt} comandos 14, verificação OK)")
            else:
                print("  Apagar DTCs: OK (resposta 54, verificação OK)")
            return True

        print(f"  Apagar DTCs: ainda {len(remaining)} DTC(s) após resposta 54")
        if attempt < max_attempts:
            print("  Repetindo 14 FF FF FF…")

    print(f"  Apagar DTCs: falhou — ainda {len(remaining)} DTC(s)")
    for rec in remaining.values():
        print(f"    • {format_dtc_record_line(rec)}")
    return False


def read_dtcs_for_module(
    client: IsotpVagClient,
    extended_session: bool,
    verbose: bool,
    *,
    print_header: bool = True,
) -> None:
    if print_header:
        print_module_header(client.module)
    if extended_session:
        open_extended_session(client, verbose)

    all_records: dict[bytes, DtcRecord] = {}
    for mask, label in DTC_STATUS_MASKS:
        req = bytes([0x19, 0x02, mask])
        if verbose:
            print(f"  → 19 02 {mask:02X} ({label})")
        resp = client.transceive(req, timeout=5.0)
        if resp is None:
            print(f"  Máscara 0x{mask:02X}: sem resposta")
            continue
        if resp[0] == 0x7F:
            print(f"  Máscara 0x{mask:02X}: {describe_negative(resp)}")
            continue
        availability, records = parse_read_dtc_response(resp)
        if availability is None:
            print(f"  Máscara 0x{mask:02X}: resposta inesperada {resp.hex()}")
            continue
        print(
            f"  Máscara 0x{mask:02X} ({label}): "
            f"availability=0x{availability:02X}, DTCs={len(records)}"
        )
        for rec in records:
            all_records[rec.raw] = rec

    if not all_records:
        print("\n  Nenhum DTC reportado.")
        return
    print(f"\n  Total único: {len(all_records)} DTC(s)")
    for rec in all_records.values():
        print(f"    • {format_dtc_record_line(rec)}")


def infer_interface(channel: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    if channel.startswith("/dev/") or channel.upper().startswith("COM"):
        return "slcan"
    return "socketcan"


def apply_connection_args(args: argparse.Namespace) -> None:
    if args.detect or args.channel is None:
        found = detect_slcan_channel()
        if found:
            args.channel = found
            print(f"Adaptador detectado: {found}")
        elif args.channel is None:
            args.channel = "can0"
    args.interface = infer_interface(args.channel, args.interface)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Lê/apaga DTCs VAG (UDS/ISO-TP).")
    p.add_argument("-m", "--module", default="all", help="abs | painel | airbag | all")
    p.add_argument("-i", "--interface", default=None)
    p.add_argument("-c", "--channel", default=None)
    p.add_argument("--detect", action="store_true")
    p.add_argument("-b", "--bitrate", type=int, default=500000)
    p.add_argument("--scan", action="store_true")
    p.add_argument("--scan-from", type=lambda x: int(x, 0), default=0x01)
    p.add_argument("--scan-to", type=lambda x: int(x, 0), default=0x7F)
    p.add_argument("--probe-ms", type=int, default=70)
    p.add_argument("--clear", action="store_true")
    p.add_argument("--extended-session", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main() -> None:
    args = build_parser().parse_args()
    apply_connection_args(args)

    bus = can.interface.Bus(
        channel=args.channel,
        interface=args.interface,
        bitrate=args.bitrate,
    )
    try:
        if args.scan:
            results = scan_responding_modules(
                bus,
                addr_min=args.scan_from,
                addr_max=args.scan_to,
                timeout=args.probe_ms / 1000.0,
                verbose=args.verbose,
            )
            print_scan_results(results)
            return

        for mod in resolve_module_key(args.module):
            client = IsotpVagClient(bus, mod)
            if args.clear:
                clear_dtcs_for_module(client, args.extended_session, args.verbose)
                print("\n  --- Verificação pós-clear ---")
                read_dtcs_for_module(
                    client, False, args.verbose, print_header=False
                )
            else:
                read_dtcs_for_module(client, args.extended_session, args.verbose)
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
