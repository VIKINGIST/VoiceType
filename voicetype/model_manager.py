"""Завантаження та кеш-менеджмент Whisper моделей (faster-whisper CTranslate2)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

log = logging.getLogger("voicetype")


# ── HuggingFace cache ────────────────────────────────────────

def _hf_cache_dir() -> Path:
    """Директорія кешу HuggingFace."""
    try:
        from huggingface_hub.constants import HF_HUB_CACHE
        return Path(HF_HUB_CACHE)
    except Exception:
        return Path.home() / ".cache" / "huggingface" / "hub"


# ── Реєстр моделей ──────────────────────────────────────────

# Fallback маппінг (якщо faster-whisper не доступний)
_FALLBACK_REPOS: dict[str, str] = {
    "large-v3-turbo": "Systran/faster-whisper-large-v3-turbo",
    "large-v3": "Systran/faster-whisper-large-v3",
    "medium": "Systran/faster-whisper-medium",
    "small": "Systran/faster-whisper-small",
    "base": "Systran/faster-whisper-base",
    "tiny": "Systran/faster-whisper-tiny",
}

# Приблизні розміри моделей (MB)
_MODEL_SIZES_MB: dict[str, int] = {
    "large-v3-turbo": 1600,
    "large-v3": 3100,
    "medium": 1500,
    "small": 500,
    "base": 150,
    "tiny": 80,
}


def _get_repo(model_name: str) -> str:
    """HuggingFace repo ID — використовуємо маппінг faster-whisper."""
    try:
        from faster_whisper.utils import _MODELS
        repo = _MODELS.get(model_name)
        if repo:
            return repo
    except Exception:
        pass
    return _FALLBACK_REPOS.get(model_name, f"Systran/faster-whisper-{model_name}")


def is_model_cached(model_name: str) -> bool:
    """Перевірити чи модель завантажена в HF кеш."""
    cache_dir = _hf_cache_dir()
    if not cache_dir.exists():
        return False

    repo_id = _get_repo(model_name)
    safe_name = f"models--{repo_id.replace('/', '--')}"
    model_dir = cache_dir / safe_name / "snapshots"
    if not model_dir.exists():
        return False

    for snap in model_dir.iterdir():
        if (snap / "model.bin").exists():
            return True
    return False


def get_model_size_mb(model_name: str) -> int:
    """Приблизний розмір моделі в MB."""
    return _MODEL_SIZES_MB.get(model_name, 500)


# ── Прогрес ──────────────────────────────────────────────────

@dataclass
class DownloadProgress:
    """Стан завантаження для callback."""
    percent: float = 0.0
    speed_mbps: float = 0.0
    downloaded_mb: float = 0.0
    total_mb: float = 0.0
    eta_seconds: int = 0

    @property
    def eta_str(self) -> str:
        if self.eta_seconds <= 0:
            return "--:--"
        m, s = divmod(self.eta_seconds, 60)
        if m >= 60:
            h, m = divmod(m, 60)
            return f"{h}h {m:02d}m"
        return f"{m}:{s:02d}"

    @property
    def speed_str(self) -> str:
        if self.speed_mbps >= 1:
            return f"{self.speed_mbps:.1f} MB/s"
        if self.speed_mbps > 0:
            return f"{self.speed_mbps * 1024:.0f} KB/s"
        return "..."


# ── Завантаження ─────────────────────────────────────────────

class _DownloadCancelled(Exception):
    pass


def download_model(
    model_name: str,
    on_progress: Callable[[DownloadProgress], None] | None = None,
    errors: list | None = None,
    cancel_event: "threading.Event | None" = None,
) -> str | None:
    """Завантажити модель з HuggingFace.

    Повертає локальний шлях або None при помилці/скасуванні.
    """
    from faster_whisper.utils import download_model as fw_download
    import time as _time

    repo_id = _get_repo(model_name)
    total_mb = get_model_size_mb(model_name)
    expected_bytes = total_mb * 1024 * 1024
    log.info("Downloading model %s from %s (~%d MB)...", model_name, repo_id, total_mb)

    cache_dir = _hf_cache_dir()
    model_cache = cache_dir / f"models--{repo_id.replace('/', '--')}"

    # Xet cache (HuggingFace Xet transport)
    try:
        from huggingface_hub.constants import HF_HOME as _HF_HOME
        xet_cache = Path(_HF_HOME) / "xet"
    except Exception:
        xet_cache = Path.home() / ".cache" / "huggingface" / "xet"

    stop_monitor = threading.Event()

    def _disk_bytes(*dirs: Path) -> int:
        total = 0
        for d in dirs:
            try:
                if d.exists():
                    total += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            except Exception:
                pass
        return total

    def _monitor():
        start_time = _time.time()
        start_size = _disk_bytes(model_cache, xet_cache)
        while not stop_monitor.is_set():
            stop_monitor.wait(1.5)
            if stop_monitor.is_set():
                break
            if cancel_event and cancel_event.is_set():
                break
            current = _disk_bytes(model_cache, xet_cache)
            downloaded = max(current - start_size, 0)
            elapsed = _time.time() - start_time
            pct = min(downloaded / expected_bytes, 0.99) if expected_bytes > 0 else 0
            speed = downloaded / elapsed / (1024 * 1024) if elapsed > 1 else 0
            remaining = expected_bytes - downloaded
            eta = int(remaining / (downloaded / elapsed)) if downloaded > 0 and elapsed > 1 else 0
            if on_progress:
                on_progress(DownloadProgress(
                    percent=pct, speed_mbps=speed,
                    downloaded_mb=downloaded / (1024 * 1024),
                    total_mb=total_mb,
                    eta_seconds=eta,
                ))

    threading.Thread(target=_monitor, daemon=True).start()

    try:
        if cancel_event and cancel_event.is_set():
            raise _DownloadCancelled()
        local_path = fw_download(model_name)
        stop_monitor.set()
        if cancel_event and cancel_event.is_set():
            raise _DownloadCancelled()
        if on_progress:
            on_progress(DownloadProgress(
                percent=1.0, speed_mbps=0,
                downloaded_mb=total_mb, total_mb=total_mb,
                eta_seconds=0,
            ))
        log.info("Model downloaded to %s", local_path)
        return local_path

    except _DownloadCancelled:
        stop_monitor.set()
        log.info("Download cancelled for %s", model_name)
        return None

    except Exception as e:
        stop_monitor.set()
        log.error("Download failed for %s: %s", model_name, e)
        if errors is not None:
            errors.append(str(e))
        return None


# ── Список та видалення ──────────────────────────────────────

def list_cached_models() -> list[dict]:
    """Список завантажених моделей з розмірами."""
    cache_dir = _hf_cache_dir()
    if not cache_dir.exists():
        return []

    result = []
    for short_name in _FALLBACK_REPOS:
        repo_id = _get_repo(short_name)
        safe_name = f"models--{repo_id.replace('/', '--')}"
        model_dir = cache_dir / safe_name
        if not model_dir.exists():
            continue
        snapshots = model_dir / "snapshots"
        if not snapshots.exists():
            continue
        has_model = any((snap / "model.bin").exists() for snap in snapshots.iterdir())
        if not has_model:
            continue
        try:
            total = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
            size_mb = round(total / (1024 * 1024))
        except Exception:
            size_mb = 0
        if size_mb > 1:
            result.append({
                "name": short_name,
                "size_mb": size_mb,
                "path": model_dir,
            })

    return sorted(result, key=lambda m: m["name"])


def delete_model(model_path: Path) -> bool:
    """Видалити модель з кешу."""
    import shutil
    try:
        shutil.rmtree(model_path)
        log.info("Deleted model cache: %s", model_path)
        return True
    except Exception as e:
        log.error("Failed to delete model: %s", e)
        return False
