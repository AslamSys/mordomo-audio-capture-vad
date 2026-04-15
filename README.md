# 🎤 Audio Capture + VAD

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---

**Container:** `audio-capture-vad`  
**Ecossistema:** Mordomo  
**Posição no Fluxo:** Primeiro componente - entrada de áudio

---

## 📋 Propósito

**Produtor contínuo de áudio filtrado** - Captura áudio do microfone 24/7, aplica filtros (VAD, eco, ruído) e distribui via ZeroMQ para todos os consumidores (Wake Word Detector e futuros componentes). Este container é a **única fonte de áudio** do sistema.

---

## 🎯 Responsabilidades

### Primárias
- ✅ **Capturar áudio continuamente** do microfone (nunca para)
- ✅ **Aplicar VAD** para detectar atividade de voz
- ✅ **Filtrar silêncio e ruído** de fundo
- ✅ **Cancelar eco** (AEC) do próprio TTS
- ✅ **Distribuir áudio via ZeroMQ** (PUB/SUB) para todos os consumidores
- ✅ **Publicar apenas quando VAD detecta voz ativa** (economiza processamento)

### Secundárias
- ✅ Monitorar qualidade do áudio (SNR, clipping)
- ✅ Auto-ajuste de ganho (AGC)
- ✅ Log de métricas de captura
- ✅ Health check do dispositivo de áudio

---

## 🔄 Papel no Fluxo do Sistema

```
┌─────────────────────────────────────────────────────┐
│  VAD = PRODUTOR CONTÍNUO (sempre ouvindo)           │
└─────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
   Wake Word      (futuros         (outros
   Detector       consumers)       consumers)
   
   - Consumidores se inscrevem no ZeroMQ (tcp://vad:5555)
   - VAD publica áudio filtrado continuamente
   - Cada consumidor processa independentemente
```

**Importante:**
- ✅ VAD **NÃO espera** wake word - ele distribui áudio sempre
- ✅ Wake Word **escuta** o stream do VAD e detecta "ASLAM"
- ✅ Após wake word, **mesmo áudio continua fluindo** para Speaker Verification → Whisper
- ✅ VAD é **stateless** - não sabe se wake word foi detectado

---

## 🔮 Arquitetura Futura (ESP32 Satellites)

**Status:** Planejado (Roadmap)
**Objetivo:** Reduzir custo de hardware e distribuir a captura de áudio.

Atualmente, o `audio-capture-vad` roda centralizado no Orange Pi, conectado a um microfone USB de alta qualidade. No futuro, migraremos para uma arquitetura distribuída:

1.  **Satélites ESP32-S3:**
    *   Dispositivos baratos (~$10) espalhados pela casa.
    *   Rodam firmware com **Wake Word Local** (ESP-SR).
    *   Conectados via Wi-Fi (WebRTC/UDP).
    *   Alimentados via USB (tomada).

2.  **Fluxo Híbrido:**
    *   ESP32 detecta "Mordomo" localmente.
    *   ESP32 envia stream de áudio (com buffer de pré-roll de ~1s) para o servidor.
    *   Este container (`audio-capture`) deixa de capturar do USB e passa a atuar como um **Audio Mixer/Gateway**.
    *   Ele recebe N streams, seleciona o melhor (maior SNR/Volume) e injeta no ZeroMQ como se fosse local.

**Por enquanto:** Mantemos a implementação atual (Microfone USB Local) para validar o core do sistema.

---

## 🔧 Tecnologias

**Linguagem:** Python

### Core
- **Sounddevice** - Captura de áudio cross-platform (Python binding para PortAudio C)
- **WebRTC VAD** - Voice Activity Detection (C nativo, wrapper Python)
- **NumPy** - Processamento de arrays (C/Fortran backend via OpenBLAS)

### Opcionais
- **SpeexDSP** - Cancelamento de eco e supressão de ruído (C nativo)
- **PyAudio** - Alternativa ao Sounddevice

**Performance:** Processamento real em **C nativo** (PortAudio, WebRTC, OpenBLAS), Python apenas orquestra o pipeline. Overhead Python ~1-2ms.

---

## 📊 Especificações Técnicas

### Áudio Input
```yaml
Sample Rate: 16000 Hz
Channels: 1 (mono)
Bit Depth: 16-bit
Format: PCM (Linear PCM)
Frame Size: 10-30 ms (160-480 samples @ 16kHz)
Buffer: Circular buffer de 1 segundo
```

### VAD Configuration
```yaml
Mode: Aggressive (3) # 0=Quality, 3=Aggressive
Frame Duration: 30 ms
Threshold: Adaptativo baseado em SNR
Hangover: 300 ms # Continua após silêncio
```

### Performance
```yaml
CPU Usage: < 5% (1 core ARM64)
RAM Usage: ~ 50 MB
Latency: < 10 ms
Throughput: 32 KB/s (16kHz mono 16-bit)
```

---

## 🔌 Interfaces de Comunicação

