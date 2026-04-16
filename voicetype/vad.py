"""Voice Activity Detection через Silero VAD (sherpa-onnx ONNX runtime)."""

import logging
from pathlib import Path

import numpy as np
import sherpa_onnx

from voicetype.config import _app_dir

log = logging.getLogger("voicetype")

# Шлях до Silero VAD ONNX моделі
_VAD_MODEL_PATH = _app_dir() / "models" / "silero-vad" / "silero_vad.onnx"


def _ensure_vad_model() -> Path:
    """Перевірити наявність VAD моделі, завантажити якщо потрібно."""
    if _VAD_MODEL_PATH.exists():
        return _VAD_MODEL_PATH

    log.info("Downloading Silero VAD model...")
    _VAD_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import hf_hub_download
    hf_hub_download(
        repo_id="deepghs/silero-vad-onnx",
        filename="silero_vad.onnx",
        local_dir=str(_VAD_MODEL_PATH.parent),
    )
    log.info("Silero VAD model downloaded to %s", _VAD_MODEL_PATH)
    return _VAD_MODEL_PATH


class VoiceActivityDetector:
    """Silero VAD через sherpa-onnx — визначає наявність мовлення."""

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate

        model_path = _ensure_vad_model()

        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(model_path)
        config.silero_vad.threshold = threshold
        config.silero_vad.min_silence_duration = 0.5
        config.silero_vad.min_speech_duration = 0.25
        config.sample_rate = sample_rate
        config.num_threads = 2

        self._model = sherpa_onnx.VadModel.create(config)
        self._window_size = self._model.window_size()

    @property
    def window_size(self) -> int:
        """Розмір чанку для VAD (samples)."""
        return self._window_size

    def is_speech(self, chunk: np.ndarray) -> bool:
        """Перевірити чи є мовлення в чанку."""
        return self._model.is_speech(chunk.tolist())

    def reset(self) -> None:
        """Скинути внутрішній стан моделі між записами."""
        self._model.reset()


class SilenceTracker:
    """Трекер тиші — рахує послідовні тихі фрейми для авто-стопу."""

    def __init__(
        self,
        vad: VoiceActivityDetector,
        silence_duration: float = 2.0,
        sample_rate: int = 16000,
        chunk_size: int | None = None,
    ):
        self.vad = vad
        # Використовуємо window_size з VAD моделі якщо chunk_size не заданий
        actual_chunk = chunk_size or vad.window_size
        self._frames_for_silence = int(silence_duration * sample_rate / actual_chunk)
        self._silent_frames = 0
        self._speech_started = False

    def process_chunk(self, chunk: np.ndarray) -> bool:
        """Обробити чанк. Повертає True якщо потрібно зупинити запис."""
        if self.vad.is_speech(chunk):
            self._speech_started = True
            self._silent_frames = 0
            return False

        if self._speech_started:
            self._silent_frames += 1
            return self._silent_frames >= self._frames_for_silence

        return False

    def reset(self) -> None:
        """Скинути трекер для нового запису."""
        self._silent_frames = 0
        self._speech_started = False
        self.vad.reset()
