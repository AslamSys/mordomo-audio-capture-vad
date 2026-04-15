import os


class Config:
    # Audio device
    device_index: int | None = (
        int(os.getenv("AUDIO_DEVICE_INDEX"))
        if os.getenv("AUDIO_DEVICE_INDEX") is not None
        else None
    )
    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))
    channels: int = 1
    frame_duration_ms: int = int(os.getenv("FRAME_DURATION_MS", "30"))   # 10 | 20 | 30
    hangover_ms: int = int(os.getenv("VAD_HANGOVER_MS", "300"))           # silence tail

    # VAD aggressiveness: 0=quality … 3=aggressive
    vad_mode: int = int(os.getenv("VAD_MODE", "3"))

    # AGC
    agc_enabled: bool = os.getenv("AGC_ENABLED", "true").lower() == "true"
    agc_target_dbfs: float = float(os.getenv("AGC_TARGET_DBFS", "-18.0"))

    # ZeroMQ publisher
    zmq_bind: str = os.getenv("ZMQ_BIND", "tcp://*:5555")
    zmq_topic: str = os.getenv("ZMQ_TOPIC", "audio.raw")

    # NATS (health + status publishing)
    nats_url: str = os.getenv("NATS_URL", "nats://nats:4222")

    @property
    def frame_size(self) -> int:
        """Samples per VAD frame."""
        return int(self.sample_rate * self.frame_duration_ms / 1000)

    @property
    def hangover_frames(self) -> int:
        return max(1, self.hangover_ms // self.frame_duration_ms)


config = Config()
