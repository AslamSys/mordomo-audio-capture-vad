"""PCM int16 resampling (e.g. USB 48 kHz → pipeline 16 kHz)."""
import numpy as np


def resample_int16(samples: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    if from_rate == to_rate or len(samples) == 0:
        return samples

    out_len = max(1, int(round(len(samples) * to_rate / from_rate)))
    x_old = np.arange(len(samples), dtype=np.float64)
    x_new = np.linspace(0, len(samples) - 1, num=out_len)
    return np.interp(x_new, x_old, samples.astype(np.float64)).astype(np.int16)
