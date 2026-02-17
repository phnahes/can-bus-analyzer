"""
Diff Manager - Manages message difference detection for Monitor mode

Detects and filters repeated CAN messages based on configurable criteria.
Only applies to Monitor mode display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple, List, Set
from collections import defaultdict, deque

from ..models import CANMessage
from ..logger import get_logger


class DiffConfig:
    """Configuration for Diff mode"""

    def __init__(self):
        self.enabled: bool = False
        # Operation mode:
        # - "filter": hide repeated frames (no highlight)
        # - "highlight": show all frames, highlight deltas vs snapshot
        # - "both": hide repeated frames and highlight deltas vs snapshot
        self.mode: str = "filter"
        # Filtering only applies when current rate is above this threshold.
        self.min_message_rate: float = 10.0  # msgs/s
        # Minimum number of bytes that must change (vs last displayed) to show.
        self.min_bytes_changed: int = 1
        # Sliding window for per-ID rate calculation (milliseconds).
        self.time_window_ms: int = 500
        # Heartbeat: even if no significant changes, show at least 1 frame per interval (ms).
        self.max_suppress_ms: int = 1000
        # Compare by ID+channel or just ID.
        self.compare_by_channel: bool = True
        # Which bytes to compare: "all" or comma/range indices, ex: "0-3,5,7".
        self.byte_mask: str = "all"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'enabled': self.enabled,
            'mode': self.mode,
            'min_message_rate': self.min_message_rate,
            'min_bytes_changed': self.min_bytes_changed,
            'time_window_ms': self.time_window_ms,
            'max_suppress_ms': self.max_suppress_ms,
            'compare_by_channel': self.compare_by_channel,
            'byte_mask': self.byte_mask,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DiffConfig':
        """Create from dictionary"""
        config = cls()
        config.enabled = data.get('enabled', False)
        config.mode = data.get('mode', 'filter')
        config.min_message_rate = data.get('min_message_rate', 10.0)
        config.min_bytes_changed = data.get('min_bytes_changed', 1)
        config.time_window_ms = data.get('time_window_ms', 500)
        config.max_suppress_ms = data.get('max_suppress_ms', 1000)
        config.compare_by_channel = data.get('compare_by_channel', True)
        config.byte_mask = data.get('byte_mask', 'all')
        return config


class MessageStats:
    """Statistics for a specific CAN key"""

    def __init__(self):
        self.message_count: int = 0
        self.last_timestamp: float = 0.0
        self.message_rate: float = 0.0  # msgs/s (sliding window)
        self.bytes_changed_count: int = 0
        self.total_bytes_changed: int = 0
        self.display_count: int = 0
        self.hidden_count: int = 0


@dataclass(frozen=True)
class DiffDecision:
    display: bool
    key: Tuple
    rate_mps: float
    bytes_changed_vs_last_displayed: int
    bytes_changed_vs_snapshot: int
    changed_indices_vs_snapshot: List[int]
    reason: str


class DiffManager:
    """Manages message difference detection for Monitor mode"""

    def __init__(self, config: DiffConfig):
        self.config = config
        self.logger = get_logger()

        # Store last seen/displayed/snapshot per key
        self.last_seen: Dict[Tuple, CANMessage] = {}
        self.last_displayed: Dict[Tuple, CANMessage] = {}
        self.snapshot: Dict[Tuple, CANMessage] = {}
        self._last_displayed_ts: Dict[Tuple, float] = {}

        # Sliding window timestamps for per-key rate calculation
        self._rate_windows: Dict[Tuple, Deque[float]] = defaultdict(deque)

        # Cached parsed byte mask
        self._byte_indices: Optional[Set[int]] = None
        self._byte_mask_cache_key: str = ""

        # Statistics per key
        self.stats: Dict[Tuple, MessageStats] = defaultdict(MessageStats)

        # Global statistics
        self.total_received: int = 0
        self.total_displayed: int = 0
        self.total_hidden: int = 0

        # NOTE: get_logger() returns a wrapper (CANLogger) whose .info() takes a single string.
        self.logger.info(
            f"DiffManager initialized: enabled={config.enabled}, "
            f"min_rate={config.min_message_rate}, min_bytes={config.min_bytes_changed}, "
            f"window_ms={config.time_window_ms}, max_suppress_ms={config.max_suppress_ms}"
        )

    def _get_key(self, msg: CANMessage) -> Tuple:
        return (msg.can_id, msg.source) if self.config.compare_by_channel else (msg.can_id,)

    def _get_byte_indices(self) -> Optional[Set[int]]:
        """Parse/cached byte mask configuration."""
        if self.config.byte_mask == "all":
            self._byte_indices = None
            self._byte_mask_cache_key = "all"
            return None

        if self._byte_mask_cache_key == self.config.byte_mask:
            return self._byte_indices

        try:
            indices: Set[int] = set()
            parts = self.config.byte_mask.split(',')
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if '-' in part:
                    start_s, end_s = part.split('-', 1)
                    start, end = int(start_s), int(end_s)
                    if end < start:
                        start, end = end, start
                    for i in range(start, end + 1):
                        indices.add(i)
                else:
                    indices.add(int(part))
            self._byte_indices = indices
            self._byte_mask_cache_key = self.config.byte_mask
            return indices
        except Exception as e:
            self.logger.warning(f"Invalid byte mask '{self.config.byte_mask}': {e}")
            self._byte_indices = None
            self._byte_mask_cache_key = self.config.byte_mask
            return None

    def _calculate_bytes_changed_and_indices(self, msg1: CANMessage, msg2: CANMessage) -> tuple[int, List[int]]:
        """Return (changed_count, changed_indices) applying byte mask."""
        byte_indices = self._get_byte_indices()

        changed = 0
        changed_idxs: List[int] = []
        max_len = max(len(msg1.data), len(msg2.data))

        for i in range(max_len):
            if byte_indices is not None and i not in byte_indices:
                continue
            b1 = msg1.data[i] if i < len(msg1.data) else 0
            b2 = msg2.data[i] if i < len(msg2.data) else 0
            if b1 != b2:
                changed += 1
                changed_idxs.append(i)

        return changed, changed_idxs

    def _update_rate(self, key: Tuple, timestamp: float) -> float:
        window_ms = max(50, int(self.config.time_window_ms))
        window_s = window_ms / 1000.0
        dq = self._rate_windows[key]
        dq.append(timestamp)
        cutoff = timestamp - window_s
        while dq and dq[0] < cutoff:
            dq.popleft()
        return 0.0 if window_s <= 0 else (len(dq) / window_s)

    def _ensure_snapshot(self, key: Tuple, msg: CANMessage) -> None:
        if key not in self.snapshot:
            self.snapshot[key] = msg

    def take_snapshot(self, keys: Optional[List[Tuple]] = None) -> None:
        """Capture snapshot baseline from current last_seen."""
        if keys is None:
            keys = list(self.last_seen.keys())
        for k in keys:
            if k in self.last_seen:
                self.snapshot[k] = self.last_seen[k]
        self.logger.info(f"Diff snapshot captured: keys={len(keys)}")

    def format_data_with_delta(self, msg: CANMessage, changed_indices: List[int]) -> str:
        """ASCII-only formatting: changed bytes are wrapped in [..]."""
        changed_set = set(changed_indices)
        parts: List[str] = []
        for i, b in enumerate(msg.data):
            hx = f"{b:02X}"
            parts.append(f"[{hx}]" if i in changed_set else hx)
        return " ".join(parts)

    def get_last_seen_messages(self) -> Dict[Tuple, CANMessage]:
        return dict(self.last_seen)

    def evaluate(self, msg: CANMessage) -> DiffDecision:
        """
        Decide whether to display msg in Monitor mode.
        - Snapshot is used to compute delta/highlight (cansniffer-like baseline).
        - Suppression compares against last_displayed (show transitions).
        - Filtering only kicks in above min_message_rate (sliding window).
        """
        key = self._get_key(msg)

        # Always track last_seen so snapshot can be taken anytime.
        self.last_seen[key] = msg
        self._ensure_snapshot(key, msg)

        if not self.config.enabled:
            return DiffDecision(True, key, 0.0, 0, 0, [], "disabled")

        mode = (self.config.mode or "filter").strip().lower()
        if mode not in ("filter", "highlight", "both"):
            mode = "filter"

        self.total_received += 1
        stats = self.stats[key]
        stats.message_count += 1
        stats.last_timestamp = msg.timestamp
        rate = self._update_rate(key, msg.timestamp)
        stats.message_rate = rate

        snap = self.snapshot[key]
        bytes_changed_snap, changed_idxs_snap = self._calculate_bytes_changed_and_indices(msg, snap)

        # In highlight-only mode, we always show (no suppression), but we still keep
        # last_displayed updated so "bytes_changed_vs_last_displayed" remains meaningful.
        if mode == "highlight":
            if key in self.last_displayed:
                last_disp = self.last_displayed[key]
                bytes_changed_last, _ = self._calculate_bytes_changed_and_indices(msg, last_disp)
            else:
                bytes_changed_last = bytes_changed_snap

            self.last_displayed[key] = msg
            self._last_displayed_ts[key] = msg.timestamp
            self.total_displayed += 1
            stats.display_count += 1
            return DiffDecision(True, key, rate, bytes_changed_last, bytes_changed_snap, changed_idxs_snap, "highlight")

        # First time for this key: always show.
        if key not in self.last_displayed:
            self.last_displayed[key] = msg
            self._last_displayed_ts[key] = msg.timestamp
            self.total_displayed += 1
            stats.display_count += 1
            return DiffDecision(True, key, rate, bytes_changed_snap, bytes_changed_snap, changed_idxs_snap, "first")

        last_disp = self.last_displayed[key]
        bytes_changed_last, _ = self._calculate_bytes_changed_and_indices(msg, last_disp)

        # Below rate threshold -> always show
        if rate < self.config.min_message_rate:
            self.last_displayed[key] = msg
            self._last_displayed_ts[key] = msg.timestamp
            self.total_displayed += 1
            stats.display_count += 1
            return DiffDecision(True, key, rate, bytes_changed_last, bytes_changed_snap, changed_idxs_snap, "low_rate")

        # Show meaningful transitions (vs last displayed)
        if bytes_changed_last >= self.config.min_bytes_changed:
            self.last_displayed[key] = msg
            self._last_displayed_ts[key] = msg.timestamp
            self.total_displayed += 1
            stats.display_count += 1
            stats.bytes_changed_count += 1
            stats.total_bytes_changed += bytes_changed_last
            return DiffDecision(True, key, rate, bytes_changed_last, bytes_changed_snap, changed_idxs_snap, "delta")

        # Heartbeat
        max_suppress_ms = max(0, int(self.config.max_suppress_ms))
        last_ts = self._last_displayed_ts.get(key, msg.timestamp)
        if max_suppress_ms > 0 and (msg.timestamp - last_ts) * 1000.0 >= max_suppress_ms:
            self.last_displayed[key] = msg
            self._last_displayed_ts[key] = msg.timestamp
            self.total_displayed += 1
            stats.display_count += 1
            return DiffDecision(True, key, rate, bytes_changed_last, bytes_changed_snap, changed_idxs_snap, "heartbeat")

        # Suppress
        self.total_hidden += 1
        stats.hidden_count += 1
        return DiffDecision(False, key, rate, bytes_changed_last, bytes_changed_snap, changed_idxs_snap, "suppressed")

    def should_display_message(self, msg: CANMessage) -> bool:
        """Compatibility wrapper for older callers."""
        return self.evaluate(msg).display

    def get_statistics(self) -> Dict:
        hidden_percent = (self.total_hidden / self.total_received) * 100 if self.total_received > 0 else 0.0
        return {
            'total_received': self.total_received,
            'total_displayed': self.total_displayed,
            'total_hidden': self.total_hidden,
            'hidden_percent': hidden_percent,
            'unique_ids': len(self.last_seen),
            'enabled': self.config.enabled,
        }

    def get_id_statistics(self, can_id: int, source: str = None) -> Optional[Dict]:
        if self.config.compare_by_channel and source:
            key = (can_id, source)
        else:
            key = (can_id,)
        if key not in self.stats:
            return None
        stats = self.stats[key]
        avg = stats.total_bytes_changed / stats.bytes_changed_count if stats.bytes_changed_count > 0 else 0
        return {
            'message_count': stats.message_count,
            'message_rate': stats.message_rate,
            'bytes_changed_count': stats.bytes_changed_count,
            'total_bytes_changed': stats.total_bytes_changed,
            'avg_bytes_changed': avg,
            'display_count': stats.display_count,
            'hidden_count': stats.hidden_count,
        }

    def reset(self):
        """Reset all statistics and stored messages"""
        self.last_seen.clear()
        self.last_displayed.clear()
        self.snapshot.clear()
        self._last_displayed_ts.clear()
        self._rate_windows.clear()
        self.stats.clear()
        self.total_received = 0
        self.total_displayed = 0
        self.total_hidden = 0
        self._byte_indices = None
        self._byte_mask_cache_key = ""
        self.logger.info("DiffManager reset")

    def update_config(self, config: DiffConfig):
        self.config = config
        # Reset caches that depend on config.
        self._byte_indices = None
        self._byte_mask_cache_key = ""
        self.logger.info(f"DiffManager config updated: enabled={config.enabled}")
