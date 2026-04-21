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
            "device": config.device_index,
        }
        await nc.publish("audio.capture.status", json.dumps(payload).encode())


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

        # Apply VAD — only publish if speech detected
        is_speech = vad.is_speech(pcm_bytes)
        if is_speech:
            _stats["frames_speech"] += 1
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
                        "energy": round(rms, 2),
                        "is_speech": is_speech,
                        "enabled": True,
                        "source": "virtual",
                    }).encode(),
                ),
                loop,
            )

    sock.close()


def _audio_loop(publisher: AudioPublisher, vad: VADPipeline, agc: AGC | None, nc=None, loop=None):
    """Blocking hardware capture loop — runs in thread executor."""
    global _mic_enabled
    frame_size   = config.frame_size
    last_telemetry = 0

    logger.info(f"Capture service ready. (Device={config.device_index})")

    with sd.InputStream(
        device=config.device_index,
        samplerate=config.sample_rate,
        channels=config.channels,
        dtype="int16",
        blocksize=frame_size,
    ) as stream:
        while True:
            if not _mic_enabled:
                time.sleep(0.1)
                continue

            frame, overflowed = stream.read(frame_size)
            if overflowed:
                logger.debug("Audio buffer overflow")

            samples = frame[:, 0]  # mono
            rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))

            if agc:
                samples = agc.process(samples)

            pcm = samples.tobytes()
            _stats["frames_total"] += 1

            is_speech = vad.is_speech(pcm)
            if is_speech:
                _stats["frames_speech"] += 1
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
            global _mic_enabled
            is_open = "open" in msg.subject
            _mic_enabled = is_open
            logger.warning(f"🎙️  HARDWARE MIC {'OPENED' if is_open else 'CLOSED'}")
            await nc.publish(
                "mordomo.audio.capture.state",
                json.dumps({
                    "enabled": _mic_enabled,
                    "source": "hardware",
                    "timestamp": time.time(),
                }).encode(),
            )

        await nc.subscribe("mordomo.audio.capture.open",  cb=_toggle_mic)
        await nc.subscribe("mordomo.audio.capture.close", cb=_toggle_mic)
        asyncio.create_task(_nats_heartbeat(nc))

    except Exception as e:
        logger.warning(f"Control channel failed: {e} — running without NATS")

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
        await loop.run_in_executor(None, _audio_loop, publisher, vad, agc, nc, loop)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        publisher.close()
        if nc:
            await nc.drain()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
