"""
VAD pipeline — wraps webrtcvad with hangover logic.

webrtcvad requires frames of exactly 10, 20, or 30 ms at
8000, 16000, 32000 or 48000 Hz in 16-bit mono PCM.
"""
import collections
import logging

import webrtcvad

logger = logging.getLogger("audio-capture-vad.vad")


class VADPipeline:
    def __init__(self, mode: int, sample_rate: int, frame_duration_ms: int, hangover_frames: int):
        self._vad = webrtcvad.Vad(mode)
        self._sample_rate = sample_rate
        self._frame_bytes = int(sample_rate * frame_duration_ms / 1000) * 2  # int16 = 2 bytes
        self._hangover_frames = hangover_frames
        self._hangover_counter = 0

    def is_speech(self, frame_bytes: bytes) -> bool:
        """
        Returns True while voice is active, including hangover tail.
        frame_bytes must be exactly self._frame_bytes long.
        """
        if len(frame_bytes) != self._frame_bytes:
            logger.warning(
                f"VAD: unexpected frame size {len(frame_bytes)} (expected {self._frame_bytes})"
            )
            return False

        try:
            active = self._vad.is_speech(frame_bytes, self._sample_rate)
        except Exception as e:
            logger.debug(f"VAD error: {e}")
            return False

        if active:
            self._hangover_counter = self._hangover_frames
            return True

        if self._hangover_counter > 0:
            self._hangover_counter -= 1
            return True

        return False
