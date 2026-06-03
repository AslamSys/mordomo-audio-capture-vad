"""
Main entry point — captures mic, applies VAD+AGC, publishes via ZeroMQ.
Also listens on a PULL socket for virtual audio injected by debug_neural.py
and re-publishes those frames through the same PUB socket, so all downstream
consumers (wake-word, whisper) receive both hardware and virtual audio.

ZMQ sockets:
  PUB  tcp://*:5555  — broadcast to all subscribers (audio.raw)
  PULL tcp://*:5556  — receive virtual frames from mordomo-people (debug bridge)
"""
import asyncio
import logging
import time
import json
import threading

import numpy as np
import sounddevice as sd
import nats
import zmq

from src.config import config
from src.vad import VADPipeline
from src.agc import AGC
from src.publisher import AudioPublisher
from src.resample import resample_int16
from src.device_probe import resolve_capture_sample_rate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("audio-capture-vad")

# ── Stats ──────────────────────────────────────────────────────────────────
_stats = {
    "frames_total": 0,
    "frames_speech": 0,
    "frames_virtual": 0,
    "started_at": time.time(),
}

# ── Globals ───────────────────────────────────────────────────────────────
_mic_enabled = False


async def _nats_heartbeat(nc):
    while True:
        await asyncio.sleep(30)
        payload = {
            "service": "audio-capture-vad",
            "enabled": _mic_enabled,
            "uptime_seconds": int(time.time() - _stats["started_at"]),
            "frames_total": _stats["frames_total"],
            "frames_speech": _stats["frames_speech"],
            "frames_virtual": _stats["frames_virtual"],
            "sample_rate": config.sample_rate,
            "capture_sample_rate": getattr(config, "_active_capture_rate", config.sample_rate),
            "device": config.device_index,
        }
        await nc.publish("audio.capture.status", json.dumps(payload).encode())


async def _set_mic_enabled(nc, enabled: bool, reason: str):
    global _mic_enabled
    _mic_enabled = enabled
    logger.warning(
        "🎙️  HARDWARE MIC %s (%s)",
        "OPENED" if enabled else "CLOSED",
        reason,
    )
    if nc:
        await nc.publish(
            "mordomo.audio.capture.state",
            json.dumps({
                "enabled": _mic_enabled,
                "source": "hardware",
                "timestamp": time.time(),
                "reason": reason,
            }).encode(),
        )


def _virtual_pull_loop(publisher: AudioPublisher, vad: VADPipeline, nc=None, loop=None):
    """
    Blocking PULL loop — receives PCM frames injected by debug_neural.py,
    runs them through VAD and re-publishes via the main PUB socket.
    Runs in a dedicated daemon thread.
    """
    pull_bind = config.zmq_pull_bind   # tcp://*:5556
    topic_bytes = config.zmq_topic.encode()

    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.PULL)
    sock.bind(pull_bind)
    sock.setsockopt(zmq.RCVTIMEO, 500)  # 500 ms timeout so thread can exit
    logger.info(f"ZMQ PULL socket bound to {pull_bind} — waiting for virtual frames")

    last_telemetry = 0

    while True:
        try:
            pcm_bytes = sock.recv()
        except zmq.Again:
            continue
        except zmq.ZMQError:
            break

        _stats["frames_virtual"] += 1
        _stats["frames_total"] += 1

        # Virtual frames bypass VAD — publish ALL frames directly.
        # The Wake Word detector has its own decision logic.
        # (VAD filtering is only needed to save bandwidth from the hardware mic.)
        publisher.publish(pcm_bytes)

        # Telemetry for dashboard
        if nc and loop and (time.time() - last_telemetry > 0.1):
            last_telemetry = time.time()
            samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            rms = float(np.sqrt(np.mean(samples ** 2)))
            asyncio.run_coroutine_threadsafe(
                nc.publish(
                    "mordomo.audio.vad.energy",
                    json.dumps({
                        "energy": round(rms, 6),
                        "is_speech": rms > 100,   # rough threshold for display only
                        "enabled": True,
                        "source": "virtual",
                    }).encode(),
                ),
                loop,
            )


    sock.close()