### Input
```python
# Hardware (fonte única)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
source: /dev/audio ou ALSA device
device_index: 0  # Microfone padrão
```

### Output Principal (ZeroMQ PUB/SUB)
```python
# ZeroMQ PUB Socket - DISTRIBUIDOR DE ÁUDIO

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
endpoint: "tcp://*:5555"
topic: "audio.raw"

# Consumidores conectam via ZeroMQ SUB:

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
# - Wake Word Detector: tcp://audio-capture-vad:5555

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
# - (futuros consumidores podem se inscrever)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---

# Payload Format (publicado a cada 30ms quando VAD ativo)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
{
  "timestamp": 1732723200.123,  # Unix timestamp
  "sample_rate": 16000,
  "channels": 1,
  "format": "int16",
  "data": b"<raw PCM bytes>",  # 480 bytes (30ms @ 16kHz)
  "vad_active": true,           # sempre true (só publica quando ativo)
  "energy": 0.45,               # RMS energy (volume)
  "sequence": 12345             # número sequencial do frame
}
```

### Output Secundário (NATS Events - Metadados)
```python
# Publica quando detecta voz (início de atividade)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
subject: "audio.voice_started"
payload: {
  "timestamp": 1732723200.123,
  "energy": 0.45,
  "device": "microphone_1"
}

# Publica quando silêncio prolongado (fim de atividade)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
subject: "audio.voice_ended"
payload: {
  "timestamp": 1732723202.623,
  "duration": 2.5,  # segundos de voz contínua
  "device": "microphone_1"
}
```

**Nota importante sobre o fluxo:**
- **ZeroMQ** = Canal principal de áudio (alta performance, baixa latência)
- **NATS** = Eventos de metadados (início/fim de voz, erros)

---

## 🏗️ Arquitetura Interna

```
┌─────────────────────────────────────────────┐
│       AUDIO CAPTURE + VAD CONTAINER         │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐                          │
│  │  Microphone  │                          │
│  │   Device     │                          │
│  └──────┬───────┘                          │
│         │                                   │
│         ▼                                   │
│  ┌──────────────┐                          │
│  │   Sounddev   │ ──► Capture Thread       │
│  │   Callback   │     (30ms frames)        │
│  └──────┬───────┘                          │
│         │                                   │
│         ▼                                   │
│  ┌──────────────┐                          │
│  │  AGC (Auto   │ ──► Normalize volume     │
│  │  Gain Ctrl)  │                          │
│  └──────┬───────┘                          │
│         │                                   │
│         ▼                                   │
│  ┌──────────────┐                          │
│  │  AEC (Echo   │ ──► Cancel echo          │
│  │  Canceller)  │                          │
│  └──────┬───────┘                          │
│         │                                   │
│         ▼                                   │
│  ┌──────────────┐                          │
│  │  WebRTC VAD  │ ──► Voice detection      │
│  └──────┬───────┘                          │
│         │                                   │
│    ┌────┴─────┐                            │
│    │          │                             │
│    ▼          ▼                             │
│  Voice      Silence                         │
│    │          │                             │
│    │          └──► Discard                  │
│    │                                        │
│    ▼                                        │
│  ┌──────────────┐                          │
│  │  ZeroMQ PUB  │ ──► Send to Wake Word    │
│  │   Publisher  │                          │
│  └──────────────┘                          │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📦 Dependências

### Python Packages
```txt
sounddevice==0.4.6
webrtcvad==2.0.10
numpy==1.24.3
pyzmq==25.1.1
pynats==1.1.0
```

### System Libraries
```bash
# Debian/Ubuntu

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
apt-get install -y \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2

# Alpine (Docker)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
apk add --no-cache \
    alsa-lib-dev \
    portaudio-dev
```

---

## 🐳 Dockerfile

```dockerfile
FROM python:3.11-slim

# System dependencies

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
RUN apt-get update && apt-get install -y \
    libasound2-dev \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
COPY src/ ./src/
COPY config/ ./config/

# Expose metrics

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
EXPOSE 8000

# Run

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
CMD ["python", "src/main.py"]
```

---

## ⚙️ Configuração

### Environment Variables
```bash
# Dispositivo de áudio

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
AUDIO_DEVICE_INDEX=0
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1

# VAD

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
VAD_MODE=3  # 0-3 (3 = most aggressive)
VAD_FRAME_DURATION_MS=30

# AEC (Echo Cancellation)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
AEC_ENABLED=true
AEC_FILTER_LENGTH=512

# AGC (Auto Gain Control)

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
AGC_ENABLED=true
AGC_TARGET_LEVEL=3

# ZeroMQ

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
ZMQ_PUB_ENDPOINT=tcp://*:5555

# NATS

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
NATS_URL=nats://event-bus-nats:4222

