"""VoiceType — локальний голосовий ввід для Windows.

Точка входу: трей-іконка, глобальний хоткей, orchestration запис→розпізнавання→вставка.
"""

from __future__ import annotations

import os
import sys

# CUDA DLLs: nvidia пакети ставлять DLL в site-packages/nvidia/*/bin/
# Потрібно додати в PATH ДО імпорту ctranslate2/faster-whisper
_nvidia_base = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
if os.path.isdir(_nvidia_base):
    for _d in os.listdir(_nvidia_base):
        _bin = os.path.join(_nvidia_base, _d, "bin")
        if os.path.isdir(_bin):
            os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")

import logging
import threading
import queue
import time
from pathlib import Path
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw
import keyboard
import pystray

# ─── Logging ─────────────────────────────────────────────────

from voicetype.config import _app_dir
LOG_DIR = _app_dir() / "logs"
LOG_DIR.mkdir(exist_ok=True)

_log_file = LOG_DIR / "voicetype.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
log = logging.getLogger("voicetype")

# pythonw.exe не має stdout/stderr — перенаправити в лог-файл
# інакше будь-який print/warning від бібліотек падає з NoneType.write
if sys.stdout is None or sys.stderr is None:
    _devnull = open(_log_file, "a", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _devnull
    if sys.stderr is None:
        sys.stderr = _devnull

from voicetype.config import Config
from voicetype.i18n import t, set_language
from voicetype.recorder import AudioRecorder
from voicetype.vad import VoiceActivityDetector, SilenceTracker
from voicetype.transcriber import Transcriber
from voicetype.input_handler import paste_text
from voicetype.notifier import notify, beep_start, beep_stop
from voicetype.postprocessor import PostProcessor
from voicetype.settings_window import SettingsWindow


# ─── Tray icons ──────────────────────────────────────────────

def _make_icon(circle_color: str, mic_color: str = "white", size: int = 64) -> Image.Image:
    """Створити іконку мікрофона з прозорим фоном для Windows tray."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 2
    # Кольорове коло
    draw.ellipse([margin, margin, size - margin, size - margin], fill=circle_color)
    # Мікрофон
    cx, cy = size // 2, size // 2
    # Головка мікрофона (округлий верх)
    draw.rounded_rectangle([cx - 5, cy - 15, cx + 5, cy + 1], radius=5, fill=mic_color)
    # Дуга-тримач
    draw.arc([cx - 11, cy - 6, cx + 11, cy + 8], start=0, end=180, fill=mic_color, width=2)
    # Ніжка
    draw.line([cx, cy + 8, cx, cy + 14], fill=mic_color, width=2)
    # Підставка
    draw.line([cx - 6, cy + 14, cx + 6, cy + 14], fill=mic_color, width=2)
    return img


ICON_IDLE = _make_icon("#45475a")
ICON_LOADING = _make_icon("#f9e2af", "#1e1e2e")
ICON_RECORDING = _make_icon("#f38ba8")
ICON_PROCESSING = _make_icon("#89b4fa")


# ─── App ─────────────────────────────────────────────────────

class VoiceTypeApp:
    """Головний клас додатку."""

    def __init__(self):
        self.config = Config.load()
        set_language(self.config.ui_language)
        self._command_queue: queue.Queue = queue.Queue()
        self._is_recording = False
        self._tray: pystray.Icon | None = None
        self._hotkey_listener = None
        self._settings_proc = None
        self._recorder: AudioRecorder | None = None
        self._vad: VoiceActivityDetector | None = None
        self._silence_tracker: SilenceTracker | None = None
        self._transcriber: Transcriber | None = None
        self._postprocessor: PostProcessor | None = None
        self._worker_thread: threading.Thread | None = None
        self._max_timer: threading.Timer | None = None
        self._translate_mode = False  # True коли запис через translate hotkey
        self._held_key = None  # blocked key during hold recording

    def run(self) -> None:
        """Запустити додаток."""
        # Встановити AppUserModelID для всього процесу — іконка в taskbar
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("voicetype.app")
        log.info("VoiceType starting...")
        # Worker thread для обробки команд
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        # Завантаження моделей у фоні
        self._command_queue.put(("init", None))

        # Tray menu (dynamic — re-evaluated on each open for translate submenu)
        self._tray = pystray.Icon(
            "voicetype", ICON_LOADING, t("tray.loading"),
            menu=pystray.Menu(lambda: self._build_tray_menu_items()),
        )
        self._tray.run(setup=self._on_tray_ready)

    def _on_tray_ready(self, icon: pystray.Icon) -> None:
        """Callback після створення трей-іконки — запуск хоткея."""
        icon.visible = True
        self._start_hotkey_listener()

    def _start_hotkey_listener(self) -> None:
        """Запустити (або перезапустити) глобальний хоткей."""
        keyboard.unhook_all()
        mode = self.config.recording_mode

        if mode == "hold":
            keyboard.add_hotkey(
                self.config.hotkey, self._on_hotkey_down, suppress=True, trigger_on_release=False
            )
            last_key = self.config.hotkey.split("+")[-1].strip()
            keyboard.on_release_key(last_key, self._on_hotkey_up, suppress=True)
        else:
            keyboard.add_hotkey(
                self.config.hotkey, self._on_hotkey_toggle, suppress=True
            )

        # Translate hotkey (тільки якщо обробка має сенс)
        if self.config.translate_hotkey and self._is_processing_useful():
            if mode == "hold":
                keyboard.add_hotkey(
                    self.config.translate_hotkey,
                    lambda: self._on_hotkey_down(translate=True),
                    suppress=True, trigger_on_release=False,
                )
                last_key_t = self.config.translate_hotkey.split("+")[-1].strip()
                keyboard.on_release_key(last_key_t, lambda e=None: self._on_hotkey_up(e, translate=True), suppress=True)
            else:
                keyboard.add_hotkey(
                    self.config.translate_hotkey,
                    lambda: self._on_hotkey_toggle(translate=True),
                    suppress=True,
                )

    def _is_processing_useful(self) -> bool:
        """True якщо translate_hotkey дійсно щось зробить."""
        cfg = self.config
        # Whisper native translate — no API needed
        if cfg.translate_to == "English (Whisper)":
            return True
        # LLM features need API key + at least one feature enabled
        provider = getattr(cfg, "llm_provider", "deepseek")
        api_key = (
            getattr(cfg, "openrouter_api_key", "")
            if provider == "openrouter"
            else cfg.deepseek_api_key
        )
        has_feature = bool(cfg.translate_to) or bool(cfg.custom_prompt) or bool(cfg.active_filters)
        return bool(api_key) and has_feature

    def _on_hotkey_toggle(self, translate: bool = False) -> None:
        """Режим auto/toggle — натиснув = toggle запису."""
        if self._is_recording:
            self._command_queue.put(("stop_recording", None))
        else:
            self._command_queue.put(("start_recording", {"translate": translate}))

    def _on_hotkey_down(self, translate: bool = False) -> None:
        """Режим hold — натиснув = старт."""
        if not self._is_recording:
            self._command_queue.put(("start_recording", {"translate": translate}))

    def _on_hotkey_up(self, event=None, translate: bool = False) -> None:
        """Режим hold — відпустив = стоп."""
        if self._is_recording:
            self._command_queue.put(("stop_recording", None))

    # ─── Worker loop ─────────────────────────────────────────

    def _worker_loop(self) -> None:
        """Головний цикл обробки команд (окремий потік)."""
        config_check_counter = 0
        idle_check_counter = 0
        while True:
            try:
                cmd, data = self._command_queue.get(timeout=1.0)
            except queue.Empty:
                # Кожні ~3с перевіряти чи конфіг змінився (settings — окремий процес)
                config_check_counter += 1
                if config_check_counter >= 3:
                    config_check_counter = 0
                    self._check_config_change()

                # Кожні ~10с перевіряти idle timeout моделі
                idle_check_counter += 1
                if idle_check_counter >= 10:
                    idle_check_counter = 0
                    self._check_model_idle()
                continue

            if cmd == "init":
                self._do_init()
            elif cmd == "start_recording":
                self._do_start_recording(data)
            elif cmd == "stop_recording":
                self._do_stop_recording()
            elif cmd == "vad_stop":
                self._do_stop_recording()
            elif cmd == "max_timeout":
                self._do_stop_recording()
            elif cmd == "processing_done":
                self._on_processing_done(data)
            elif cmd == "quit":
                break

    def _do_init(self) -> None:
        """Ініціалізація моделей (VAD + Whisper)."""
        from voicetype.model_manager import is_model_cached, download_model, get_model_size_mb

        log.info("Initializing models...")

        # Перевірити чи модель в кеші — якщо ні, запитати користувача
        if not is_model_cached(self.config.model):
            import ctypes
            size_mb = get_model_size_mb(self.config.model)
            result = ctypes.windll.user32.MessageBoxW(
                0,
                t("notify.download_prompt", model=self.config.model, size=f"~{size_mb / 1000:.1f} GB"),
                "VoiceType",
                0x04 | 0x40  # MB_YESNO | MB_ICONINFORMATION
            )
            if result != 6:  # Не Yes — запустити без моделі
                self._set_tray(t("tray.ready", hotkey=self.config.hotkey), ICON_IDLE)
                return

            # Yes — завантажити з прогресом в треї
            def on_progress(p) -> None:
                if p.percent < 1.0:
                    self._set_tray(
                        f"⬇ {self.config.model}  {p.percent:.0%}  "
                        f"{p.speed_str}  ETA {p.eta_str}  "
                        f"({p.downloaded_mb:.0f}/{p.total_mb:.0f} MB)",
                        ICON_LOADING,
                    )
                else:
                    self._set_tray(t("notify.loading_whisper"), ICON_LOADING)

            result_path = download_model(self.config.model, on_progress=on_progress)
            if result_path is None:
                notify(t("notify.error_title"), t("notify.whisper_failed", error="Download failed"))
                self._set_tray(t("tray.error_whisper"), ICON_IDLE)
                return

        # VAD
        self._set_tray(t("notify.loading_vad"), ICON_LOADING)

        try:
            self._vad = VoiceActivityDetector(
                threshold=self.config.vad_threshold,
                sample_rate=self.config.sample_rate,
            )
        except Exception as e:
            log.error("VAD init failed: %s", e)
            notify(t("notify.error_title"), t("notify.vad_failed", error=e))
            self._set_tray(t("tray.error_vad"), ICON_IDLE)
            return

        # Whisper
        self._set_tray(f"⏳ {t('notify.loading_whisper')} ({self.config.model})", ICON_LOADING)

        try:
            self._transcriber = Transcriber(self.config)
            self._transcriber.load_model()
        except Exception as e:
            log.error("Whisper init failed: %s", e)
            notify(t("notify.error_title"), t("notify.whisper_failed", error=e))
            self._set_tray(t("tray.error_whisper"), ICON_IDLE)
            return

        # Post-processor (DeepSeek API)
        self._postprocessor = PostProcessor(self.config)
        if self._postprocessor.is_enabled:
            log.info("Post-processing enabled (translate=%s, prompt=%s)",
                     self.config.translate_to or "off",
                     "yes" if self.config.custom_prompt else "no")

        hotkey_info = self.config.hotkey
        if self.config.translate_hotkey and self._is_processing_useful():
            hotkey_info += f" | {self.config.translate_hotkey}→process"
        log.info("Ready. Model: %s, Hotkey: %s", self.config.model, hotkey_info)
        self._set_tray(t("tray.ready", hotkey=hotkey_info), ICON_IDLE)
        notify("VoiceType", t("notify.ready", model=self.config.model, hotkey=self.config.hotkey))

    def _check_model_idle(self) -> None:
        """Перевірити чи модель простоює довше таймауту — вивантажити."""
        timeout = self.config.model_idle_timeout
        if timeout <= 0 or not self._transcriber or not self._transcriber.is_loaded:
            return
        if self._is_recording:
            return
        elapsed = time.time() - self._transcriber.last_used
        if elapsed >= timeout * 60:
            self._transcriber.unload_model()
            self._set_tray(t("tray.idle_unloaded", hotkey=self.config.hotkey), ICON_IDLE)
            log.info("Model unloaded after %d min idle", timeout)

    def _ensure_model_loaded(self) -> bool:
        """Переконатись що модель завантажена. Повертає False якщо не вдалось."""
        if self._transcriber and self._transcriber.is_loaded:
            return True
        if not self._transcriber:
            return False
        # Модель була вивантажена — перезавантажити
        self._set_tray(f"⏳ {t('notify.loading_whisper')} ({self.config.model})", ICON_LOADING)
        try:
            self._transcriber.load_model()
            self._set_tray(t("tray.ready", hotkey=self.config.hotkey), ICON_IDLE)
            log.info("Model reloaded after idle unload")
            return True
        except Exception as e:
            log.error("Model reload failed: %s", e)
            notify(t("notify.error_title"), t("notify.whisper_failed", error=e))
            self._set_tray(t("tray.error_whisper"), ICON_IDLE)
            return False

    def _do_start_recording(self, data: dict | None = None) -> None:
        """Почати запис."""
        if self._is_recording:
            return
        if not self._transcriber:
            return
        if not self._ensure_model_loaded():
            return

        self._translate_mode = bool(data and data.get("translate"))

        self._is_recording = True

        # Hold mode: block trigger key to prevent key repeat typing
        if self.config.recording_mode == "hold":
            hotkey_str = self.config.translate_hotkey if self._translate_mode else self.config.hotkey
            self._held_key = hotkey_str.split("+")[-1].strip()
            try:
                keyboard.block_key(self._held_key)
            except Exception:
                self._held_key = None
        else:
            self._held_key = None

        self._set_tray(t("tray.recording"), ICON_RECORDING)

        if self.config.sound_on_start:
            threading.Thread(target=beep_start, daemon=True).start()

        # Підготувати silence tracker
        self._silence_tracker = SilenceTracker(
            vad=self._vad,
            silence_duration=self.config.silence_duration,
            sample_rate=self.config.sample_rate,
        )

        # Callback для VAD — авто-стоп по тиші (тільки в auto режимі)
        use_vad_stop = self.config.recording_mode == "auto"

        def on_chunk(chunk: np.ndarray) -> None:
            if use_vad_stop and self._silence_tracker and self._silence_tracker.process_chunk(chunk):
                self._command_queue.put(("vad_stop", None))

        self._recorder = AudioRecorder(self.config, on_chunk=on_chunk)
        self._recorder.start()

        # Таймер максимального запису (0 = без ліміту)
        if self.config.max_recording > 0:
            self._max_timer = threading.Timer(
                self.config.max_recording, lambda: self._command_queue.put(("max_timeout", None))
            )
            self._max_timer.start()

    def _do_stop_recording(self) -> None:
        """Зупинити запис і запустити транскрипцію в окремому потоці (non-blocking)."""
        if not self._is_recording:
            return

        self._is_recording = False

        # Unblock held key
        if self._held_key:
            try:
                keyboard.unblock_key(self._held_key)
            except Exception:
                pass
            self._held_key = None

        # Скасувати таймер
        if self._max_timer:
            self._max_timer.cancel()
            self._max_timer = None

        if self.config.sound_on_stop:
            threading.Thread(target=beep_stop, daemon=True).start()

        self._set_tray(t("tray.processing"), ICON_PROCESSING)

        # Отримати аудіо
        audio = self._recorder.stop() if self._recorder else np.array([], dtype=np.float32)

        if len(audio) < self.config.sample_rate * 0.3:  # менше 0.3с — пропустити
            self._set_tray(t("tray.ready", hotkey=self.config.hotkey), ICON_IDLE)
            return

        # Скинути VAD стан
        if self._silence_tracker:
            self._silence_tracker.reset()

        # Non-blocking: транскрипція + пост-обробка + вставка в окремому потоці
        translate = self._translate_mode
        self._translate_mode = False
        threading.Thread(
            target=self._process_audio, args=(audio, translate), daemon=True
        ).start()

    def _process_audio(self, audio: np.ndarray, translate: bool = False) -> None:
        """Транскрипція + пост-обробка + вставка (окремий потік)."""
        # Визначити task для Whisper
        if translate and self.config.translate_to == "English (Whisper)":
            task = "translate"
        else:
            task = "transcribe"

        try:
            text = self._transcriber.transcribe(audio, task=task)
        except Exception as e:
            log.error("Transcription failed: %s", e)
            self._command_queue.put(("processing_done", None))
            return

        if not text:
            log.info("Empty transcription, skipping")
            self._command_queue.put(("processing_done", None))
            return

        # Хоткей обробки → фільтри + custom_prompt + переклад
        if translate and self._postprocessor and self._postprocessor.is_enabled:
            try:
                processed = self._postprocessor.process(text)
                if processed:
                    text = processed
            except Exception as e:
                log.error("Post-processing failed: %s", e)

        # Основний хоткей → чиста транскрипція, без LLM
        self._command_queue.put(("processing_done", text))

    def _on_processing_done(self, text: str | None) -> None:
        """Обробка результату транскрипції (worker thread)."""
        if not text:
            self._set_tray(t("tray.ready", hotkey=self.config.hotkey), ICON_IDLE)
            return

        log.info("Transcribed: %s", text)

        # Вставка тексту
        if self.config.copy_to_clipboard or self.config.auto_paste:
            import pyperclip
            pyperclip.copy(text)
            log.info("Copied to clipboard")

        if self.config.auto_paste:
            time.sleep(0.3)
            keyboard.send("ctrl+v")
            log.info("Sent Ctrl+V")

        if self.config.show_notification:
            preview = text[:100] + ("..." if len(text) > 100 else "")
            notify("VoiceType", preview, self.config.notification_duration)

        self._set_tray(t("tray.ready", hotkey=self.config.hotkey), ICON_IDLE)

    # ─── Tray actions ────────────────────────────────────────

    def _build_tray_menu_items(self):
        """Build tray menu items — called each time menu opens (dynamic)."""
        from voicetype.config import TRANSLATE_LANGUAGES

        # Translate submenu
        translate_items = []
        # "Off" item
        translate_items.append(
            pystray.MenuItem(
                t("tray.translate_off"),
                lambda icon, item: self._set_translate_to(""),
                checked=lambda item: self.config.translate_to == "",
                radio=True,
            )
        )
        for lang_key, lang_display in TRANSLATE_LANGUAGES.items():
            if not lang_key:
                continue
            def _make_action(lk):
                return lambda icon, item: self._set_translate_to(lk)
            def _make_checked(lk):
                return lambda item: self.config.translate_to == lk
            translate_items.append(
                pystray.MenuItem(
                    lang_display,
                    _make_action(lang_key),
                    checked=_make_checked(lang_key),
                    radio=True,
                )
            )

        return (
            pystray.MenuItem("VoiceType", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.translate_submenu"), pystray.Menu(*translate_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.settings"), self._on_settings),
            pystray.MenuItem(t("tray.about"), self._on_about),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.quit"), self._on_quit),
        )

    def _set_translate_to(self, lang: str) -> None:
        """Update translate_to config from tray menu."""
        if self.config.translate_to == lang:
            return
        self.config.translate_to = lang
        self.config.save()
        self._postprocessor = PostProcessor(self.config)
        # Re-register hotkeys if translate_hotkey visibility changes
        self._start_hotkey_listener()
        hotkey_info = self.config.hotkey
        if self.config.translate_hotkey and self._is_processing_useful():
            hotkey_info += f" | {self.config.translate_hotkey}→process"
        self._set_tray(t("tray.ready", hotkey=hotkey_info), ICON_IDLE)
        log.info("Translate target changed to: %s", lang or "off")

    def _set_tray(self, title: str, icon: Image.Image) -> None:
        if self._tray:
            self._tray.icon = icon
            self._tray.title = title

    def _on_settings(self, icon=None, item=None) -> None:
        """Відкрити вікно налаштувань — або винести існуюче на передній план."""
        import subprocess, ctypes
        if self._settings_proc and self._settings_proc.poll() is None:
            # Спробувати винести вікно на передній план
            title = t("settings.title")
            hwnd = ctypes.windll.user32.FindWindowW(None, title)
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            return
        if getattr(sys, "frozen", False):
            self._settings_proc = subprocess.Popen(
                [sys.executable, "--settings"],
                cwd=str(_app_dir()),
            )
        else:
            self._settings_proc = subprocess.Popen(
                [sys.executable, "-m", "voicetype.settings_window"],
                cwd=str(Path(__file__).parent.parent),
            )

    def _check_config_change(self) -> None:
        """Перевірити чи конфіг змінився (після закриття settings)."""
        new_config = Config.load()
        if new_config == self.config:
            return
        old = self.config
        self.config = new_config

        # UI мова
        if old.ui_language != new_config.ui_language:
            set_language(new_config.ui_language)

        # Хоткей або режим запису
        if (old.hotkey != new_config.hotkey or old.recording_mode != new_config.recording_mode
                or old.translate_hotkey != new_config.translate_hotkey):
            self._start_hotkey_listener()

        # Post-processor — перестворити при зміні налаштувань
        if (old.deepseek_api_key != new_config.deepseek_api_key
                or getattr(old, 'openrouter_api_key', '') != getattr(new_config, 'openrouter_api_key', '')
                or getattr(old, 'llm_provider', 'deepseek') != getattr(new_config, 'llm_provider', 'deepseek')
                or old.translate_to != new_config.translate_to
                or old.custom_prompt != new_config.custom_prompt
                or old.active_filters != new_config.active_filters):
            self._postprocessor = PostProcessor(new_config)
            log.info("Post-processor updated (enabled=%s)", self._postprocessor.is_enabled)
            # Re-register hotkeys — translate_hotkey visibility may change
            if new_config.translate_hotkey:
                self._start_hotkey_listener()

        # Оновити config у transcriber (для translate_to та інших runtime полів)
        if self._transcriber:
            self._transcriber.config = new_config

        # Модель/device/compute — потрібен повний reinit
        if (old.model != new_config.model or old.device != new_config.device
                or old.compute_type != new_config.compute_type or old.language != new_config.language):
            self._command_queue.put(("init", None))
        else:
            # Просто оновити tray title (може змінитись мова UI)
            hotkey_info = self.config.hotkey
            if self.config.translate_hotkey and self._is_processing_useful():
                hotkey_info += f" | {self.config.translate_hotkey}→process"
            self._set_tray(t("tray.ready", hotkey=hotkey_info), ICON_IDLE)

    def _on_about(self, icon=None, item=None) -> None:
        """Відкрити вікно About як окремий процес."""
        import subprocess
        if getattr(sys, "frozen", False):
            self._settings_proc = subprocess.Popen(
                [sys.executable, "--about"],
                cwd=str(_app_dir()),
            )
        else:
            self._settings_proc = subprocess.Popen(
                [sys.executable, "-m", "voicetype.about_window"],
                cwd=str(Path(__file__).parent.parent),
            )

    def _on_quit(self, icon=None, item=None) -> None:
        """Вихід з додатку — закрити все."""
        keyboard.unhook_all_hotkeys()
        if self._recorder and self._recorder.is_recording:
            self._recorder.stop()
        # Закрити всі дочірні процеси
        import psutil
        try:
            parent = psutil.Process(os.getpid())
            for child in parent.children(recursive=True):
                child.terminate()
        except Exception:
            pass
        self._command_queue.put(("quit", None))
        if self._tray:
            self._tray.stop()


# ─── Single instance lock ────────────────────────────────────

_lock_file = None

def _acquire_lock() -> bool:
    """Спробувати захопити lock-файл. Повертає False якщо вже запущено."""
    global _lock_file
    lock_path = LOG_DIR / "voicetype.lock"
    try:
        import msvcrt
        _lock_file = open(lock_path, "w", encoding="utf-8")
        msvcrt.locking(_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
        return True
    except (OSError, IOError):
        return False


def _release_lock() -> None:
    global _lock_file
    if _lock_file:
        try:
            import msvcrt
            _lock_file.seek(0)
            msvcrt.locking(_lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            _lock_file.close()
        except Exception:
            pass
        _lock_file = None


# ─── Entry point ─────────────────────────────────────────────

def main():
    # --settings / --about: відкрити вікно без lock, без tray
    if "--settings" in sys.argv:
        from voicetype.settings_window import SettingsWindow
        config = Config.load()
        set_language(config.ui_language)
        win = SettingsWindow(config)
        win.open()
        return

    if "--about" in sys.argv:
        from voicetype.about_window import AboutWindow
        config = Config.load()
        set_language(config.ui_language)
        AboutWindow(config).open()
        return

    if not _acquire_lock():
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, t("notify.already_running"), "VoiceType", 0x40
        )
        return

    try:
        app = VoiceTypeApp()
        app.run()
    finally:
        _release_lock()


if __name__ == "__main__":
    main()
