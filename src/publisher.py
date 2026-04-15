"""
Audio publisher — ZeroMQ PUB socket that streams audio frames.

Message format (multipart):
  frame 0: topic bytes  (e.g. b"audio.raw")
  frame 1: raw PCM bytes (int16 LE, 16 kHz, mono)
"""
import logging

import zmq

logger = logging.getLogger("audio-capture-vad.publisher")


class AudioPublisher:
    def __init__(self, bind: str, topic: str):
        self._bind = bind
        self._topic = topic.encode()
        self._ctx = zmq.Context.instance()
        self._sock: zmq.Socket | None = None

    def start(self):
        self._sock = self._ctx.socket(zmq.PUB)
        self._sock.bind(self._bind)
        # Small HWM so slow consumers don't cause memory bloat
        self._sock.setsockopt(zmq.SNDHWM, 10)
        logger.info(f"ZeroMQ PUB bound to {self._bind}, topic={self._topic.decode()}")

    def publish(self, pcm_bytes: bytes):
        if self._sock:
            self._sock.send_multipart([self._topic, pcm_bytes], flags=zmq.NOBLOCK)

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None
