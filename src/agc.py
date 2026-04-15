"""
AGC — simple digital gain control.
Adjusts frame gain to keep average RMS near target_dbfs.
"""
import numpy as np

_REF = 32768.0  # int16 max


def _rms_dbfs(samples: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
    if rms < 1.0:
        return -96.0
    return 20.0 * np.log10(rms / _REF)


class AGC:
    def __init__(self, target_dbfs: float = -18.0, speed: float = 0.05):
        self._target = target_dbfs
        self._speed = speed          # how fast gain tracks (0–1)
        self._gain: float = 1.0

    def process(self, samples: np.ndarray) -> np.ndarray:
        db = _rms_dbfs(samples)
        error = self._target - db
        # Adjust gain slowly toward target
        self._gain *= 10 ** (error * self._speed / 20.0)
        self._gain = float(np.clip(self._gain, 0.1, 10.0))
        out = (samples.astype(np.float32) * self._gain).clip(-32768, 32767)
        return out.astype(np.int16)
