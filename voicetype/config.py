"""Завантаження та управління конфігурацією VoiceType."""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
import yaml


def _app_dir() -> Path:
    """Кореневий каталог додатку — працює і з PyInstaller, і без."""
    if getattr(sys, "frozen", False):
        # PyInstaller EXE — config поруч з exe
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


CONFIG_PATH = _app_dir() / "config.yaml"

RECORDING_MODES = {
    "auto": "Автоматичний — натиснув, говориш, тиша → стоп",
    "hold": "Утримання — тримаєш клавішу = запис, відпустив → стоп",
    "toggle": "Перемикач — натиснув = старт, натиснув ще раз = стоп",
}

UI_LANGUAGES = {
    "uk": "Українська",
    "en": "English",
    "de": "Deutsch",
    "pl": "Polski",
    "fr": "Français",
    "es": "Español",
}

DEFAULTS = {
    "hotkey": "alt+q",
    "recording_mode": "auto",
    "ui_language": "en",
    "language": "auto",
    "model": "large-v3-turbo",
    "device": 0,
    "compute_type": "float16",
    "sample_rate": 16000,
    "channels": 1,
    "vad_threshold": 0.5,
    "silence_duration": 2.0,
    "max_recording": 0,
    "auto_paste": True,
    "copy_to_clipboard": True,
    "show_notification": True,
    "notification_duration": 3,
    "sound_on_start": True,
    "sound_on_stop": True,
    "start_minimized": True,
    "model_idle_timeout": 5,
    "deepseek_api_key": "",
    "translate_to": "",
    "translate_hotkey": "",
    "custom_prompt": "",
    "active_filters": [],
    "llm_provider": "deepseek",
    "openrouter_api_key": "",
}

# Мови для перекладу через LLM (окремо від мови розпізнавання)
TRANSLATE_LANGUAGES = {
    "": "— вимкнено —",
    "English (Whisper)": "English (native, no API)",
    # ── Основні ──
    "English": "English",
    "Ukrainian": "Українська",
    "German": "Deutsch",
    "French": "Français",
    "Spanish": "Español",
    "Polish": "Polski",
    "Italian": "Italiano",
    "Portuguese": "Português",
    # ── Азія ──
    "Chinese": "中文",
    "Japanese": "日本語",
    "Korean": "한국어",
    "Hindi": "हिन्दी",
    "Thai": "ไทย",
    "Vietnamese": "Tiếng Việt",
    "Indonesian": "Bahasa Indonesia",
    "Malay": "Bahasa Melayu",
    # ── Європа ──
    "Dutch": "Nederlands",
    "Swedish": "Svenska",
    "Norwegian": "Norsk",
    "Danish": "Dansk",
    "Finnish": "Suomi",
    "Czech": "Čeština",
    "Slovak": "Slovenčina",
    "Romanian": "Română",
    "Hungarian": "Magyar",
    "Bulgarian": "Български",
    "Croatian": "Hrvatski",
    "Greek": "Ελληνικά",
    "Turkish": "Türkçe",
    # ── Інші ──
    "Arabic": "العربية",
    "Hebrew": "עברית",
    "Persian": "فارسی",
    "Russian": "Русский",
}

LANGUAGES = {
    "auto": "Auto-detect",
    # ── Основні ──
    "uk": "Українська",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "pl": "Polski",
    "it": "Italiano",
    "pt": "Português",
    # ── Азія ──
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "hi": "हिन्दी",
    "th": "ไทย",
    "vi": "Tiếng Việt",
    "id": "Bahasa Indonesia",
    "ms": "Bahasa Melayu",
    # ── Європа ──
    "nl": "Nederlands",
    "sv": "Svenska",
    "no": "Norsk",
    "da": "Dansk",
    "fi": "Suomi",
    "cs": "Čeština",
    "sk": "Slovenčina",
    "ro": "Română",
    "hu": "Magyar",
    "bg": "Български",
    "hr": "Hrvatski",
    "el": "Ελληνικά",
    "tr": "Türkçe",
    # ── Інші ──
    "ar": "العربية",
    "he": "עברית",
    "fa": "فارسی",
    "ru": "Русский",
}

MODELS = {
    "large-v3-turbo": "large-v3-turbo",
    "large-v3": "large-v3",
    "medium": "medium",
    "small": "small",
    "base": "base",
}

MODEL_INFO = {
    "large-v3-turbo": {"vram": "~1.6 GB", "speed": "~0.2s / 10s"},
    "large-v3": {"vram": "~3.0 GB", "speed": "~1.0s / 10s"},
    "medium": {"vram": "~1.0 GB", "speed": "~0.1s / 10s"},
    "small": {"vram": "~0.5 GB", "speed": "~0.05s / 10s"},
    "base": {"vram": "~0.15 GB", "speed": "~0.02s / 10s"},
}

COMPUTE_TYPES = ["float16", "int8_float16", "int8", "float32"]

LLM_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "default_model": "deepseek-chat",
        "register_url": "https://platform.deepseek.com",
        "key_placeholder": "sk-...",
    },
    "openrouter": {
        "name": "OpenRouter",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "openai/gpt-4o-mini",
        "register_url": "https://openrouter.ai",
        "key_placeholder": "sk-or-...",
    },
}


@dataclass
class Config:
    hotkey: str = "alt+q"
    recording_mode: str = "auto"
    ui_language: str = "en"
    language: str = "auto"
    model: str = "large-v3-turbo"
    device: int = 0
    compute_type: str = "float16"
    sample_rate: int = 16000
    channels: int = 1
    vad_threshold: float = 0.5
    silence_duration: float = 2.0
    max_recording: int = 0
    auto_paste: bool = True
    copy_to_clipboard: bool = True
    show_notification: bool = True
    notification_duration: int = 3
    sound_on_start: bool = True
    sound_on_stop: bool = True
    start_minimized: bool = True
    model_idle_timeout: int = 5  # хвилин, 0 = вимкнено
    deepseek_api_key: str = ""
    translate_to: str = ""
    translate_hotkey: str = ""  # хоткей для перекладу, "" = вимкнено
    custom_prompt: str = ""
    active_filters: list = field(default_factory=list)
    llm_provider: str = "deepseek"  # "deepseek" | "openrouter"
    openrouter_api_key: str = ""

    def save(self, path: Path | None = None) -> None:
        p = path or CONFIG_PATH
        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(asdict(self), f, default_flow_style=False, allow_unicode=True)

    # Маппінг старих назв → актуальні (зворотна сумісність)
    _MODEL_ALIASES = {
        "turbo": "large-v3-turbo",
    }

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        p = path or CONFIG_PATH
        merged = dict(DEFAULTS)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            merged.update(data)
        if merged.get("model") in cls._MODEL_ALIASES:
            merged["model"] = cls._MODEL_ALIASES[merged["model"]]
        return cls(**{k: v for k, v in merged.items() if k in cls.__dataclass_fields__})
