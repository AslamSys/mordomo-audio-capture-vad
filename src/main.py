"""
Main entry point — captures mic, applies VAD+AGC, publishes via ZeroMQ.
Also publishes health status to NATS every 30 s.
"""
import asyncio
import logging
import time

import numpy as np
import sounddevice as sd
import nats

from src.config import config
from src.vad import VADPipeline
from src.agc import AGC
from src.publisher import AudioPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("audio-capture-vad")

# ── Stats ──────────────────────────────────────────────────────────────────
_stats = {
    "frames_total": 0,
    "frames_speech": 0,
    "started_at": time.time(),
}


async def _nats_heartbeat(nc):
    import json
    while True:
        await asyncio.sleep(30)
        payload = {
            "service": "audio-capture-vad",
            "uptime_seconds": int(time.time() - _stats["started_at"]),
            "frames_total": _stats["frames_total"],
            "frames_speech": _stats["frames_speech"],
            "sample_rate": config.sample_rate,
            "frame_duration_ms": config.frame_duration_ms,
            "vad_mode": config.vad_mode,
        }
        await nc.publish("audio.capture.status", json.dumps(payload).encode())


def _audio_loop(publisher: AudioPublisher, vad: VADPipeline, agc: AGC | None):
    """Blocking audio capture loop — runs in a thread."""
    frame_size = config.frame_size

    logger.info(
        f"Starting capture: device={config.device_index}, "
        f"rate={config.sample_rate}, frame={frame_size} samples "
        f"({config.frame_duration_ms}ms)"
    )

    with sd.InputStream(
        device=config.device_index,
        samplerate=config.sample_rate,
        channels=config.channels,
        dtype="int16",
        blocksize=frame_size,
    ) as stream:
        logger.info("Microphone open — streaming started")
        while True:
            frame, overflowed = stream.read(frame_size)
            if overflowed:
                logger.debug("Audio buffer overflow")

            samples = frame[:, 0]  # mono

            if agc:
                samples = agc.process(samples)

            pcm = samples.tobytes()

            _stats["frames_total"] += 1

            if vad.is_speech(pcm):
                _stats["frames_speech"] += 1
                publisher.publish(pcm)


async def main():
    # ── ZeroMQ publisher ───────────────────────────────────────────────
    publisher = AudioPublisher(config.zmq_bind, config.zmq_topic)
    publisher.start()

    # ── VAD ────────────────────────────────────────────────────────────
    vad = VADPipeline(
        mode=config.vad_mode,
        sample_rate=config.sample_rate,
        frame_duration_ms=config.frame_duration_ms,
        hangover_frames=config.hangover_frames,
    )

    # ── AGC ────────────────────────────────────────────────────────────
    agc = AGC(target_dbfs=config.agc_target_dbfs) if config.agc_enabled else None

    # ── NATS ───────────────────────────────────────────────────────────
    try:
        async def error_cb(e):
            logger.error(f"NATS error: {e}")

        async def reconnected_cb():
            logger.warning("NATS reconnected")

        async def disconnected_cb():
            logger.warning("NATS disconnected")

        nc = await nats.connect(
            config.nats_url,
            error_cb=error_cb,
            reconnected_cb=reconnected_cb,
            disconnected_cb=disconnected_cb,
        )
        logger.info(f"Connected to NATS: {config.nats_url}")
        asyncio.create_task(_nats_heartbeat(nc))
    except Exception as e:
        logger.warning(f"NATS unavailable — continuing without heartbeat: {e}")
        nc = None

    # ── Capture loop in thread (blocking) ─────────────────────────────
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _audio_loop, publisher, vad, agc)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        publisher.close()
        if nc:
            await nc.drain()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
