"""
Main entry point — captures mic, applies VAD+AGC, publishes via ZeroMQ.
Also publishes health status to NATS every 30 s.
"""
import asyncio
import logging
import time
import json

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


def _audio_loop(publisher: AudioPublisher, vad: VADPipeline, agc: AGC | None, nc=None, loop=None):
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
            if nc and loop and (time.time() - last_telemetry > 0.1):
                last_telemetry = time.time()
                asyncio.run_coroutine_threadsafe(
                    nc.publish("mordomo.audio.vad.energy", json.dumps({
                        "energy": round(rms, 2),
                        "is_speech": is_speech,
                        "enabled": _mic_enabled
                    }).encode()),
                    loop
                )


async def main():
    global _mic_enabled
    # ── ZeroMQ publisher ───────────────────────────────────────────────
    publisher = AudioPublisher(config.zmq_bind, config.zmq_topic)
    publisher.start()

    # ── VAD & AGC ──────────────────────────────────────────────────────
    vad = VADPipeline(
        mode=config.vad_mode, 
        sample_rate=config.sample_rate,
        frame_duration_ms=config.frame_duration_ms,
        hangover_frames=config.hangover_frames
    )
    agc = AGC(target_dbfs=config.agc_target_dbfs) if config.agc_enabled else None

    # ── NATS ───────────────────────────────────────────────────────────
    _virtual_active = False 
    try:
        nc = await nats.connect(config.nats_url)
        logger.info("Control channel connected to NATS")
        
        async def _toggle_mic(msg):
            global _mic_enabled
            nonlocal _virtual_active
            try:
                payload = json.loads(msg.data.decode())
            except:
                payload = {"source": "hardware"}
            
            source = payload.get("source", "hardware")
            is_open = "open" in msg.subject
            
            if source == "browser-pc":
                _virtual_active = is_open
                logger.warning(f"🌐 VIRTUAL SESSION {'STARTED' if is_open else 'ENDED'}")
            else:
                _mic_enabled = is_open
                logger.warning(f"🎙️ HARDWARE MIC {'OPENED' if is_open else 'CLOSED'}")
            
            await nc.publish("mordomo.audio.capture.state", json.dumps({
                "enabled": _mic_enabled or _virtual_active,
                "source": source,
                "timestamp": time.time()
            }).encode())

        _virtual_audio_buffer = bytearray()

        async def _nats_audio_stream(msg):
            """Handler for virtual audio stream coming from NATS (Browser)."""
            nonlocal _virtual_audio_buffer
            if _virtual_active and vad:
                try:
                    data = msg.data
                    _virtual_audio_buffer.extend(data)
                    frame_size = vad._frame_bytes
                    while len(_virtual_audio_buffer) >= frame_size:
                        chunk_bytes = bytes(_virtual_audio_buffer[:frame_size])
                        _virtual_audio_buffer = _virtual_audio_buffer[frame_size:]
                        
                        chunk_np = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        rms = np.sqrt(np.mean(chunk_np**2))
                        await nc.publish("mordomo.audio.vad.energy", json.dumps({"rms": float(rms)}).encode())
                        
                        if vad.is_speech(chunk_bytes):
                            logger.info("🎙️  VIRTUAL SPEECH DETECTED")
                            await nc.publish("mordomo.audio.vad.speech", chunk_bytes)
                except Exception as e:
                    logger.error(f"Virtual VAD Error: {e}")

        await nc.subscribe("mordomo.audio.capture.open", cb=_toggle_mic)
        await nc.subscribe("mordomo.audio.capture.close", cb=_toggle_mic)
        await nc.subscribe("mordomo.audio.stream", cb=_nats_audio_stream)
        asyncio.create_task(_nats_heartbeat(nc))
    except Exception as e:
        logger.warning(f"Control channel failed: {e}")
        nc = None

    # ── Capture loop (blocking) ───────────────────────────────────────
    loop = asyncio.get_event_loop()
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
