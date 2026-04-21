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


# ── Globals ──────────────────────────────────────────────────────────────────
_mic_enabled = False

async def _nats_heartbeat(nc):
    import json
    while True:
        await asyncio.sleep(30)
        payload = {
            "service": "audio-capture-vad",
            "enabled": _mic_enabled,
            "uptime_seconds": int(time.time() - _stats["started_at"]),
            "frames_total": _stats["frames_total"],
            "frames_speech": _stats["frames_speech"],
            "sample_rate": config.sample_rate,
            "device": config.device_index
        }
        await nc.publish("audio.capture.status", json.dumps(payload).encode())


def _audio_loop(publisher: AudioPublisher, vad: VADPipeline, agc: AGC | None, nc=None):
    """Blocking audio capture loop — runs in a thread."""
    global _mic_enabled
    frame_size = config.frame_size
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
            # Check mic state before processing logic
            if not _mic_enabled:
                time.sleep(0.1)
                continue

            frame, overflowed = stream.read(frame_size)
            if overflowed:
                logger.debug("Audio buffer overflow")

            samples = frame[:, 0]  # mono
            rms = float(np.sqrt(np.mean(samples.astype(np.float32)**2)))
            
            if agc:
                samples = agc.process(samples)

            pcm = samples.tobytes()
            _stats["frames_total"] += 1

            is_speech = vad.is_speech(pcm)
            if is_speech:
                _stats["frames_speech"] += 1
                publisher.publish(pcm)

            # Telemetry for monitor
            if nc and (time.time() - last_telemetry > 0.1):
                last_telemetry = time.time()
                import json
                asyncio.run_coroutine_threadsafe(
                    nc.publish("mordomo.audio.vad.energy", json.dumps({
                        "energy": round(rms, 2),
                        "is_speech": is_speech,
                        "enabled": _mic_enabled
                    }).encode()),
                    asyncio.get_event_loop()
                )


async def main():
    global _mic_enabled
    # ── ZeroMQ publisher ───────────────────────────────────────────────
    publisher = AudioPublisher(config.zmq_bind, config.zmq_topic)
    publisher.start()

    # ── VAD & AGC ──────────────────────────────────────────────────────
    vad = VADPipeline(mode=config.vad_mode, sample_rate=config.sample_rate)
    agc = AGC(target_dbfs=config.agc_target_dbfs) if config.agc_enabled else None

    # ── NATS ───────────────────────────────────────────────────────────
    try:
        nc = await nats.connect(config.nats_url)
        logger.info("Control channel connected to NATS")
        
        async def _toggle_mic(msg):
            global _mic_enabled
            cmd = msg.data.decode().lower()
            if "open" in cmd:
                _mic_enabled = True
                logger.warning("🎙️  MICROPHONE OPENED VIA REMOTE COMMAND")
            else:
                _mic_enabled = False
                logger.info("💤  MICROPHONE CLOSED VIA REMOTE COMMAND")
            
            # Broadcast state
            await nc.publish("mordomo.audio.capture.state", json.dumps({
                "enabled": _mic_enabled,
                "timestamp": time.time()
            }).encode())

        await nc.subscribe("mordomo.audio.capture.open", cb=_toggle_mic)
        await nc.subscribe("mordomo.audio.capture.close", cb=_toggle_mic)
        asyncio.create_task(_nats_heartbeat(nc))
    except Exception as e:
        logger.warning(f"Control channel failed: {e}")
        nc = None

    # ── Capture loop (blocking) ───────────────────────────────────────
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _audio_loop, publisher, vad, agc, nc)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        publisher.close()
        if nc:
            await nc.drain()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
