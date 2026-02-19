"""
VAG BAP (Bedien- und Anzeigeprotokoll) - Core decoder

Goal for this project: detect BAP traffic with high confidence, and provide
basic reassembly/fields for UI visualization.

This module is application-agnostic (no PyQt) and keeps minimal state to
reassemble multi-frame BAP payloads.

BAP Protocol Overview:
----------------------
BAP is Volkswagen's bidirectional communication protocol on CAN bus.
- FSG (Functional control unit): typically radio/infotainment
- ASG (Display control unit): typically instrument cluster

Frame Structure:
- Single-frame: <= 8 bytes total, no preamble
- Multi-frame: uses preamble for segmentation
  - Start frame: 0x80 prefix, contains total length
  - Continuation frames: 0xC0 prefix, contains sequence index

Platform Differences:
- PQ (11-bit CAN ID): Older platform, LSG in header byte
- MQB (29-bit CAN ID): Newer platform, LSG embedded in CAN ID

BAP Header (after preamble):
- Opcode: 3 bits (operation type)
- LSG: 6 bits (logical control unit)
- FCT: 6 bits (function code)

References:
- https://github.com/norly/revag-bap (C implementation)
- https://github.com/tmbinc/kisim/tree/master/kisim (Python implementation)
- https://github.com/ea/vag-bap (header definitions)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple, Any


# ============================================================================
# Protocol Constants
# ============================================================================

# Multi-frame preamble masks
MF_PREAMBLE_MASK = 0xC0        # Mask to extract preamble bits (top 2 bits)
MF_START_PREAMBLE = 0x80       # Start frame preamble (10xxxxxx)
MF_CONT_PREAMBLE = 0xC0        # Continuation frame preamble (11xxxxxx)

# Multi-frame channel and sequence
MF_CHANNEL_MASK = 0x03         # Mask for MF channel (bits 4-5 of byte 0)
MF_CHANNEL_SHIFT = 4           # Shift to extract MF channel
MF_SEQ_MASK = 0x0F             # Mask for sequence index (bits 0-3 of byte 0)

# BAP header bit masks (PQ platform)
OPCODE_MASK = 0xE0             # Top 3 bits of header byte
OPCODE_SHIFT = 5               # Shift to extract opcode
LSG_MASK = 0x1F                # Bottom 5 bits of first header byte
FCT_MASK = 0x3F                # Bottom 6 bits of second header byte

# MQB CAN ID bit masks (29-bit extended ID)
MQB_LSG_MASK = 0x3F            # Bits 8-13 contain LSG
MQB_LSG_SHIFT = 8              # Shift to extract LSG from CAN ID
MQB_ENDPOINT_MASK = 0xFF       # Bottom 8 bits contain endpoint address

# Timeouts and limits
STREAM_TIMEOUT_SEC = 2.0       # Max age for incomplete multi-frame streams
MAX_BAP_LENGTH = 4095          # Maximum BAP payload length (12-bit field)


class BAPPlatform(str, Enum):
    PQ = "PQ"
    MQB = "MQB"


class BAPDetectionMode(str, Enum):
    # Conservative: only multi-frame traffic (0x80/0xC0) -> high confidence
    CONSERVATIVE = "conservative"
    # Aggressive: also attempt single-frame decode (more false positives)
    AGGRESSIVE = "aggressive"


@dataclass
class BAPHeaderPQ:
    opcode: int  # 0..7
    lsg: int     # 0..63
    fct: int     # 0..63


@dataclass
class _StreamState:
    total_len: int
    header_pq: Optional[BAPHeaderPQ]
    buffer: bytearray
    last_timestamp: float
    packet_id: int


class BAPDecoder:
    """
    Core decoder for BAP traffic.

    - High-confidence detection defaults to multi-frame only.
    - Reassembly keyed by (platform, can_id, mf_channel).
    """

    def __init__(self, detection_mode: BAPDetectionMode = BAPDetectionMode.CONSERVATIVE):
        self.detection_mode = detection_mode
        self._streams: Dict[Tuple[BAPPlatform, int, int], _StreamState] = {}
        self._packet_seq: int = 0

        # Conservative heuristic: once we see a valid multi-frame completion for a CAN ID,
        # we may treat single-frames on this ID as "likely BAP" if AGGRESSIVE is enabled.
        self._known_bap_ids_pq: set[int] = set()
        self._known_bap_ids_mqb: set[int] = set()

    def set_detection_mode(self, mode: str | BAPDetectionMode) -> None:
        try:
            self.detection_mode = BAPDetectionMode(str(mode))
        except Exception:
            self.detection_mode = BAPDetectionMode.CONSERVATIVE

    def clear(self) -> None:
        self._streams.clear()
        self._known_bap_ids_pq.clear()
        self._known_bap_ids_mqb.clear()
        self._packet_seq = 0

    def _cleanup_timeouts(self, timestamp: float, timeout_s: float = STREAM_TIMEOUT_SEC) -> None:
        """Remove incomplete multi-frame streams that have timed out."""
        if not self._streams:
            return
        to_delete = []
        for key, st in self._streams.items():
            if timestamp and st.last_timestamp and (timestamp - st.last_timestamp) > timeout_s:
                to_delete.append(key)
        for key in to_delete:
            del self._streams[key]

    @staticmethod
    def _is_multiframe_preamble(b0: int) -> bool:
        """Check if byte 0 has a multi-frame preamble (start or continuation)."""
        return (b0 & MF_PREAMBLE_MASK) in (MF_START_PREAMBLE, MF_CONT_PREAMBLE)

    @staticmethod
    def _is_start_frame(b0: int) -> bool:
        """Check if byte 0 indicates a start frame (0x80 pattern)."""
        return (b0 & MF_PREAMBLE_MASK) == MF_START_PREAMBLE

    @staticmethod
    def _is_cont_frame(b0: int) -> bool:
        """Check if byte 0 indicates a continuation frame (0xC0 pattern)."""
        return (b0 & MF_PREAMBLE_MASK) == MF_CONT_PREAMBLE

    @staticmethod
    def _mf_channel_from_b0(b0: int) -> int:
        """Extract multi-frame channel (0-3) from bits 4-5 of byte 0."""
        return (b0 >> MF_CHANNEL_SHIFT) & MF_CHANNEL_MASK

    @staticmethod
    def _len_from_start_frame(b0: int, b1: int) -> int:
        """Extract 12-bit payload length from start frame (low nibble of b0 + b1)."""
        return ((b0 & MF_SEQ_MASK) << 8) | (b1 & 0xFF)

    @staticmethod
    def _parse_pq_header(data: bytes, offset: int = 0) -> Optional[BAPHeaderPQ]:
        """
        Parse PQ platform BAP header (2 bytes big-endian).
        
        Format: opcode(3 bits) / lsg(6 bits) / fct(6 bits)
        Total: 15 bits packed into 2 bytes
        """
        if len(data) < offset + 2:
            return None
        header = (data[offset] << 8) | data[offset + 1]
        opcode = (header >> 12) & 0x7
        lsg = (header >> 6) & FCT_MASK
        fct = header & FCT_MASK
        return BAPHeaderPQ(opcode=opcode, lsg=lsg, fct=fct)

    @staticmethod
    def _extract_mqb_id_fields(can_id: int) -> Dict[str, int]:
        """
        Extract BAP fields from MQB 29-bit CAN ID.
        
        MQB embeds LSG and endpoint in the extended CAN ID.
        Example: 0x17333310 -> base=0x1733, lsg=0x33, endpoint=0x10
        """
        return {
            "base_id": (can_id >> 16) & 0xFFFF,
            "lsg": (can_id >> MQB_LSG_SHIFT) & MQB_LSG_MASK,
            "subsystem": can_id & MQB_ENDPOINT_MASK,
        }

    def decode_message(self, can_id: int, data: bytes, is_extended: bool, timestamp: float = 0.0) -> Dict[str, Any]:
        """
        Decode a single CAN frame and (if multi-frame completes) emit a reassembled BAP message.

        Returns a dict with keys:
          - success: bool
          - is_bap_candidate: bool
          - is_complete: bool
          - platform: "PQ"|"MQB"|None
          - header: (PQ) {opcode,lsg,fct} if known
          - payload: hex string if complete
          - error: optional string
        """
        result: Dict[str, Any] = {
            "raw_id": can_id,
            "raw_data": (data or b"").hex(),
            "is_extended": bool(is_extended),
            "success": False,
            "is_bap_candidate": False,
            "is_complete": False,
            "platform": None,
            "header": None,
            "mqb": None,
            "total_len": None,
            "mf_channel": None,
            "packet_id": None,
            "payload": None,
            "error": None,
        }

        if not data or len(data) < 2:
            return result

        # Drop old partial streams.
        self._cleanup_timeouts(timestamp, timeout_s=STREAM_TIMEOUT_SEC)

        platform = BAPPlatform.MQB if is_extended else BAPPlatform.PQ

        b0 = data[0]
        if self._is_multiframe_preamble(b0):
            result["is_bap_candidate"] = True
            result["platform"] = platform.value
            mf_channel = self._mf_channel_from_b0(b0)
            result["mf_channel"] = mf_channel

            if self._is_start_frame(b0):
                # Start frame needs length + (usually) a 2-byte header.
                if len(data) < 4:
                    result["error"] = "Start frame too short"
                    return result

                total_len = self._len_from_start_frame(b0, data[1])
                result["total_len"] = total_len
                if total_len <= 0 or total_len > MAX_BAP_LENGTH:
                    result["error"] = f"Invalid total_len={total_len}"
                    return result

                header_pq: Optional[BAPHeaderPQ] = None
                if platform == BAPPlatform.PQ:
                    header_pq = self._parse_pq_header(data, offset=2)
                    if header_pq:
                        result["header"] = {"opcode": header_pq.opcode, "lsg": header_pq.lsg, "fct": header_pq.fct}
                else:
                    result["mqb"] = self._extract_mqb_id_fields(can_id)

                # Payload part in this CAN frame:
                # PQ: bytes 4..end (header consumes bytes 2..3)
                # MQB: we keep the same slicing; this works as "best effort".
                chunk = data[4:]
                if len(chunk) > total_len:
                    result["error"] = "Start chunk exceeds total length"
                    return result

                key = (platform, can_id, mf_channel)
                self._packet_seq += 1
                packet_id = self._packet_seq
                result["packet_id"] = packet_id
                self._streams[key] = _StreamState(
                    total_len=total_len,
                    header_pq=header_pq,
                    buffer=bytearray(chunk),
                    last_timestamp=timestamp,
                    packet_id=packet_id,
                )

                # Complete in a single start frame (<=4 payload bytes typical).
                if len(chunk) == total_len:
                    payload = bytes(chunk)
                    self._finish_stream(key)
                    return self._build_complete_result(result, platform, can_id, mf_channel, total_len, header_pq, payload)

                # Incomplete: wait for continuations.
                result["success"] = True
                return result

            # Continuation frame
            if self._is_cont_frame(b0):
                key = (platform, can_id, mf_channel)
                st = self._streams.get(key)
                if not st:
                    result["error"] = "Continuation without active stream"
                    return result
                result["packet_id"] = st.packet_id

                chunk = data[1:]
                if not chunk:
                    result["error"] = "Empty continuation chunk"
                    self._finish_stream(key, drop=True)
                    return result

                if len(st.buffer) + len(chunk) > st.total_len:
                    result["error"] = "Continuation exceeds total length"
                    self._finish_stream(key, drop=True)
                    return result

                st.buffer.extend(chunk)
                st.last_timestamp = timestamp
                result["total_len"] = st.total_len
                if st.header_pq:
                    result["header"] = {"opcode": st.header_pq.opcode, "lsg": st.header_pq.lsg, "fct": st.header_pq.fct}
                if platform == BAPPlatform.MQB:
                    result["mqb"] = self._extract_mqb_id_fields(can_id)
                result["bytes_done"] = len(st.buffer)

                if len(st.buffer) == st.total_len:
                    payload = bytes(st.buffer)
                    header_pq = st.header_pq
                    self._finish_stream(key)
                    return self._build_complete_result(result, platform, can_id, mf_channel, st.total_len, header_pq, payload)

                result["success"] = True
                return result

        # Single-frame (only when aggressive mode is enabled)
        if self.detection_mode == BAPDetectionMode.AGGRESSIVE:
            if platform == BAPPlatform.PQ:
                if can_id not in self._known_bap_ids_pq:
                    # Keep aggressive mode still reasonably safe: require we saw multi-frame first.
                    return result
                header = self._parse_pq_header(data, offset=0)
                if not header:
                    return result
                payload = data[2:]
                result.update(
                    {
                        "success": True,
                        "is_bap_candidate": True,
                        "is_complete": True,
                        "platform": platform.value,
                        "header": {"opcode": header.opcode, "lsg": header.lsg, "fct": header.fct},
                        "total_len": len(payload),
                        "payload": payload.hex(),
                    }
                )
                return result
            else:
                if can_id not in self._known_bap_ids_mqb:
                    return result
                # MQB single-frame structure varies; show raw payload.
                payload = data
                result.update(
                    {
                        "success": True,
                        "is_bap_candidate": True,
                        "is_complete": True,
                        "platform": platform.value,
                        "mqb": self._extract_mqb_id_fields(can_id),
                        "total_len": len(payload),
                        "payload": payload.hex(),
                    }
                )
                return result

        return result

    def _finish_stream(self, key: Tuple[BAPPlatform, int, int], drop: bool = False) -> None:
        try:
            st = self._streams.get(key)
            if not st:
                return
            if not drop:
                platform, can_id, _ = key
                if platform == BAPPlatform.PQ:
                    self._known_bap_ids_pq.add(can_id)
                else:
                    self._known_bap_ids_mqb.add(can_id)
        finally:
            if key in self._streams:
                del self._streams[key]

    def _build_complete_result(
        self,
        base: Dict[str, Any],
        platform: BAPPlatform,
        can_id: int,
        mf_channel: int,
        total_len: int,
        header_pq: Optional[BAPHeaderPQ],
        payload: bytes,
    ) -> Dict[str, Any]:
        out = dict(base)
        out["success"] = True
        out["is_complete"] = True
        out["platform"] = platform.value
        out["mf_channel"] = mf_channel
        out["total_len"] = total_len
        out["payload"] = payload.hex()
        out["bytes_done"] = len(payload)
        if platform == BAPPlatform.PQ and header_pq:
            out["header"] = {"opcode": header_pq.opcode, "lsg": header_pq.lsg, "fct": header_pq.fct}
        if platform == BAPPlatform.MQB:
            out["mqb"] = self._extract_mqb_id_fields(can_id)
        return out

    def get_active_streams_count(self) -> int:
        return len(self._streams)

    def has_active_stream(self, can_id: int, is_extended: bool, mf_channel: int) -> bool:
        platform = BAPPlatform.MQB if is_extended else BAPPlatform.PQ
        return (platform, can_id, int(mf_channel) & 0x03) in self._streams

    def get_stream_progress(self, can_id: int, is_extended: bool, mf_channel: int) -> Optional[Dict[str, int]]:
        """
        Return stream progress for an active multi-frame reassembly, if any.

        Returns:
          { "done": <bytes>, "total": <bytes> } or None if no active stream.
        """
        platform = BAPPlatform.MQB if is_extended else BAPPlatform.PQ
        key = (platform, can_id, int(mf_channel) & 0x03)
        st = self._streams.get(key)
        if not st:
            return None
        return {"done": len(st.buffer), "total": int(st.total_len), "packet_id": int(st.packet_id)}