# Logging

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
LOG_LEVEL=INFO
METRICS_PORT=8000
```

### Config File (config/audio.yaml)
```yaml
audio:
  device:
    index: 0
    name: "default"
  
  capture:
    sample_rate: 16000
    channels: 1
    dtype: int16
    frames_per_buffer: 480  # 30ms
    
  vad:
    mode: 3
    frame_duration_ms: 30
    threshold_db: -40
    hangover_ms: 300
    
  processing:
    agc:
      enabled: true
      target_level_dbfs: -3
      compression_gain_db: 9
    
    aec:
      enabled: true
      filter_length: 512
      echo_path_delay_ms: 50

output:
  zeromq:
    endpoint: "tcp://*:5555"
    topic: "audio.raw"
  
  nats:
    url: "nats://event-bus-nats:4222"
    subjects:
      voice_detected: "audio.voice_detected"
      silence: "audio.silence"
```

---

## 📈 Métricas Prometheus

```python
# Expostas em :8000/metrics

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---

# Contadores

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
audio_frames_captured_total
audio_frames_voice_total
audio_frames_silence_total
audio_capture_errors_total

# Gauges

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
audio_energy_current  # RMS atual
audio_snr_db  # Signal-to-noise ratio
audio_device_status  # 1=ok, 0=error

# Histogramas

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
audio_processing_latency_seconds
audio_frame_energy_distribution
```

---

## 🔍 Logs

### Formato
```json
{
  "timestamp": "2025-11-27T10:30:45.123Z",
  "level": "INFO",
  "container": "audio-capture-vad",
  "message": "Voice activity detected",
  "metadata": {
    "energy": 0.45,
    "duration_ms": 1500,
    "vad_confidence": 0.92
  }
}
```

### Níveis
```
DEBUG: Frame-by-frame processing details
INFO: Voice detection, device changes
WARNING: Low SNR, clipping detected
ERROR: Device errors, buffer overflow
CRITICAL: Complete audio failure
```

---

## 🧪 Testes

### Unit Tests
```python
# test_vad.py

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
def test_vad_detects_voice():
    # Testa detecção com sample de voz
    
def test_vad_ignores_silence():
    # Testa filtro de silêncio
    
def test_agc_normalizes_volume():
    # Testa normalização automática
```

### Integration Tests
```python
# test_integration.py

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
def test_publishes_to_zeromq():
    # Testa publicação ZeroMQ
    
def test_publishes_events_to_nats():
    # Testa eventos NATS
```

---

## 🚀 Deploy

### Docker Compose
```yaml
audio-capture-vad:
  build: ./containers/audio-capture-vad
  container_name: audio-capture-vad
  devices:
    - /dev/snd:/dev/snd  # ALSA device
  environment:
    - AUDIO_DEVICE_INDEX=0
    - VAD_MODE=3
    - NATS_URL=nats://event-bus-nats:4222
  ports:
    - "5555:5555"  # ZeroMQ
    - "8000:8000"  # Metrics
  networks:
    - mordomo-net
  restart: unless-stopped
```

---

## 🔧 Troubleshooting

### Problema: Áudio não captura
```bash
# Verificar dispositivos disponíveis

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
python -c "import sounddevice; print(sounddevice.query_devices())"

# Testar captura manual

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
arecord -l
```

### Problema: VAD muito sensível
```yaml
# Ajustar modo VAD

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
VAD_MODE=2  # Menos agressivo
VAD_THRESHOLD_DB=-35  # Threshold mais alto
```

### Problema: Eco não cancela
```yaml
# Aumentar filter length

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-audio-capture-vad**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-system-watchdog](https://github.com/AslamSys/mordomo-system-watchdog)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---
AEC_FILTER_LENGTH=1024
AEC_ECHO_PATH_DELAY_MS=100
```

---

## 📊 SLA e Performance

```yaml
Target Metrics:
  Uptime: 99.9%
  Latency: < 10ms
  CPU Usage: < 5%
  RAM Usage: < 100MB
  
Alerts:
  - audio_device_status == 0  # Dispositivo offline
  - audio_processing_latency_seconds > 0.050  # Latência alta
  - audio_capture_errors_total rate > 10/min  # Muitos erros
```

---

## 🔗 Integração com Outros Containers

### Downstream (Envia para)
- **Wake Word Detector** - Via ZeroMQ (áudio raw)
- **Event Bus (NATS)** - Eventos de voz detectada

### Upstream (Recebe de)
- Nenhum (primeiro container no pipeline)

### Monitoring
- **Prometheus** - Scrape de métricas em :8000/metrics
- **Loki** - Logs via Docker log driver

---

## 📝 Checklist de Implementação

- [ ] Configurar dispositivo de áudio ALSA/PortAudio
- [ ] Implementar callback de captura contínua
- [ ] Integrar WebRTC VAD
- [ ] Adicionar AGC (Auto Gain Control)
- [ ] Implementar AEC (Echo Cancellation)
- [ ] Configurar publisher ZeroMQ
- [ ] Integrar eventos NATS
- [ ] Expor métricas Prometheus
- [ ] Configurar logs estruturados
- [ ] Testes unitários e integração
- [ ] Dockerfile otimizado
- [ ] Health checks
- [ ] Documentação de troubleshooting

---

**Versão:** 1.0  
**Última atualização:** 27/11/2025
