#!/usr/bin/env python3
"""
Headless UI load benchmark.

Feeds synthetic frames through the real receive pipeline (message queue ->
UIUpdateHandler -> ReceiveTableManager -> QTableWidget) and reports tick
latency, so UI stalls can be reproduced without any CAN hardware.

Examples
--------
    # reporter's case: random IDs, ~ saturating a 500 kbit bus
    python tools/general/bench_ui_feed.py --rate 3000 --seconds 15

    # older behaviour check: watch a single ID
    python tools/general/bench_ui_feed.py --rate 5000 --mode monitor --ids fixed

    # tracer + ring buffer
    python tools/general/bench_ui_feed.py --rate 2000 --mode tracer --max-rows 5000
"""

import argparse
import os
import queue
import random
import statistics
import sys
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtGui import QColor  # noqa: E402
from PyQt6.QtWidgets import QApplication, QTableWidget  # noqa: E402

from src.handlers.message_handler import MessageHandler  # noqa: E402
from src.handlers.ui_update_handler import UIUpdateHandler  # noqa: E402
from src.logger import init_logger  # noqa: E402
from src.models import CANMessage  # noqa: E402
from src.ui.receive_table_manager import ReceiveTableManager  # noqa: E402


class BenchWindow:
    """Minimal stand-in for CANAnalyzerWindow (only what the pipeline needs)."""

    def __init__(self, queue_size: int, tracer: bool, max_rows: int, logger=None):
        from collections import defaultdict

        self.message_queue = queue.Queue(maxsize=queue_size)
        self.received_messages = []
        self.message_counters = defaultdict(int)
        self.message_last_timestamp = {}
        self.paused = False
        self.connected = True
        self.recording = tracer  # Tracer mode only renders while recording
        self.tracer_mode = tracer
        self.split_screen_mode = False
        self.receive_table_left = None
        self.receive_table_right = None
        self.triggers_enabled = False
        self._ftcan_dialog = None
        self._bap_dialog = None
        self.logger = logger
        self._dropped_frames = 0
        self.message_count_updates = 0

        self.recording_mgr = self
        self.recorded = []

        self.colors = {
            "normal_bg": QColor("#101010"),
            "normal_text": QColor("#f0f0f0"),
            "highlight": QColor("#303030"),
        }

        self.message_handler = MessageHandler(self)
        self.receive_table_mgr = ReceiveTableManager(self, self.message_handler)
        self.receive_table_mgr.max_tracer_rows = max_rows
        self.receive_table = QTableWidget()
        self.receive_table_mgr.setup_table(self.receive_table, tracer_mode=tracer)

    # -- callbacks used by the pipeline -----------------------------------
    def add_message_tracer_mode(self, msg, highlight=True):
        msg_index = len(self.recorded) - 1 if self.recording else None
        self.receive_table_mgr.add_message_tracer(
            self.receive_table, msg, highlight, msg_index=msg_index
        )

    def add_message_monitor_mode(self, msg, highlight=True, target_table=None):
        self.receive_table_mgr.add_message_monitor(
            self.receive_table, msg, self.colors, highlight
        )

    def update_message_count(self):
        self.message_count_updates += 1

    def check_and_fire_triggers(self, msg):
        pass

    def add_message(self, msg):
        """RecordingHandler.add_message stub."""
        self.recorded.append(msg)

    def get_message_count(self):
        return len(self.recorded)


def producer(window, rate, seconds, ids_mode, stop_event):
    """Push frames at ~rate fps (same shape as a busy bus)."""
    period = 1.0 / rate
    next_at = time.perf_counter()
    random_ids = list(range(0x100, 0x100 + 800))
    counter = 0
    while not stop_event.is_set():
        if ids_mode == "random":
            can_id = random.choice(random_ids)
        else:
            can_id = 0x100 + (counter % 4)
        msg = CANMessage(
            timestamp=time.time(),
            can_id=can_id,
            dlc=8,
            data=bytes([counter & 0xFF] * 8),
            source="CAN1",
        )
        try:
            window.message_queue.put_nowait(msg)
            if window.recording:
                window.recorded.append(msg)
        except queue.Full:
            window._dropped_frames += 1

        counter += 1
        next_at += period
        sleep_for = next_at - time.perf_counter()
        if sleep_for > 0:
            time.sleep(sleep_for)
        else:
            next_at = time.perf_counter()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rate", type=int, default=2000, help="frames per second (default 2000)")
    parser.add_argument("--seconds", type=float, default=10.0, help="run duration (default 10)")
    parser.add_argument("--mode", choices=["monitor", "tracer"], default="monitor")
    parser.add_argument("--ids", choices=["random", "fixed"], default="random",
                        help="random = cangen default, fixed = few recurring IDs")
    parser.add_argument("--max-rows", type=int, default=20000,
                        help="tracer row cap (0 = unlimited)")
    parser.add_argument("--queue-size", type=int, default=50000)
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()

    init_logger(log_dir=os.path.join(REPO_ROOT, "logs"))
    from src.logger import get_logger

    app = QApplication([])
    window = BenchWindow(args.queue_size, args.mode == "tracer", args.max_rows, logger=get_logger())
    handler = UIUpdateHandler(window)

    ticks = []
    stop_event = threading.Event()

    def on_tick():
        start = time.perf_counter()
        handler.update_ui()
        ticks.append((time.perf_counter() - start) * 1000.0)

    timer = QTimer()
    timer.timeout.connect(on_tick)
    timer.start(args.tick_ms)

    thread = threading.Thread(
        target=producer,
        args=(window, args.rate, args.seconds, args.ids, stop_event),
        daemon=True,
    )
    started = time.perf_counter()
    thread.start()

    def finish():
        stop_event.set()
        timer.stop()
        elapsed = time.perf_counter() - started
        app.quit()

    QTimer.singleShot(int(args.seconds * 1000), finish)
    app.exec()

    displayed = window.receive_table.rowCount()
    if not ticks:
        print("no ticks recorded")
        return 1

    ticks_sorted = sorted(ticks)
    p = lambda q: ticks_sorted[min(len(ticks_sorted) - 1, int(len(ticks_sorted) * q))]
    expected = args.rate * args.seconds
    shown = displayed if args.mode == "monitor" else displayed

    print()
    print(f"mode={args.mode} ids={args.ids} rate={args.rate}/s duration={args.seconds:.0f}s")
    print(f"frames produced : {int(expected)}")
    print(f"frames dropped  : {window._dropped_frames}")
    print(f"rows on screen  : {displayed}")
    print(f"ticks           : {len(ticks)}")
    print(f"tick p50/p95/p99/max : {p(0.50):.1f} / {p(0.95):.1f} / {p(0.99):.1f} / {max(ticks):.1f} ms")
    print(f"ui updates      : {window.message_count_updates}")
    if p(0.95) > args.tick_ms * 2:
        print("\nFAIL: p95 tick above 2x the timer interval (UI cannot keep up)")
        return 2
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
