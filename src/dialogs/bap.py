"""
VAG BAP Dialog - Dedicated UI for BAP detection/inspection
"""

from __future__ import annotations

import json
import threading
import time
import queue
import math
from datetime import datetime
from typing import List, Dict, Optional, Any

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QGroupBox,
    QTextEdit,
    QCheckBox,
    QComboBox,
    QHeaderView,
    QLineEdit,
    QTabWidget,
    QWidget,
    QFileDialog,
    QMessageBox,
    QSplitter,
    QFrame,
)
from PyQt6.QtCore import Qt, QTimer, QItemSelection, QItemSelectionModel
from PyQt6.QtGui import QFont, QFontMetrics

from ..models import CANMessage
from ..decoders.decoder_bap import BAPDecoder, BAPDetectionMode


# Thread-safe cache lock for details panel
_details_cache_lock = threading.Lock()


class _BAPDecodeWorker:
    """
    Background worker for BAP decoding/reassembly.

    Note: BAP reassembly is stateful and order-dependent per stream, so we keep a
    single decoder instance here. If we later want multiple workers, we'd need
    deterministic sharding by (can_id, mf_channel, platform) to preserve order.
    """

    def __init__(self, max_inflight: int = 20000):
        self.decoder = BAPDecoder(detection_mode=BAPDetectionMode.CONSERVATIVE)
        # Set maxsize to prevent unbounded memory growth if decoder stalls
        self.in_q: "queue.Queue[CANMessage]" = queue.Queue(maxsize=25000)
        self.out_q: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=25000)
        self.max_inflight = int(max_inflight)
        self.running = True
        self.dropped = 0
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def set_mode(self, mode: str) -> None:
        self.decoder.set_detection_mode(mode)

    def stop(self) -> None:
        self.running = False
        try:
            self.in_q.put_nowait(None)  # type: ignore[arg-type]
        except Exception:
            pass

    def submit(self, msg: CANMessage) -> None:
        if not self.running:
            return
        # Backpressure: if queue grows too much, drop to keep app responsive.
        try:
            if self.in_q.qsize() > self.max_inflight:
                self.dropped += 1
                return
        except Exception:
            pass
        try:
            self.in_q.put_nowait(msg)
        except Exception:
            self.dropped += 1

    def _run(self) -> None:
        while self.running:
            try:
                msg = self.in_q.get(timeout=0.25)
            except Exception:
                continue

            if msg is None:
                continue

            try:
                decoded = self.decoder.decode_message(
                    msg.can_id,
                    msg.data,
                    is_extended=bool(getattr(msg, "is_extended", msg.can_id > 0x7FF)),
                    timestamp=float(getattr(msg, "timestamp", 0.0) or 0.0),
                )
            except Exception:
                continue

            if not decoded:
                continue

            # Push a record containing both msg + decoded.
            try:
                self.out_q.put_nowait({"msg": msg, "decoded": decoded})
            except Exception:
                # If UI can't keep up, drop results.
                self.dropped += 1


