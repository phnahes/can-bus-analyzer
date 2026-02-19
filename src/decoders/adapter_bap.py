"""
VAG BAP Protocol Adapter (plugin for modular decoder system)

Wraps the core BAPDecoder and exposes it via ProtocolDecoder/DecodedData.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from .base import ProtocolDecoder, DecodedData, DecoderPriority
from .decoder_bap import BAPDecoder, BAPDetectionMode


class BAPProtocolDecoder(ProtocolDecoder):
    """Decoder for VAG BAP (PQ/MQB) traffic (app plugin)."""

    def __init__(self):
        super().__init__()
        self.priority = DecoderPriority.LOW  # keep out of the way; this is a detector
        self.decoder = BAPDecoder(detection_mode=BAPDetectionMode.CONSERVATIVE)

    def get_name(self) -> str:
        return "VAG BAP"

    def get_description(self) -> str:
        return "VW/Audi BAP protocol detector (PQ+MQB) - high confidence (multi-frame)"

    def get_settings(self) -> Dict[str, Any]:
        settings = super().get_settings()
        settings.update(
            {
                "detection_mode": self.decoder.detection_mode.value,
            }
        )
        return settings

    def set_settings(self, settings: Dict[str, Any]):
        super().set_settings(settings)
        mode = settings.get("detection_mode")
        if mode:
            self.decoder.set_detection_mode(mode)

    def can_decode(self, can_id: int, data: bytes, is_extended: bool) -> bool:
        # High-confidence default: only multi-frame preambles (0x80/0xC0).
        if not data or len(data) < 2:
            return False
        b0 = data[0]
        pre = (b0 & 0xC0)
        if pre == 0x80:
            return True  # start frame
        if pre == 0xC0:
            # only accept continuation when we already have an active stream
            mf_channel = (b0 >> 4) & 0x03
            return self.decoder.has_active_stream(can_id, is_extended=is_extended, mf_channel=mf_channel)
        return False

    def decode(self, can_id: int, data: bytes, is_extended: bool, timestamp: float) -> Optional[DecodedData]:
        try:
            result = self.decoder.decode_message(can_id, data, is_extended, timestamp=timestamp)

            if not result.get("success"):
                return DecodedData(
                    protocol="VAG BAP",
                    success=False,
                    confidence=0.0,
                    data={},
                    raw_description=f"Error: {result.get('error') or 'unable to decode'}",
                )

            if not result.get("is_complete"):
                # For the modular system we only emit completed payloads (keeps UI clean).
                return None

            platform = result.get("platform") or "?"
            hdr = result.get("header") or {}
            if hdr:
                desc = f"{platform} opcode={hdr.get('opcode')} lsg={hdr.get('lsg')} fct={hdr.get('fct')} len={result.get('total_len')}"
            else:
                mqb = result.get("mqb") or {}
                if mqb:
                    desc = f"{platform} lsg=0x{mqb.get('lsg', 0):02X} len={result.get('total_len')}"
                else:
                    desc = f"{platform} len={result.get('total_len')}"

            # Conservative multi-frame completion is strong signal.
            confidence = 0.95

            return DecodedData(
                protocol="VAG BAP",
                success=True,
                confidence=confidence,
                data=result,
                raw_description=desc,
                detailed_info=result,
            )
        except Exception as e:
            return DecodedData(
                protocol="VAG BAP",
                success=False,
                confidence=0.0,
                data={},
                raw_description=f"Decode error: {str(e)}",
            )

