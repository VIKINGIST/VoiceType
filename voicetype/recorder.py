"""Запис аудіо з мікрофона через sounddevice."""

from __future__ import annotations

import threading
from typing import Callable

import numpy as np
import sounddevice as sd

from voicetype.config import Config


class AudioRecorder:
    """Записує аудіо з мікрофона в ring buffer, зупиняється через event."""

    def __init__(self, config: Config, on_chunk: Callable | None = None):
        self.config = config
        self.on_chunk = on_chunk  # callback(chunk: np.ndarray) для VAD
        self._buffer: list[np.ndarray] = []
        self._stop_event = threading.Event()
        self._stream: sd.InputStream | None = None

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            print(f"[AUDIO] {status}")
        chunk = indata[:, 0].copy()
        self._buffer.append(chunk)
        if self.on_chunk:
            self.on_chunk(chunk)
        if self._stop_event.is_set():
            raise sd.CallbackStop()

    def start(self) -> None:
        """Почати запис. Неблокуючий — працює у фоновому потоці sounddevice."""
        self._buffer.clear()
        self._stop_event.clear()
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype="float32",
            blocksize=576,  # 36ms при 16kHz — розмір вікна sherpa-onnx Silero VAD
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Зупинити запис, повернути конкатенований аудіо масив."""
        self._stop_event.set()
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._buffer:
            return np.concatenate(self._buffer)
        return np.array([], dtype=np.float32)

    @property
    def is_recording(self) -> bool:
        return self._stream is not None and self._stream.active

    @staticmethod
    def list_devices() -> list[dict]:
        """Список доступних аудіо-пристроїв вводу."""
        devices = sd.query_devices()
        result = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                result.append({"index": i, "name": d["name"], "channels": d["max_input_channels"]})
        return result
