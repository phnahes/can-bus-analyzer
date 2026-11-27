#!/usr/bin/env python3
"""
gs_usb / candleLight loopback stress test.

Opens a dual-channel adapter as one CandleBus (channel 0 -> channel 1), sends
sequence-numbered frames and verifies every one on the receiving channel.
The two channels must be wired together (CAN-H/CAN-L, terminated).

Examples
--------
    # CAN FD, 1 Mbit/s nominal, 8 Mbit/s data, 64 bytes, BRS, 20k frames
    python tools/general/stress_candle.py

    # 5 Mbit/s data phase, 100k smaller frames
    python tools/general/stress_candle.py --data-bitrate 5000000 --frames 100000

    # Classical CAN at 1 Mbit/s
    python tools/general/stress_candle.py --classic --nominal-bitrate 1000000

    # pick a device/channels explicitly
    python tools/general/stress_candle.py --serial 2088339B413250013 --tx 0 --rx 1
"""

import argparse
import struct
import sys
import threading
import time

try:
    import can
    import candle_api
except ImportError as exc:  # pragma: no cover - tool, not app code
    print(f"python-can-candle is required: {exc}")
    raise SystemExit(2)


def first_serial() -> str:
    devices = candle_api.list_device()
    if not devices:
        raise SystemExit("No gs_usb adapter found (is it plugged in?)")
    if len(devices) > 1:
        print("Multiple adapters found; using the first. Pass --serial to choose:")
        for device in devices:
            print(f"  {device.serial_number}  {device.product}")
    return str(devices[0].serial_number)


def build_bus(args):
    kwargs = dict(
        interface="candle",
        channel=[args.tx, args.rx],
        serial_number=args.serial,
        bitrate=args.nominal_bitrate,
        fd=not args.classic,
        listen_only=False,
        ignore_config=True,
    )
    if not args.classic:
        kwargs["data_bitrate"] = args.data_bitrate
        kwargs["data_sample_point"] = args.data_sample_point

    try:
        return can.Bus(**kwargs)
    except Exception as exc:
        raise SystemExit(f"Could not open {args.serial}:{args.tx}/{args.rx}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serial", default=None, help="adapter serial number")
    parser.add_argument("--tx", type=int, default=0, help="transmit channel (default 0)")
    parser.add_argument("--rx", type=int, default=1, help="receive channel (default 1)")
    parser.add_argument("--nominal-bitrate", type=int, default=1_000_000)
    parser.add_argument("--data-bitrate", type=int, default=8_000_000)
    parser.add_argument("--data-sample-point", type=float, default=87.5)
    parser.add_argument("--frames", type=int, default=20_000)
    parser.add_argument("--payload", type=int, default=64, help="bytes per frame")
    parser.add_argument("--no-brs", action="store_true", help="FD without bit rate switch")
    parser.add_argument("--classic", action="store_true", help="Classical CAN instead of FD")
    parser.add_argument("--drain", type=float, default=3.0,
                        help="seconds to wait for the last frames")
    args = parser.parse_args()

    if args.classic:
        args.payload = min(args.payload, 8)
    args.payload = max(0, min(args.payload, 64))
    if not 0 <= args.tx <= 63 or not 0 <= args.rx <= 63 or args.tx == args.rx:
        raise SystemExit("--tx/--rx must be different channel indexes")
    if args.serial is None:
        args.serial = first_serial()

    bus = build_bus(args)
    stop = threading.Event()
    lock = threading.Lock()
    seen = set()
    bad = 0
    bus_errors = 0
    rx_frames = 0

    def receiver():
        nonlocal bad, bus_errors, rx_frames
        while not stop.is_set():
            try:
                msg = bus.recv(timeout=0.05)
            except Exception:
                bus_errors += 1
                continue
            if msg is None:
                continue
            # Candle reports TX confirmations as is_rx=False.
            if msg.is_rx is False or msg.channel != args.rx:
                continue
            rx_frames += 1
            if msg.is_error_frame:
                bus_errors += 1
                continue
            if len(msg.data) != args.payload or bool(msg.is_fd) == args.classic:
                bad += 1
                continue
            if args.payload >= 4:
                seq = struct.unpack("<I", bytes(msg.data[:4]))[0]
                with lock:
                    if seq in seen:
                        bad += 1
                    else:
                        seen.add(seq)

    thread = threading.Thread(target=receiver, daemon=True)
    thread.start()

    fd = not args.classic
    brs = fd and not args.no_brs
    sent = 0
    send_errors = 0
    t0 = time.perf_counter()
    try:
        for index in range(args.frames):
            data = struct.pack("<I", index) if args.payload >= 4 else b""
            data += bytes([index & 0xFF]) * (args.payload - len(data))
            msg = can.Message(arbitration_id=0x100, data=data, is_fd=fd,
                              bitrate_switch=brs, channel=args.tx)
            try:
                bus.send(msg, timeout=1.0)
                sent += 1
            except Exception:
                send_errors += 1

        tx_time = time.perf_counter() - t0
        expected = sent
        deadline = time.time() + args.drain
        while time.time() < deadline and len(seen) < expected:
            time.sleep(0.01)
    finally:
        stop.set()
        thread.join(timeout=1.0)
        bus.shutdown()

    total_time = time.perf_counter() - t0
    unique = len(seen)
    lost = sent - unique if args.payload >= 4 else sent - rx_frames
    mode = "Classical" if args.classic else f"FD {args.data_bitrate // 1000}k"
    print(f"{mode}, {args.payload}B{' BRS' if brs else ''}, "
          f"{args.nominal_bitrate // 1000}k nominal")
    print(f"  sent={sent} tx_errors={send_errors} rx={rx_frames} unique={unique}")
    print(f"  lost={lost} bad={bad} bus_errors={bus_errors}")
    print(f"  tx={sent / tx_time:,.0f} fps "
          f"({sent * args.payload * 8 / tx_time / 1e6:.2f} Mbit/s payload), "
          f"rx={unique / total_time:,.0f} fps")

    ok = send_errors == 0 and bad == 0 and bus_errors == 0 and lost <= 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
