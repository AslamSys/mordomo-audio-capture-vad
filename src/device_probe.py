"""Resolve PortAudio capture rate for a given device."""
import logging

import sounddevice as sd

logger = logging.getLogger("audio-capture-vad.device_probe")


def resolve_capture_sample_rate(
    device_index: int | None,
    output_rate: int,
    explicit_capture_rate: int | None,
) -> int:
    if explicit_capture_rate:
        sd.check_input_settings(
            device=device_index, channels=1, samplerate=explicit_capture_rate
        )
        return explicit_capture_rate

    for rate in (output_rate, 48000, 44100, 32000, 8000):
        try:
            sd.check_input_settings(device=device_index, channels=1, samplerate=rate)
            if rate != output_rate:
                logger.info(
                    "Capture rate %s Hz (output/ZMQ/VAD at %s Hz via resample)",
                    rate,
                    output_rate,
                )
            return rate
        except Exception:
            continue

    raise RuntimeError(
        f"No supported capture sample rate for device_index={device_index}"
    )
