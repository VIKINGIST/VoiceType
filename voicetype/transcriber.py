"""Транскрибація аудіо через faster-whisper (CTranslate2, без torch)."""

from __future__ import annotations

import gc
import logging
import time

import numpy as np
from faster_whisper import WhisperModel

from voicetype.config import Config

log = logging.getLogger("voicetype")

# RMS нормалізація: цільовий рівень гучності
_TARGET_RMS = 0.1
_MIN_RMS = 1e-6  # поріг тиші — не нормалізувати шум


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """RMS нормалізація аудіо до цільового рівня."""
    rms = np.sqrt(np.mean(audio ** 2))
    if rms < _MIN_RMS:
        return audio
    gain = _TARGET_RMS / rms
    # Обмежити підсилення (макс 10x) щоб не роздувати шум
    gain = min(gain, 10.0)
    normalized = audio * gain
    # Clamp до [-1, 1]
    return np.clip(normalized, -1.0, 1.0)


class Transcriber:
    """Обгортка над faster-whisper — завантажує модель один раз, транскрибує багато."""

    def __init__(self, config: Config):
        self.config = config
        self._model: WhisperModel | None = None
        self.last_used: float = 0.0  # timestamp останнього використання

    def load_model(self) -> None:
        """Завантажити модель в GPU/CPU. Викликається один раз при старті."""
        device = "cuda" if self.config.device >= 0 else "cpu"
        device_index = self.config.device if device == "cuda" else 0
        compute = "float16" if device == "cuda" else "int8"

        log.info(
            "Loading Whisper model=%s device=%s compute=%s",
            self.config.model, device, compute,
        )

        self._model = WhisperModel(
            self.config.model,
            device=device,
            device_index=device_index,
            compute_type=compute,
        )
        self.last_used = time.time()
        log.info("Model loaded successfully")

    def unload_model(self) -> None:
        """Вивантажити модель з пам'яті (VRAM/RAM)."""
        if self._model is None:
            return
        log.info("Unloading Whisper model (idle timeout)")
        del self._model
        self._model = None
        gc.collect()
        log.info("Model unloaded, memory freed")

    def transcribe(self, audio: np.ndarray, task: str = "transcribe") -> str:
        """Розпізнати аудіо масив (float32, 16kHz, mono). Повертає текст."""
        if self._model is None:
            raise RuntimeError("Модель не завантажена. Викличте load_model() спершу.")

        if len(audio) == 0:
            return ""

        # RMS нормалізація
        audio = normalize_audio(audio)

        language = None if self.config.language == "auto" else self.config.language

        # Whisper native translate: task="translate" перекладає на англійську без API
        if task == "translate" and "turbo" in self.config.model:
            log.warning("Native translate with turbo model may be inaccurate. Use medium/large-v3 for better results.")

        segments, info = self._model.transcribe(
            audio,
            language=language,
            task=task,
            beam_size=5,
            vad_filter=False,  # VAD вже зроблено на етапі запису
        )

        text = " ".join(seg.text.strip() for seg in segments)
        self.last_used = time.time()
        return text.strip()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None