class BAPDialog(QDialog):
    """
    Dialog to inspect detected BAP messages.

    Default: conservative (high confidence) -> only multi-frame completions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VAG BAP Analyzer")
        self.resize(1200, 720)

        self.worker = _BAPDecodeWorker(max_inflight=20000)
        # Kept for backward-compat; worker is the primary pipeline.
        self._rx_queue: List[CANMessage] = []

        # Records are kept for export/import/refiltering:
        #   record = {"msg": {...}, "decoded": {...}}
        self._decoded_records: List[Dict[str, Any]] = []
        self._raw_records: List[Dict[str, Any]] = []
        # Index for fast lookup on click (packet_id -> raw records)
        self._raw_records_by_packet: Dict[int, List[Dict[str, Any]]] = {}
        # Cache for expensive Details formatting
        self._details_cache: Dict[tuple, str] = {}
        self._total_frames_seen = 0
        self._last_lag_ms: int = 0

        self._known_sources: set[str] = set()
        self._suppress_selection_handlers = False
        self._highlighted_packet_id: Optional[int] = None
        self._analysis_paused: bool = False
        self._dropped_while_paused: int = 0
        self._replay_thread: Optional[threading.Thread] = None
        self._replay_stop = threading.Event()
        self._split_msgs: Optional[QSplitter] = None
        self._split_raw: Optional[QSplitter] = None
        self._split_applied_once: bool = False
        self._split_ratio_msgs: float = 0.85  # 85% table / 15% details
        self._split_ratio_raw: float = 0.85   # 85% table / 15% details
        self._did_autosize_cols_msgs: bool = False
        self._did_autosize_cols_raw: bool = False

        self._setup_ui()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_queue)
        self.update_timer.start(100)

    def showEvent(self, event) -> None:
        # Apply initial splitter ratio after the window has a real size.
        # Qt can ignore early setSizes() during layout negotiation, which results in 50/50.
        try:
            super().showEvent(event)
        except Exception:
            pass

        if self._split_applied_once:
            return
        self._split_applied_once = True

        # Apply splitter ratios after layout is done
        QTimer.singleShot(100, self._apply_splitter_ratios)

    def resizeEvent(self, event) -> None:
        # Keep splitter proportions consistent on window resize.
        try:
            super().resizeEvent(event)
        except Exception:
            pass
        self._apply_splitter_ratios()

    def _apply_splitter_ratios(self) -> None:
        def apply(splitter: Optional[QSplitter], ratio: float) -> None:
            if not splitter:
                return
            try:
                # Use the actual splitter space, not the window height.
                total = int(splitter.size().height())
                if total <= 0:
                    return

                rr = max(0.40, min(0.60, float(ratio)))
                w_left = splitter.widget(0)
                w_right = splitter.widget(1)
                sizes_now = splitter.sizes() or []
                # If details pane is explicitly hidden, keep it collapsed.
                # Note: do NOT keep it collapsed just because size==0, otherwise Show Details can't restore it.
                if w_right is not None and (not w_right.isVisible()):
                    splitter.setSizes([max(1, total), 0])
                    return
                min_left = int(w_left.minimumSize().height()) if w_left else 1
                min_right = int(w_right.minimumSize().height()) if w_right else 1

                # Desired sizes
                left = int(total * rr)
                right = total - left

                # Clamp by minimums
                if right < min_right:
                    right = min_right
                    left = total - right
                if left < min_left:
                    left = min_left
                    right = total - left

                left = max(1, left)
                right = max(1, right)

                # Avoid churn if already close (prevents jitter).
                sizes = splitter.sizes()
                if sizes and len(sizes) >= 2 and total > 0:
                    cur_r = float(sizes[0]) / float(sum(sizes) or total)
                    if abs(cur_r - rr) < 0.02:
                        return

                splitter.setSizes([left, right])
            except Exception:
                return

        apply(self._split_msgs, self._split_ratio_msgs)
        apply(self._split_raw, self._split_ratio_raw)

    def _update_split_ratio_from_widget(self, which: str) -> None:
        try:
            splitter = self._split_msgs if which == "msgs" else self._split_raw
            if not splitter:
                return
            sizes = splitter.sizes()
            if not sizes or len(sizes) < 2:
                return
            total = float(sum(sizes))
            if total <= 0:
                return
            ratio = float(sizes[0]) / total
            ratio = max(0.10, min(0.90, ratio))
            if which == "msgs":
                self._split_ratio_msgs = ratio
            else:
                self._split_ratio_raw = ratio
            self._sync_details_toggle_state(which)
        except Exception:
            pass

    def _toggle_details_visible(self, which: str) -> None:
        """Toggle details panel visibility for the current tab only."""
        splitter = self._split_msgs if which == "msgs" else self._split_raw
        btn = getattr(self, "_hide_details_btn_msgs", None) if which == "msgs" else getattr(self, "_hide_details_btn_raw", None)
        if not splitter or not btn:
            return
        try:
            details_w = splitter.widget(1)
            if not details_w:
                return
            sizes = splitter.sizes() or []
            collapsed = bool(len(sizes) >= 2 and int(sizes[1]) <= 0)
            is_hidden = (not details_w.isVisible()) or collapsed

            if not is_hidden:
                details_w.setVisible(False)
                splitter.setSizes([max(1, splitter.size().height()), 0])
            else:
                details_w.setVisible(True)
                self._apply_splitter_ratios()
            self._sync_details_toggle_state(which)
        except Exception:
            pass

    @staticmethod
    def _vline() -> QFrame:
        """Small vertical separator for button bars."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setFixedHeight(18)
        return line

    def _sync_details_toggle_state(self, which: str) -> None:
        """Keep Hide/Show button text in sync with actual details state."""
        try:
            splitter = self._split_msgs if which == "msgs" else self._split_raw
            btn = getattr(self, "_hide_details_btn_msgs", None) if which == "msgs" else getattr(self, "_hide_details_btn_raw", None)
            if not splitter or not btn:
                return
            details_w = splitter.widget(1)
            if not details_w:
                return

            sizes = splitter.sizes() or []
            collapsed = bool(len(sizes) >= 2 and int(sizes[1]) <= 0)
            is_hidden = (not details_w.isVisible()) or collapsed
            btn.setText("Show Details" if is_hidden else "Hide Details")
        except Exception:
            pass

    def _on_bap_tab_changed(self, _idx: int) -> None:
        # When user switches tabs, ensure each tab's Hide/Show text matches current state.
        self._sync_details_toggle_state("msgs")
        self._sync_details_toggle_state("raw")

    @staticmethod
    def _parse_int(text: str) -> Optional[int]:
        s = (text or "").strip()
        if not s:
            return None
        try:
            if s.lower().startswith("0x"):
                return int(s, 16)
            # treat bare hex if it contains hex letters
            if any(c in "abcdefABCDEF" for c in s):
                return int(s, 16)
            return int(s, 10)
        except Exception:
            return None

    @staticmethod
    def _msg_to_record(msg: CANMessage) -> Dict[str, Any]:
        return {
            "timestamp": float(getattr(msg, "timestamp", 0.0) or 0.0),
            "source": str(getattr(msg, "source", "") or ""),
            "can_id": int(getattr(msg, "can_id", 0) or 0),
            "is_extended": bool(getattr(msg, "is_extended", (getattr(msg, "can_id", 0) or 0) > 0x7FF)),
            "dlc": int(getattr(msg, "dlc", len(getattr(msg, "data", b"") or b""))),
            "data_hex": (getattr(msg, "data", b"") or b"").hex(),
        }

    @staticmethod
    def _record_to_msg(rec: Dict[str, Any]) -> CANMessage:
        can_id = int(rec.get("can_id") or 0)
        data_hex = str(rec.get("data_hex") or "")
        data = bytes.fromhex(data_hex) if data_hex else b""
        return CANMessage(
            timestamp=float(rec.get("timestamp") or 0.0),
            can_id=can_id,
            dlc=int(rec.get("dlc") or len(data)),
            data=data,
            is_extended=bool(rec.get("is_extended", can_id > 0x7FF)),
            source=str(rec.get("source") or ""),
        )

    def _get_state_for_export(self) -> Dict[str, Any]:
        return {
            "detection_mode": self.mode_combo.currentData() or BAPDetectionMode.CONSERVATIVE.value,
            "filters": {
                "can_id": self.filter_canid.text(),
                "lsg": self.filter_lsg.text(),
                "source": self.filter_source.currentData() or "",
            },
        }

    def _apply_state_from_import(self, state: Dict[str, Any]) -> None:
        # Detection mode
        mode = str(state.get("detection_mode") or "")
        if mode:
            # find matching item by data
            for i in range(self.mode_combo.count()):
                if str(self.mode_combo.itemData(i)) == mode:
                    self.mode_combo.setCurrentIndex(i)
                    break

        # Filters
        filters = state.get("filters") or {}
        if isinstance(filters, dict):
            self.filter_canid.setText(str(filters.get("can_id") or ""))
            self.filter_lsg.setText(str(filters.get("lsg") or ""))

            # Source: it may not exist yet; we'll select it if present.
            src = str(filters.get("source") or "")
            if src:
                for i in range(self.filter_source.count()):
                    if str(self.filter_source.itemData(i) or "") == src:
                        self.filter_source.setCurrentIndex(i)
                        break

    def _notify(self, message: str, duration_ms: int = 2500) -> None:
        """
        Prefer main window bottom-right notifications (show_notification).
        Fall back to updating the header stats label.
        """
        try:
            parent = self.parent()
            if parent and hasattr(parent, "show_notification"):
                parent.show_notification(str(message), int(duration_ms))
                return
        except Exception:
            pass
        try:
            # Fallback: temporary text in stats label
            self.stats_label.setText(str(message))
        except Exception:
            pass

    def _get_parent_bus_manager(self):
        try:
            parent = self.parent()
            return getattr(parent, "can_bus_manager", None) if parent else None
        except Exception:
            return None

    def _get_connected_buses(self) -> List[str]:
        mgr = self._get_parent_bus_manager()
        if not mgr:
            return []
        try:
            return list(mgr.get_connected_buses())
        except Exception:
            return []

    def _send_frame(self, bus_name: str, msg: CANMessage) -> bool:
        mgr = self._get_parent_bus_manager()
        if not mgr:
            return False
        try:
            return bool(mgr.send_to(bus_name, msg))
        except Exception:
            return False

    def _stop_replay(self) -> None:
        try:
            self._replay_stop.set()
            self._notify("⏹ Replay stop requested", 1500)
        except Exception:
            pass

    def _get_selected_packet_id(self) -> Optional[int]:
        # Prefer reassembled selection, else raw selection.
        try:
            rows = self.table.selectionModel().selectedRows()
            if rows:
                rec = self.table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole) or {}
                decoded = rec.get("decoded") or {}
                if decoded.get("packet_id") is not None:
                    return int(decoded.get("packet_id"))
        except Exception:
            pass

        try:
            rows = self.raw_table.selectionModel().selectedRows()
            if rows:
                rec = self.raw_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole) or {}
                decoded = rec.get("decoded") or {}
                if decoded.get("packet_id") is not None:
                    return int(decoded.get("packet_id"))
        except Exception:
            pass

        return None

    def _replay_selected_packet(self) -> None:
        """Replay the selected BAP packet's raw frames to the CAN bus."""
        pkt = self._get_selected_packet_id()
        if pkt is None:
            self._notify("Replay: no packet selected", 2500)
            return

        packet_raw = self._get_packet_raw_records(pkt)
        if not packet_raw:
            self._notify(f"Replay: no raw frames found for pkt={pkt}", 2500)
            return

        # Validate that we have a connected bus before starting replay thread
        bus_mgr = self._get_parent_bus_manager()
        if not bus_mgr:
            self._notify("Replay: bus manager not available", 3000)
            return
        
        connected = self._get_connected_buses()
        if not connected:
            self._notify("Replay: no connected CAN bus", 3000)
            return

        # Choose target bus: prefer original source if connected, else first connected.
        first_src = str((packet_raw[0].get("msg") or {}).get("source") or "")
        target_bus = first_src if first_src in connected else connected[0]

        respect_timing = bool(self.replay_timing_check.isChecked())

        # Avoid running multiple replays concurrently.
        if self._replay_thread and self._replay_thread.is_alive():
            self._notify("Replay already running (press Stop Replay first)", 2500)
            return

        self._replay_stop.clear()
        self._replay_thread = threading.Thread(
            target=self._replay_packet_thread,
            args=(pkt, packet_raw, target_bus, respect_timing),
            daemon=True,
        )
        self._replay_thread.start()
        self._notify(f"▶ Replaying pkt={pkt} to {target_bus} ({'timing' if respect_timing else 'fast'})", 3000)

    def _replay_packet_thread(self, pkt: int, packet_raw: List[Dict[str, Any]], target_bus: str, respect_timing: bool) -> None:
        # Compute inter-frame delays from captured timestamps.
        last_ts: Optional[float] = None
        sent = 0
        failed = 0

        for rec in packet_raw:
            if self._replay_stop.is_set():
                break

            msg_rec = rec.get("msg") or {}
            try:
                msg = self._record_to_msg(msg_rec)
            except Exception:
                failed += 1
                continue

            ts = float(msg_rec.get("timestamp") or 0.0)
            if respect_timing and last_ts is not None and ts > 0 and last_ts > 0:
                dt = ts - last_ts
                # Clamp to keep replay usable/safe.
                if dt < 0:
                    dt = 0.0
                dt = min(dt, 0.25)  # max 250ms gap
                if dt > 0:
                    # Sleep in small slices to remain stoppable.
                    remaining = dt
                    while remaining > 0 and not self._replay_stop.is_set():
                        sl = min(remaining, 0.02)
                        time.sleep(sl)
                        remaining -= sl

            ok = self._send_frame(target_bus, msg)
            if ok:
                sent += 1
            else:
                failed += 1

            if ts > 0:
                last_ts = ts

        # Notify on completion (UI thread not required for show_notification)
        if self._replay_stop.is_set():
            self._notify(f"⏹ Replay stopped: pkt={pkt} sent={sent} failed={failed}", 3500)
        else:
            self._notify(f"✅ Replay done: pkt={pkt} sent={sent} failed={failed}", 3500)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        header = QGroupBox("BAP Detection")
        header_layout = QVBoxLayout()

        # Row 1: primary controls
        row1 = QHBoxLayout()

        row1.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Conservative (high confidence)", BAPDetectionMode.CONSERVATIVE.value)
        self.mode_combo.addItem("Aggressive (include single-frame)", BAPDetectionMode.AGGRESSIVE.value)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        row1.addWidget(self.mode_combo)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setToolTip("Pause BAP analysis (drops incoming frames while paused)")
        self.pause_btn.clicked.connect(self._toggle_analysis_pause)
        row1.addWidget(self.pause_btn)

        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        row1.addWidget(self.auto_scroll_check)

        row1.addStretch()

        self.export_btn = QPushButton("Export...")
        self.export_btn.clicked.connect(self._export_capture)
        row1.addWidget(self.export_btn)

        self.import_btn = QPushButton("Import...")
        self.import_btn.clicked.connect(self._import_capture)
        row1.addWidget(self.import_btn)

        self.stats_label = QLabel("Frames: 0 | BAP messages: 0 | Active streams: 0")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self.stats_label)

        # Filters
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Filter CAN ID:"))
        self.filter_canid = QLineEdit()
        self.filter_canid.setPlaceholderText("e.g. 0x63B or 0x17333310")
        self.filter_canid.setMaximumWidth(140)
        row2.addWidget(self.filter_canid)

        row2.addWidget(QLabel("LSG:"))
        self.filter_lsg = QLineEdit()
        self.filter_lsg.setPlaceholderText("e.g. 43 or 0x33")
        self.filter_lsg.setMaximumWidth(80)
        row2.addWidget(self.filter_lsg)

        row2.addWidget(QLabel("Source:"))
        self.filter_source = QComboBox()
        self.filter_source.addItem("Any", "")
        self.filter_source.setMaximumWidth(120)
        row2.addWidget(self.filter_source)

        refilter_btn = QPushButton("Re-filter")
        refilter_btn.clicked.connect(self._refilter_tables)
        row2.addWidget(refilter_btn)

        row2.addStretch()

        header_layout.addLayout(row1)
        header_layout.addLayout(row2)

        header.setLayout(header_layout)
        layout.addWidget(header)

        # Tabs: Reassembled Messages + Raw Frames
        tabs = QTabWidget()
        tabs.currentChanged.connect(self._on_bap_tab_changed)

        tab_messages = QWidget()
        tab_messages_layout = QVBoxLayout(tab_messages)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Bus", "CAN ID", "Channel", "Endpoint", "Pkt", "LSG", "FCT", "Opcode", "Len", "Payload (hex)"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)

        font = QFont("Courier New", 12)
        self.table.setFont(font)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.resizeSection(0, 100)  # time
        hdr.resizeSection(1, 70)   # bus
        hdr.resizeSection(2, 90)   # id
        hdr.resizeSection(3, 130)  # channel
        hdr.resizeSection(4, 75)   # endpoint
        hdr.resizeSection(5, 60)   # pkt
        hdr.resizeSection(6, 60)   # lsg
        hdr.resizeSection(7, 60)   # fct
        hdr.resizeSection(8, 70)   # opcode
        hdr.resizeSection(9, 50)   # len
        hdr.resizeSection(10, 420)  # payload
        hdr.setStretchLastSection(True)

        tab_raw = QWidget()
        tab_raw_layout = QVBoxLayout(tab_raw)

        self.raw_table = QTableWidget()
        self.raw_table.setColumnCount(12)
        self.raw_table.setHorizontalHeaderLabels(
            ["Time", "Bus", "CAN ID", "Channel", "Endpoint", "Pkt", "Type", "MF ch", "Len", "Done", "Header", "Raw data"]
        )
        self.raw_table.verticalHeader().setVisible(False)
        self.raw_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Needed to highlight multiple frames belonging to the same packet.
        self.raw_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.raw_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.raw_table.itemSelectionChanged.connect(self._on_raw_row_selected)
        self.raw_table.setFont(font)

        raw_hdr = self.raw_table.horizontalHeader()
        raw_hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        raw_hdr.resizeSection(0, 100)
        raw_hdr.resizeSection(1, 70)
        raw_hdr.resizeSection(2, 90)
        raw_hdr.resizeSection(3, 130)  # channel
        raw_hdr.resizeSection(4, 75)   # endpoint
        raw_hdr.resizeSection(5, 60)   # pkt
        raw_hdr.resizeSection(6, 70)   # type
        raw_hdr.resizeSection(7, 60)   # mfch
        raw_hdr.resizeSection(8, 60)   # len
        raw_hdr.resizeSection(9, 70)   # done
        raw_hdr.resizeSection(10, 160)  # header
        raw_hdr.resizeSection(11, 360)  # raw
        raw_hdr.setStretchLastSection(True)

        # Reassembled tab: Details below table (vertical splitter)
        details_group = QGroupBox("Details")
        details_group.setMinimumHeight(80)
        details_layout = QVBoxLayout()
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(60)
        self.details_text.setFont(QFont("Courier New", 11))
        details_layout.addWidget(self.details_text)
        details_group.setLayout(details_layout)

        split_msgs = QSplitter(Qt.Orientation.Vertical)
        split_msgs.addWidget(self.table)
        split_msgs.addWidget(details_group)
        split_msgs.setStretchFactor(0, 8)
        split_msgs.setStretchFactor(1, 2)
        split_msgs.setChildrenCollapsible(True)
        split_msgs.setSizes([520, 140])  # initial: table bigger, details smaller
        self._split_msgs = split_msgs
        split_msgs.splitterMoved.connect(lambda *_: self._update_split_ratio_from_widget("msgs"))

        tab_messages_layout.addWidget(split_msgs)

        btns = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        btns.addWidget(clear_btn)

        copy_btn = QPushButton("Copy Payload")
        copy_btn.clicked.connect(self._copy_selected_payload)
        btns.addWidget(copy_btn)

        # Clear/Copy | Replay controls | Hide/Show
        btns.addWidget(self._vline())

        self.replay_timing_check = QCheckBox("Replay timing")
        self.replay_timing_check.setToolTip("If enabled, replay packet with captured inter-frame delays")
        self.replay_timing_check.setChecked(True)
        btns.addWidget(self.replay_timing_check)

        replay_btn = QPushButton("Replay Packet")
        replay_btn.setToolTip("Replay Start/Cont frames for selected packet")
        replay_btn.clicked.connect(self._replay_selected_packet)
        btns.addWidget(replay_btn)

        stop_replay_btn = QPushButton("Stop Replay")
        stop_replay_btn.clicked.connect(self._stop_replay)
        btns.addWidget(stop_replay_btn)

        btns.addWidget(self._vline())

        self._hide_details_btn_msgs = QPushButton("Hide Details")
        self._hide_details_btn_msgs.clicked.connect(lambda *_: self._toggle_details_visible("msgs"))
        btns.addWidget(self._hide_details_btn_msgs)

        btns.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)

        tab_messages_layout.addLayout(btns)
        self._sync_details_toggle_state("msgs")

        # Raw tab: Details below table (vertical splitter)
        details_group_raw = QGroupBox("Details")
        details_group_raw.setMinimumHeight(80)
        details_layout_raw = QVBoxLayout()
        self.raw_details_text = QTextEdit()
        self.raw_details_text.setReadOnly(True)
        self.raw_details_text.setMinimumHeight(60)
        self.raw_details_text.setFont(QFont("Courier New", 11))
        details_layout_raw.addWidget(self.raw_details_text)
        details_group_raw.setLayout(details_layout_raw)

        btns_raw = QHBoxLayout()
        clear_raw_btn = QPushButton("Clear")
        clear_raw_btn.clicked.connect(self._clear)
        btns_raw.addWidget(clear_raw_btn)

        btns_raw.addWidget(self._vline())

        self._hide_details_btn_raw = QPushButton("Hide Details")
        self._hide_details_btn_raw.clicked.connect(lambda *_: self._toggle_details_visible("raw"))
        btns_raw.addWidget(self._hide_details_btn_raw)

        btns_raw.addStretch()
        close_raw_btn = QPushButton("Close")
        close_raw_btn.clicked.connect(self.accept)
        btns_raw.addWidget(close_raw_btn)

        split_raw = QSplitter(Qt.Orientation.Vertical)
        split_raw.addWidget(self.raw_table)
        split_raw.addWidget(details_group_raw)
        split_raw.setStretchFactor(0, 8)
        split_raw.setStretchFactor(1, 2)
        split_raw.setChildrenCollapsible(True)
        split_raw.setSizes([520, 140])
        self._split_raw = split_raw
        split_raw.splitterMoved.connect(lambda *_: self._update_split_ratio_from_widget("raw"))

        tab_raw_layout.addWidget(split_raw)
        tab_raw_layout.addLayout(btns_raw)
        self._sync_details_toggle_state("raw")

        tabs.addTab(tab_messages, "Reassembled Messages")
        tabs.addTab(tab_raw, "Raw Frames")

        layout.addWidget(tabs)
        self.setLayout(layout)

    def _on_mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        try:
            self.worker.set_mode(str(mode))
        except Exception:
            pass

    def add_message(self, msg: CANMessage) -> None:
        # Called from main UI thread (UIUpdateHandler), keep it lightweight.
        if self._analysis_paused:
            self._dropped_while_paused += 1
            return
        src = getattr(msg, "source", "") or ""
        if src and src not in self._known_sources:
            self._known_sources.add(src)
            # Add source to filter combo (best effort)
            try:
                self.filter_source.addItem(src, src)
            except Exception:
                pass
        self._total_frames_seen += 1
        # Submit to worker; decoding happens off the UI thread.
        self.worker.submit(msg)

    def _toggle_analysis_pause(self) -> None:
        self._analysis_paused = not self._analysis_paused
        if self._analysis_paused:
            # Drop any queued items to avoid lag bursts when resuming.
            try:
                dropped = 0
                # Drain worker queue best-effort.
                while True:
                    self.worker.in_q.get_nowait()
                    dropped += 1
            except Exception:
                pass
            self._dropped_while_paused += dropped
            self.pause_btn.setText("Resume")
            self._notify("⏸ BAP analysis paused (incoming frames dropped)", 2500)
        else:
            self.pause_btn.setText("Pause")
            self._notify("▶ BAP analysis resumed", 1500)

    def _process_queue(self) -> None:
        # Drain decoded output from worker and update UI in bounded batches.
        # This keeps timestamps correct, while preventing UI lag from blocking decode.
        table_scroll = self._capture_scroll_state(self.table)
        raw_scroll = self._capture_scroll_state(self.raw_table)

        batch = []
        for _ in range(300):
            try:
                batch.append(self.worker.out_q.get_nowait())
            except Exception:
                break

        if not batch:
            self._update_stats()
            return

        self.table.setUpdatesEnabled(False)
        self.raw_table.setUpdatesEnabled(False)
        try:
            for item in batch:
                msg = item.get("msg")
                decoded = item.get("decoded") or {}
                if not msg or not decoded:
                    continue

                # UI lag metric: how old is the message when we render it?
                try:
                    ts = float(getattr(msg, "timestamp", 0.0) or 0.0)
                    if ts > 0:
                        self._last_lag_ms = max(0, int((time.time() - ts) * 1000))
                except Exception:
                    pass

                if decoded.get("is_bap_candidate"):
                    rec = {"msg": self._msg_to_record(msg), "decoded": decoded}
                    self._raw_records.append(rec)
                    # Index by packet for fast Details lookups
                    try:
                        pid = decoded.get("packet_id")
                        if pid is not None:
                            pid_int = int(pid)
                            self._raw_records_by_packet.setdefault(pid_int, []).append(rec)
                    except Exception:
                        pass
                    if self._passes_filters(msg, decoded):
                        self._append_raw_row(msg, decoded, record=rec)

                if decoded.get("success") and decoded.get("is_complete"):
                    rec = {"msg": self._msg_to_record(msg), "decoded": decoded}
                    self._decoded_records.append(rec)
                    if self._passes_filters(msg, decoded):
                        self._append_row(msg, decoded, record=rec)
        finally:
            self.table.setUpdatesEnabled(True)
            self.raw_table.setUpdatesEnabled(True)

        self._update_stats()

        # One-time column autosize after first data arrives (sampled; avoids expensive full scans).
        if not self._did_autosize_cols_msgs and self.table.rowCount() > 0:
            self._autosize_columns_sampled(self.table, stretch_col=self.table.columnCount() - 1)
            self._did_autosize_cols_msgs = True
        if not self._did_autosize_cols_raw and self.raw_table.rowCount() > 0:
            self._autosize_columns_sampled(self.raw_table, stretch_col=self.raw_table.columnCount() - 1)
            self._did_autosize_cols_raw = True

        if self.auto_scroll_check.isChecked():
            self._apply_scroll_state(self.table, table_scroll, force_bottom=table_scroll.get("at_bottom", False))
            self._apply_scroll_state(self.raw_table, raw_scroll, force_bottom=raw_scroll.get("at_bottom", False))
        else:
            self._apply_scroll_state(self.table, table_scroll, force_bottom=False)
            self._apply_scroll_state(self.raw_table, raw_scroll, force_bottom=False)

        self._cap_tables(max_rows=5000)

    def _autosize_columns_sampled(self, table: QTableWidget, stretch_col: Optional[int] = None, max_sample_rows: int = 120) -> None:
        """
        Set initial column widths based on max(title, sampled content).
        Avoids QHeaderView.ResizeToContents on huge tables (can be very slow).
        """
        try:
            fm = QFontMetrics(table.font())
            cols = table.columnCount()
            rows = table.rowCount()
            if cols <= 0:
                return

            sample = min(rows, int(max_sample_rows))
            # Sample evenly from the first N rows to keep cost bounded.
            step = max(1, rows // max(1, sample))
            sampled_rows = list(range(0, rows, step))[:sample]

            pad = 22  # cell padding + sort indicator slack

            for c in range(cols):
                if stretch_col is not None and c == int(stretch_col):
                    continue
                header_text = ""
                try:
                    header_item = table.horizontalHeaderItem(c)
                    header_text = header_item.text() if header_item else ""
                except Exception:
                    header_text = ""

                max_w = fm.horizontalAdvance(header_text) + pad
                for r in sampled_rows:
                    it = table.item(r, c)
                    if not it:
                        continue
                    txt = it.text() or ""
                    w = fm.horizontalAdvance(txt) + pad
                    if w > max_w:
                        max_w = w

                # Clamp very wide columns (payload/raw should be stretch anyway).
                max_w = min(max_w, 420)
                table.setColumnWidth(c, max_w)

            if stretch_col is not None:
                table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            return

    def closeEvent(self, event):
        try:
            self.worker.stop()
        except Exception:
            pass
        super().closeEvent(event)

    @staticmethod
    def _capture_scroll_state(table: QTableWidget) -> Dict[str, Any]:
        try:
            sb = table.verticalScrollBar()
            value = int(sb.value())
            maximum = int(sb.maximum())
            # treat "near bottom" as bottom to avoid jitter when user wants live tail
            at_bottom = (maximum - value) <= 2
            return {"value": value, "at_bottom": at_bottom}
        except Exception:
            return {"value": 0, "at_bottom": True}

    @staticmethod
    def _apply_scroll_state(table: QTableWidget, state: Dict[str, Any], force_bottom: bool) -> None:
        try:
            if force_bottom:
                table.scrollToBottom()
                return
            sb = table.verticalScrollBar()
            sb.setValue(int(state.get("value", 0)))
        except Exception:
            pass

    def _cap_tables(self, max_rows: int = 5000) -> None:
        for table in (self.table, self.raw_table):
            try:
                extra = table.rowCount() - max_rows
                if extra > 0:
                    for _ in range(extra):
                        table.removeRow(0)
            except Exception:
                continue

    def _passes_filters(self, msg: CANMessage, decoded: Dict[str, Any]) -> bool:
        # CAN ID filter
        canid_filter = self._parse_int(self.filter_canid.text())
        if canid_filter is not None and int(getattr(msg, "can_id", 0)) != int(canid_filter):
            return False

        # Source filter
        src_filter = (self.filter_source.currentData() or "").strip()
        if src_filter:
            src = (getattr(msg, "source", "") or "").strip()
            if src != src_filter:
                return False

        # LSG filter (PQ header lsg or MQB id lsg)
        lsg_filter = self._parse_int(self.filter_lsg.text())
        if lsg_filter is not None:
            lsg_val: Optional[int] = None
            hdr = decoded.get("header") or {}
            if "lsg" in hdr:
                try:
                    lsg_val = int(hdr.get("lsg"))
                except Exception:
                    lsg_val = None
            if lsg_val is None:
                mqb = decoded.get("mqb") or {}
                if "lsg" in mqb:
                    try:
                        lsg_val = int(mqb.get("lsg"))
                    except Exception:
                        lsg_val = None
            if lsg_val is None or int(lsg_val) != int(lsg_filter):
                return False

        return True

    @staticmethod
    def _compute_channel_and_endpoint(decoded: Dict[str, Any]) -> tuple[str, str]:
        """
        Group key based on origin/destination CAN ID patterns:
          - MQB: group by (base_id, lsg) from CAN ID; endpoint derived from subsystem (ASG<0x10, FSG>=0x10)
          - PQ: group by LSG from BAP header; endpoint unknown
        """
        mqb = decoded.get("mqb") or {}
        if isinstance(mqb, dict) and "base_id" in mqb and "lsg" in mqb:
            try:
                base_id = int(mqb.get("base_id"))
                lsg = int(mqb.get("lsg"))
                subsystem = int(mqb.get("subsystem", 0))
                endpoint = "FSG" if subsystem >= 0x10 else "ASG"
                # Keep stable short string for sorting/grouping
                return (f"0x{base_id:04X}/0x{lsg:02X}", endpoint)
            except Exception:
                pass

        hdr = decoded.get("header") or {}
        if isinstance(hdr, dict) and "lsg" in hdr:
            try:
                lsg = int(hdr.get("lsg"))
                return (f"LSG {lsg}", "")
            except Exception:
                pass

        return ("", "")

    @staticmethod
    def _format_hex_multiline(hex_str: str, bytes_per_line: int = 16) -> str:
        """
        Render hex payload as spaced bytes, wrapped per N bytes/line.
        """
        s = (hex_str or "").strip().replace(" ", "")
        if not s:
            return ""
        # Ensure even length
        if len(s) % 2 == 1:
            s = "0" + s
        bpl = max(4, int(bytes_per_line))
        chars_per_line = bpl * 2
        lines = []
        for i in range(0, len(s), chars_per_line):
            chunk = s[i : i + chars_per_line]
            lines.append(" ".join(chunk[j : j + 2] for j in range(0, len(chunk), 2)))
        return "\n".join(lines)

    def _get_packet_raw_records(self, packet_id: Optional[int]) -> List[Dict[str, Any]]:
        if packet_id is None:
            return []
        try:
            pid = int(packet_id)
        except Exception:
            return []
        hits = list(self._raw_records_by_packet.get(pid, []) or [])

        # Sort by timestamp when available; stable fallback
        def keyf(r: Dict[str, Any]) -> float:
            try:
                return float((r.get("msg") or {}).get("timestamp") or 0.0)
            except Exception:
                return 0.0

        hits.sort(key=keyf)
        return hits

    @staticmethod
    def _infer_frame_type_from_bytes(data: bytes) -> str:
        if not data:
            return ""
        b0 = data[0]
        if (b0 & 0xC0) == 0x80:
            return "Start"
        if (b0 & 0xC0) == 0xC0:
            return "Cont"
        return "Other"

    def _explain_packet_link(self, reassembled_decoded: Dict[str, Any], packet_raw: List[Dict[str, Any]]) -> str:
        """
        Build a human-friendly explanation of how Start/Cont frames relate to the reassembled payload.
        This follows our current multi-frame slicing rules (best-effort for MQB).
        """
        if not packet_raw:
            return ""

        lines: List[str] = []
        # Build a compact table-like view (monospace).
        lines.append("idx  time         can_id        type   mfch  bytes  payload_range   chunk_head")

        cursor = 0  # payload write cursor
        total_len = reassembled_decoded.get("total_len")
        try:
            total_len_int = int(total_len) if total_len is not None else None
        except Exception:
            total_len_int = None

        for idx, rec in enumerate(packet_raw):
            msg_rec = rec.get("msg") or {}
            data_hex = str(msg_rec.get("data_hex") or "")
            data = bytes.fromhex(data_hex) if data_hex else b""
            ftype = self._infer_frame_type_from_bytes(data)

            ts = float(msg_rec.get("timestamp") or 0.0)
            time_str = ""
            if ts > 0:
                try:
                    dt = datetime.fromtimestamp(ts)
                    time_str = dt.strftime("%H:%M:%S.%f")[:-3]
                except Exception:
                    time_str = ""

            can_id = int(msg_rec.get("can_id") or 0)
            mfch = (rec.get("decoded") or {}).get("mf_channel")

            chunk = b""
            if ftype == "Start":
                chunk = data[4:] if len(data) >= 4 else b""
            elif ftype == "Cont":
                chunk = data[1:] if len(data) >= 1 else b""
            else:
                chunk = b""

            start = cursor
            end = cursor + len(chunk)
            cursor = end

            chunk_hex = chunk.hex()
            # Show only head to keep details readable; full payload is shown above.
            head = chunk_hex[:32] + ("..." if len(chunk_hex) > 32 else "")
            rng = f"{start}:{end}"
            lines.append(
                f"{idx:>3}  {time_str:<11}  0x{can_id:08X}  {ftype:<5}  {str(mfch):<4}  "
                f"{len(chunk):>5}  {rng:<12}  {head}"
            )

        if total_len_int is not None:
            ok = "OK" if cursor == total_len_int else f"mismatch (got {cursor}, expected {total_len_int})"
            lines.append(f"total_bytes={cursor} -> {ok}")
        else:
            lines.append(f"total_bytes={cursor}")

        return "\n".join(lines)

    def _highlight_packet_in_raw(self, packet_id: Optional[int]) -> None:
        """
        Highlight all raw frames that belong to the same reassembled packet.

        Implementation note: avoid per-cell background painting (very slow on large tables).
        Instead, select all matching rows using the selection model.
        """
        if packet_id is None:
            packet_id_int = None
        else:
            try:
                packet_id_int = int(packet_id)
            except Exception:
                packet_id_int = None

        # Avoid redundant work
        if packet_id_int == self._highlighted_packet_id:
            return
        self._highlighted_packet_id = packet_id_int

        sel = self.raw_table.selectionModel()
        if not sel:
            return

        self._suppress_selection_handlers = True
        try:
            sel.clearSelection()
            if packet_id_int is None:
                return

            # Select all rows that match the packet id.
            # Only need one index per row to select the whole row.
            selection = QItemSelection()
            for r in range(self.raw_table.rowCount()):
                try:
                    rec = self.raw_table.item(r, 0).data(Qt.ItemDataRole.UserRole) or {}
                    decoded = rec.get("decoded") or {}
                    if int(decoded.get("packet_id") or 0) != packet_id_int:
                        continue
                    idx0 = self.raw_table.model().index(r, 0)
                    idx_last = self.raw_table.model().index(r, self.raw_table.columnCount() - 1)
                    selection.select(idx0, idx_last)
                except Exception:
                    continue

            if not selection.isEmpty():
                sel.select(selection, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        finally:
            self._suppress_selection_handlers = False

    def _refilter_tables(self) -> None:
        # Rebuild displayed rows from cached decoded lists (keeps UI consistent after filter edits).
        try:
            self.table.setRowCount(0)
            self.raw_table.setRowCount(0)
        except Exception:
            return

        for rec in self._decoded_records:
            decoded = rec.get("decoded") or {}
            msg_rec = rec.get("msg") or {}
            try:
                fake_msg = self._record_to_msg(msg_rec)
            except Exception:
                continue
            if self._passes_filters(fake_msg, decoded):
                self._append_row(fake_msg, decoded, record=rec)

        for rec in self._raw_records:
            decoded = rec.get("decoded") or {}
            msg_rec = rec.get("msg") or {}
            try:
                fake_msg = self._record_to_msg(msg_rec)
            except Exception:
                continue
            if self._passes_filters(fake_msg, decoded):
                self._append_raw_row(fake_msg, decoded, record=rec)

        # Refresh column widths based on current view.
        self._autosize_columns_sampled(self.table, stretch_col=self.table.columnCount() - 1)
        self._autosize_columns_sampled(self.raw_table, stretch_col=self.raw_table.columnCount() - 1)

    def _append_row(self, msg: CANMessage, decoded: Dict[str, Any], record: Optional[Dict[str, Any]] = None) -> None:
        # Timestamp
        ts = float(getattr(msg, "timestamp", 0.0) or 0.0)
        time_str = ""
        if ts > 0:
            dt = datetime.fromtimestamp(ts)
            time_str = dt.strftime("%H:%M:%S.%f")[:-3]

        hdr = decoded.get("header") or {}
        mqb = decoded.get("mqb") or {}

        if hdr:
            lsg = str(hdr.get("lsg"))
            fct = str(hdr.get("fct"))
            opcode = str(hdr.get("opcode"))
        else:
            # MQB: LSG comes from CAN ID.
            lsg = f"0x{mqb.get('lsg', 0):02X}" if mqb else ""
            fct = ""
            opcode = ""

        total_len = decoded.get("total_len")
        packet_id = decoded.get("packet_id")
        channel, endpoint = self._compute_channel_and_endpoint(decoded)
        payload_hex = decoded.get("payload") or ""
        if len(payload_hex) > 120:
            payload_hex = payload_hex[:120] + "..."

        row = self.table.rowCount()
        self.table.insertRow(row)

        items = [
            QTableWidgetItem(time_str),
            QTableWidgetItem(getattr(msg, "source", "")),
            QTableWidgetItem(f"0x{msg.can_id:X}"),
            QTableWidgetItem(channel),
            QTableWidgetItem(endpoint),
            QTableWidgetItem("" if packet_id is None else str(packet_id)),
            QTableWidgetItem(lsg),
            QTableWidgetItem(fct),
            QTableWidgetItem(opcode),
            QTableWidgetItem(str(total_len if total_len is not None else "")),
            QTableWidgetItem(payload_hex),
        ]

        for c, it in enumerate(items):
            if c in (4, 5, 6, 7, 8, 9):
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, c, it)

        # Keep record in UserRole for detail/copy/export.
        self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, record or {"msg": self._msg_to_record(msg), "decoded": decoded})

    def _on_row_selected(self) -> None:
        if self._suppress_selection_handlers:
            return
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.details_text.setText("")
            self._highlight_packet_in_raw(None)
            return
        row = rows[0].row()
        rec = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) or {}
        self.details_text.setText(self._format_details_record(rec))
        try:
            decoded = rec.get("decoded") or {}
            pkt = decoded.get("packet_id")
            self._highlight_packet_in_raw(pkt if pkt is not None else None)
        except Exception:
            self._highlight_packet_in_raw(None)

    def _on_raw_row_selected(self) -> None:
        if self._suppress_selection_handlers:
            return
        rows = self.raw_table.selectionModel().selectedRows()
        if not rows:
            self.raw_details_text.setText("")
            return
        row = rows[0].row()
        rec = self.raw_table.item(row, 0).data(Qt.ItemDataRole.UserRole) or {}
        self.raw_details_text.setText(self._format_raw_details_record(rec))
        try:
            decoded = rec.get("decoded") or {}
            pkt = decoded.get("packet_id")
            self._highlight_packet_in_raw(pkt if pkt is not None else None)
        except Exception:
            pass

    def _format_details_record(self, rec: Dict[str, Any]) -> str:
        # Cache by packet_id (and CAN ID) to keep click snappy on huge traces.
        try:
            decoded0 = rec.get("decoded") or {}
            cache_key = ("reassembled", int(decoded0.get("packet_id") or 0), int(decoded0.get("raw_id") or 0), int(decoded0.get("total_len") or 0))
            with _details_cache_lock:
                cached = self._details_cache.get(cache_key)
            if cached:
                return cached
        except Exception:
            cache_key = None

        msg_rec = rec.get("msg") or {}
        decoded = rec.get("decoded") or rec  # backwards-compatible if old shape
        lines = []
        ts = float(msg_rec.get("timestamp") or 0.0)
        src = str(msg_rec.get("source") or "")
        can_id = int(decoded.get("raw_id", 0) or 0)
        ext = bool(decoded.get("is_extended"))
        mfch = decoded.get("mf_channel")
        total_len = decoded.get("total_len")
        pkt = decoded.get("packet_id")

        channel, endpoint = self._compute_channel_and_endpoint(decoded)

        lines.append("== BAP Message (Reassembled) ==")
        if ts > 0:
            dt = datetime.fromtimestamp(ts)
            lines.append(f"Time     : {dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        if src:
            lines.append(f"Source   : {src}")
        lines.append(f"CAN ID   : 0x{can_id:X} (extended={ext})")
        if channel:
            lines.append(f"Channel  : {channel} {endpoint}".rstrip())
        if pkt is not None:
            lines.append(f"Packet   : {pkt}")
        lines.append(f"MF ch    : {mfch} | Len: {total_len}")

        if decoded.get("header"):
            h = decoded["header"]
            lines.append(f"Header   : opcode={h.get('opcode')} lsg={h.get('lsg')} fct={h.get('fct')}")
        if decoded.get("mqb"):
            m = decoded["mqb"]
            lines.append(f"MQB ID   : base=0x{m.get('base_id', 0):04X} lsg=0x{m.get('lsg', 0):02X} subsystem=0x{m.get('subsystem', 0):02X}")

        payload = str(decoded.get("payload") or "")
        lines.append("")
        lines.append("-- Payload (hex) --")
        lines.append(self._format_hex_multiline(payload, bytes_per_line=16) or "(empty)")

        # If multi-frame, show how frames link to payload.
        pkt = decoded.get("packet_id")
        packet_raw = self._get_packet_raw_records(pkt if pkt is not None else None)
        if packet_raw:
            lines.append("")
            lines.append("-- Frame Linkage --")
            lines.append(self._explain_packet_link(decoded, packet_raw))
        out = "\n".join(lines)
        try:
            if cache_key is not None:
                with _details_cache_lock:
                    self._details_cache[cache_key] = out
        except Exception:
            pass
        return out

    def _format_raw_details_record(self, rec: Dict[str, Any]) -> str:
        try:
            decoded0 = rec.get("decoded") or {}
            cache_key = ("raw", int(decoded0.get("packet_id") or 0), int(decoded0.get("raw_id") or 0), int(decoded0.get("total_len") or 0), str(decoded0.get("raw_data") or "")[:32])
            with _details_cache_lock:
                cached = self._details_cache.get(cache_key)
            if cached:
                return cached
        except Exception:
            cache_key = None

        msg_rec = rec.get("msg") or {}
        decoded = rec.get("decoded") or rec  # backwards-compatible if old shape
        lines = []
        ts = float(msg_rec.get("timestamp") or 0.0)
        src = str(msg_rec.get("source") or "")
        can_id = int(decoded.get("raw_id", 0) or 0)
        ext = bool(decoded.get("is_extended"))
        mfch = decoded.get("mf_channel")
        total_len = decoded.get("total_len")
        pkt = decoded.get("packet_id")

        channel, endpoint = self._compute_channel_and_endpoint(decoded)

        lines.append("== BAP Frame (Raw) ==")
        if ts > 0:
            dt = datetime.fromtimestamp(ts)
            lines.append(f"Time     : {dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        if src:
            lines.append(f"Source   : {src}")
        lines.append(f"CAN ID   : 0x{can_id:X} (extended={ext})")
        if channel:
            lines.append(f"Channel  : {channel} {endpoint}".rstrip())
        if pkt is not None:
            lines.append(f"Packet   : {pkt}")
        lines.append(f"MF ch    : {mfch} | Len: {total_len}")

        if decoded.get("error"):
            lines.append(f"Error    : {decoded.get('error')}")
        if decoded.get("header"):
            h = decoded["header"]
            lines.append(f"Header   : opcode={h.get('opcode')} lsg={h.get('lsg')} fct={h.get('fct')}")
        if decoded.get("mqb"):
            m = decoded["mqb"]
            lines.append(
                f"MQB ID   : base=0x{m.get('base_id', 0):04X} lsg=0x{m.get('lsg', 0):02X} subsystem=0x{m.get('subsystem', 0):02X}"
            )
        lines.append("")
        lines.append("-- Raw CAN data (hex) --")
        lines.append(self._format_hex_multiline(str(decoded.get("raw_data") or ""), bytes_per_line=16) or "(empty)")

        pkt = decoded.get("packet_id")
        packet_raw = self._get_packet_raw_records(pkt if pkt is not None else None)
        if packet_raw:
            lines.append("")
            # Use this frame's packet as linkage view
            lines.append("-- Frame Linkage --")
            lines.append(self._explain_packet_link(decoded, packet_raw))
        out = "\n".join(lines)
        try:
            if cache_key is not None:
                with _details_cache_lock:
                    self._details_cache[cache_key] = out
        except Exception:
            pass
        return out

    def _copy_selected_payload(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        rec = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) or {}
        decoded = rec.get("decoded") or rec
        payload = str(decoded.get("payload") or "")
        if not payload:
            return
        try:
            from PyQt6.QtWidgets import QApplication
            cb = QApplication.instance().clipboard() if QApplication.instance() else None
            if cb:
                cb.setText(payload)
        except Exception:
            pass

    def _export_capture(self) -> None:
        """
        Export capture to JSON (reassembled + raw), including mode and filters.
        """
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export VAG BAP Capture",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not filename:
            return

        try:
            state = self._get_state_for_export()
            payload = {
                "type": "vag_bap_capture",
                "version": 1,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "state": state,
                "stats": {
                    "frames_seen": int(self._total_frames_seen),
                    "bap_messages": int(len(self._decoded_records)),
                    "raw_frames": int(len(self._raw_records)),
                },
                # Always export the full capture (not just current selection/view).
                "reassembled": self._decoded_records,
                "raw": self._raw_records,
            }

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=True, sort_keys=False)
            self._notify(f"💾 BAP capture saved: {filename}", 3500)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")

    def _import_capture(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import VAG BAP Capture",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                payload = json.load(f)

            if not isinstance(payload, dict) or payload.get("type") != "vag_bap_capture":
                raise ValueError("Not a VAG BAP capture file")

            version = int(payload.get("version") or 0)
            if version != 1:
                raise ValueError(f"Unsupported capture version: {version}")

            reassembled = payload.get("reassembled") or []
            raw = payload.get("raw") or []
            if not isinstance(reassembled, list) or not isinstance(raw, list):
                raise ValueError("Invalid capture structure")

            # Reset state + UI
            self._clear()

            # Apply saved state (mode + filters)
            state = payload.get("state") or {}
            if isinstance(state, dict):
                self._apply_state_from_import(state)

            # Restore known sources in filter combo
            sources = set()
            for rec in reassembled + raw:
                if isinstance(rec, dict):
                    msg_rec = rec.get("msg") or {}
                    src = str(msg_rec.get("source") or "")
                    if src:
                        sources.add(src)
            for src in sorted(sources):
                if src not in self._known_sources:
                    self._known_sources.add(src)
                    self.filter_source.addItem(src, src)

            # Restore records
            self._decoded_records = [r for r in reassembled if isinstance(r, dict)]
            self._raw_records = [r for r in raw if isinstance(r, dict)]
            # Rebuild packet index for fast clicks
            self._raw_records_by_packet.clear()
            for r in self._raw_records:
                try:
                    d = r.get("decoded") or {}
                    pid = d.get("packet_id")
                    if pid is None:
                        continue
                    self._raw_records_by_packet.setdefault(int(pid), []).append(r)
                except Exception:
                    continue
            with _details_cache_lock:
                self._details_cache.clear()

            # Rebuild tables with filters
            self._refilter_tables()
            self._notify(
                f"📂 BAP capture loaded: {len(self._decoded_records)} reassembled, {len(self._raw_records)} raw",
                4000,
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import:\n{e}")

    def _clear(self) -> None:
        self._rx_queue.clear()
        self._decoded_records.clear()
        self._raw_records.clear()
        self._raw_records_by_packet.clear()
        with _details_cache_lock:
            self._details_cache.clear()
        self._did_autosize_cols_msgs = False
        self._did_autosize_cols_raw = False
        self._total_frames_seen = 0
        try:
            self.worker.decoder.clear()
        except Exception:
            pass
        self.table.setRowCount(0)
        self.raw_table.setRowCount(0)
        self.details_text.setText("")
        self.raw_details_text.setText("")
        self._update_stats()

    def _update_stats(self) -> None:
        paused = "PAUSED" if self._analysis_paused else "RUN"
        dropped = self._dropped_while_paused
        worker_dropped = 0
        inflight = 0
        try:
            worker_dropped = int(getattr(self.worker, "dropped", 0))
            inflight = int(self.worker.in_q.qsize())
        except Exception:
            pass
        self.stats_label.setText(
            f"{paused} | Frames: {self._total_frames_seen} | "
            f"BAP: {len(self._decoded_records)} | "
            f"Streams: {self.worker.decoder.get_active_streams_count()} | "
            f"Lag: {self._last_lag_ms}ms | "
            f"Dropped: {dropped + worker_dropped} | "
            f"Inflight: {inflight}"
        )

    def _append_raw_row(self, msg: CANMessage, decoded: Dict[str, Any], record: Optional[Dict[str, Any]] = None) -> None:
        ts = float(getattr(msg, "timestamp", 0.0) or 0.0)
        time_str = ""
        if ts > 0:
            dt = datetime.fromtimestamp(ts)
            time_str = dt.strftime("%H:%M:%S.%f")[:-3]

        b0 = None
        try:
            if msg.data and len(msg.data) > 0:
                b0 = msg.data[0]
        except Exception:
            b0 = None

        frame_type = ""
        if b0 is not None:
            if (b0 & 0xC0) == 0x80:
                frame_type = "Start"
            elif (b0 & 0xC0) == 0xC0:
                frame_type = "Cont"
            else:
                frame_type = "Other"

        mfch = decoded.get("mf_channel")
        total_len = decoded.get("total_len")
        packet_id = decoded.get("packet_id")
        channel, endpoint = self._compute_channel_and_endpoint(decoded)

        done_str = ""
        if mfch is not None:
            prog = self.worker.decoder.get_stream_progress(
                can_id=int(getattr(msg, "can_id", 0)),
                is_extended=bool(getattr(msg, "is_extended", msg.can_id > 0x7FF)),
                mf_channel=int(mfch),
            )
            if prog:
                done_str = f"{prog.get('done', 0)}/{prog.get('total', 0)}"

        hdr = decoded.get("header") or {}
        mqb = decoded.get("mqb") or {}
        header_str = ""
        if hdr:
            header_str = f"op={hdr.get('opcode')} lsg={hdr.get('lsg')} fct={hdr.get('fct')}"
        elif mqb:
            header_str = f"lsg=0x{mqb.get('lsg', 0):02X}"

        raw_hex = (msg.data or b"").hex()
        if len(raw_hex) > 80:
            raw_hex = raw_hex[:80] + "..."

        row = self.raw_table.rowCount()
        self.raw_table.insertRow(row)

        items = [
            QTableWidgetItem(time_str),
            QTableWidgetItem(getattr(msg, "source", "")),
            QTableWidgetItem(f"0x{msg.can_id:X}"),
            QTableWidgetItem(channel),
            QTableWidgetItem(endpoint),
            QTableWidgetItem("" if packet_id is None else str(packet_id)),
            QTableWidgetItem(frame_type),
            QTableWidgetItem("" if mfch is None else str(mfch)),
            QTableWidgetItem("" if total_len is None else str(total_len)),
            QTableWidgetItem(done_str),
            QTableWidgetItem(header_str),
            QTableWidgetItem(raw_hex),
        ]

        for c, it in enumerate(items):
            if c in (4, 5, 6, 7, 8, 9):
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.raw_table.setItem(row, c, it)

        self.raw_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, record or {"msg": self._msg_to_record(msg), "decoded": decoded})