def _audio_loop(
    publisher: AudioPublisher,
    vad: VADPipeline,
    agc: AGC | None,
    capture_sample_rate: int,
    nc=None,
    loop=None,
):
    """Blocking hardware capture loop — runs in thread executor."""
    global _mic_enabled
    capture_frame_size = config.capture_frame_size(capture_sample_rate)
    last_telemetry = 0

    logger.info(
        "Capture service ready. (Device=%s, capture=%s Hz, output=%s Hz)",
        config.device_index,
        capture_sample_rate,
        config.sample_rate,
    )

    with sd.InputStream(
        device=config.device_index,
        samplerate=capture_sample_rate,
        channels=config.channels,
        dtype="int16",
        blocksize=capture_frame_size,
    ) as stream:
        while True:
            if not _mic_enabled:
                time.sleep(0.1)
                continue

            frame, overflowed = stream.read(capture_frame_size)
            if overflowed:
                logger.debug("Audio buffer overflow")

            samples = frame[:, 0]  # mono
            if capture_sample_rate != config.sample_rate:
                samples = resample_int16(samples, capture_sample_rate, config.sample_rate)

            rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))

            if agc:
                samples = agc.process(samples)

            pcm = samples.tobytes()
            _stats["frames_total"] += 1

            is_speech = vad.is_speech(pcm)
            if is_speech:
                _stats["frames_speech"] += 1

            # Wake-word needs a continuous stream, not only VAD-positive frames.
            publisher.publish(pcm)

            if nc and loop and (time.time() - last_telemetry > 0.1):
                last_telemetry = time.time()
                asyncio.run_coroutine_threadsafe(
                    nc.publish(
                        "mordomo.audio.vad.energy",
                        json.dumps({
                            "energy": round(rms, 2),
                            "is_speech": is_speech,
                            "enabled": _mic_enabled,
                            "source": "hardware",
                        }).encode(),
                    ),
                    loop,
                )


async def main():
    global _mic_enabled

    # ── ZeroMQ PUB publisher ───────────────────────────────────────────────
    publisher = AudioPublisher(config.zmq_bind, config.zmq_topic)
    publisher.start()

    # ── VAD & AGC ──────────────────────────────────────────────────────────
    vad = VADPipeline(
        mode=config.vad_mode,
        sample_rate=config.sample_rate,
        frame_duration_ms=config.frame_duration_ms,
        hangover_frames=config.hangover_frames,
    )
    agc = AGC(target_dbfs=config.agc_target_dbfs) if config.agc_enabled else None

    # ── NATS — control channel only ────────────────────────────────────────
    nc = None
    try:
        nc = await nats.connect(config.nats_url)
        logger.info("Control channel connected to NATS")

        async def _toggle_mic(msg):
            is_open = "open" in msg.subject
            await _set_mic_enabled(nc, is_open, reason="nats")

        await nc.subscribe("mordomo.audio.capture.open",  cb=_toggle_mic)
        await nc.subscribe("mordomo.audio.capture.close", cb=_toggle_mic)
        asyncio.create_task(_nats_heartbeat(nc))

        if config.mic_open_on_start:
            await _set_mic_enabled(nc, True, reason="boot")

    except Exception as e:
        logger.warning(f"Control channel failed: {e} — running without NATS")
        if config.mic_open_on_start:
            _mic_enabled = True
            logger.warning("🎙️  HARDWARE MIC OPENED (boot, NATS unavailable)")

    capture_sample_rate = resolve_capture_sample_rate(
        config.device_index,
        config.sample_rate,
        config.capture_sample_rate,
    )
    config._active_capture_rate = capture_sample_rate  # type: ignore[attr-defined]

    loop = asyncio.get_event_loop()

    # ── Virtual PULL loop (daemon thread — always running) ─────────────────
    pull_thread = threading.Thread(
        target=_virtual_pull_loop,
        args=(publisher, vad, nc, loop),
        daemon=True,
        name="zmq-pull-virtual",
    )
    pull_thread.start()
    logger.info("ZMQ PULL virtual bridge thread started")

    # ── Hardware capture loop (blocking executor) ──────────────────────────
    try:
        await loop.run_in_executor(
            None, _audio_loop, publisher, vad, agc, capture_sample_rate, nc, loop
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        publisher.close()
        if nc:
            await nc.drain()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
