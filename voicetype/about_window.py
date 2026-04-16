"""About window — інформація про програму, системні вимоги."""

from __future__ import annotations

import customtkinter as ctk

from voicetype.config import Config, _app_dir
from voicetype.i18n import t, set_language, STRINGS

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

VERSION = "0.1.0"
GITHUB = "https://github.com/VIKINGIST/VoiceType"

# Рядки About — не в i18n бо це статичний контент з форматуванням
ABOUT_STRINGS = {
    "en": {
        "sys_req": "System Requirements",
        "minimum": "Minimum",
        "recommended": "Recommended",
        "min_spec": (
            "• Windows 10/11 (64-bit)\n"
            "• 4 GB RAM\n"
            "• Any NVIDIA GPU with CUDA (GTX 1060+)\n"
            "• 2 GB free VRAM\n"
            "• Microphone\n"
            "• Internet (first launch only — model download ~1.5 GB)"
        ),
        "rec_spec": (
            "• Windows 11\n"
            "• 16 GB RAM\n"
            "• NVIDIA RTX 2060+ / 6 GB VRAM\n"
            "• Model: large-v3-turbo (float16)\n"
            "• Latency: ~0.2s per 10s of audio"
        ),
        "cpu_note": "Works on CPU too, but 10-50x slower. Use model 'small' or 'medium' for CPU.",
        "license": "License",
    },
    "uk": {
        "sys_req": "Системні вимоги",
        "minimum": "Мінімальні",
        "recommended": "Рекомендовані",
        "min_spec": (
            "• Windows 10/11 (64-біт)\n"
            "• 4 GB RAM\n"
            "• Будь-яка NVIDIA GPU з CUDA (GTX 1060+)\n"
            "• 2 GB вільної VRAM\n"
            "• Мікрофон\n"
            "• Інтернет (тільки перший запуск — завантаження моделі ~1.5 GB)"
        ),
        "rec_spec": (
            "• Windows 11\n"
            "• 16 GB RAM\n"
            "• NVIDIA RTX 2060+ / 6 GB VRAM\n"
            "• Модель: large-v3-turbo (float16)\n"
            "• Затримка: ~0.2с на 10с аудіо"
        ),
        "cpu_note": "Працює і на CPU, але в 10-50 разів повільніше. Для CPU використовуйте модель 'small' або 'medium'.",
        "license": "Ліцензія",
    },
    "de": {
        "sys_req": "Systemanforderungen",
        "minimum": "Minimum",
        "recommended": "Empfohlen",
        "min_spec": (
            "• Windows 10/11 (64-Bit)\n"
            "• 4 GB RAM\n"
            "• Beliebige NVIDIA GPU mit CUDA (GTX 1060+)\n"
            "• 2 GB freier VRAM\n"
            "• Mikrofon\n"
            "• Internet (nur beim ersten Start — Modell-Download ~1.5 GB)"
        ),
        "rec_spec": (
            "• Windows 11\n"
            "• 16 GB RAM\n"
            "• NVIDIA RTX 2060+ / 6 GB VRAM\n"
            "• Modell: large-v3-turbo (float16)\n"
            "• Latenz: ~0.2s pro 10s Audio"
        ),
        "cpu_note": "Funktioniert auch auf CPU, aber 10-50x langsamer. Verwenden Sie Modell 'small' oder 'medium' für CPU.",
        "license": "Lizenz",
    },
    "pl": {
        "sys_req": "Wymagania systemowe",
        "minimum": "Minimalne",
        "recommended": "Zalecane",
        "min_spec": (
            "• Windows 10/11 (64-bit)\n"
            "• 4 GB RAM\n"
            "• Dowolna karta NVIDIA z CUDA (GTX 1060+)\n"
            "• 2 GB wolnego VRAM\n"
            "• Mikrofon\n"
            "• Internet (tylko przy pierwszym uruchomieniu — pobieranie modelu ~1.5 GB)"
        ),
        "rec_spec": (
            "• Windows 11\n"
            "• 16 GB RAM\n"
            "• NVIDIA RTX 2060+ / 6 GB VRAM\n"
            "• Model: large-v3-turbo (float16)\n"
            "• Opóźnienie: ~0.2s na 10s audio"
        ),
        "cpu_note": "Działa też na CPU, ale 10-50x wolniej. Dla CPU użyj modelu 'small' lub 'medium'.",
        "license": "Licencja",
    },
    "fr": {
        "sys_req": "Configuration requise",
        "minimum": "Minimum",
        "recommended": "Recommandé",
        "min_spec": (
            "• Windows 10/11 (64 bits)\n"
            "• 4 Go RAM\n"
            "• N'importe quel GPU NVIDIA avec CUDA (GTX 1060+)\n"
            "• 2 Go de VRAM libre\n"
            "• Microphone\n"
            "• Internet (premier lancement uniquement — téléchargement du modèle ~1.5 Go)"
        ),
        "rec_spec": (
            "• Windows 11\n"
            "• 16 Go RAM\n"
            "• NVIDIA RTX 2060+ / 6 Go VRAM\n"
            "• Modèle : large-v3-turbo (float16)\n"
            "• Latence : ~0.2s pour 10s d'audio"
        ),
        "cpu_note": "Fonctionne aussi sur CPU, mais 10-50x plus lent. Utilisez le modèle 'small' ou 'medium' pour CPU.",
        "license": "Licence",
    },
    "es": {
        "sys_req": "Requisitos del sistema",
        "minimum": "Mínimos",
        "recommended": "Recomendados",
        "min_spec": (
            "• Windows 10/11 (64 bits)\n"
            "• 4 GB RAM\n"
            "• Cualquier GPU NVIDIA con CUDA (GTX 1060+)\n"
            "• 2 GB de VRAM libre\n"
            "• Micrófono\n"
            "• Internet (solo primer inicio — descarga del modelo ~1.5 GB)"
        ),
        "rec_spec": (
            "• Windows 11\n"
            "• 16 GB RAM\n"
            "• NVIDIA RTX 2060+ / 6 GB VRAM\n"
            "• Modelo: large-v3-turbo (float16)\n"
            "• Latencia: ~0.2s por 10s de audio"
        ),
        "cpu_note": "También funciona en CPU, pero 10-50x más lento. Para CPU usa el modelo 'small' o 'medium'.",
        "license": "Licencia",
    },
}


def _s(key: str, lang: str) -> str:
    """Get about string with fallback."""
    return ABOUT_STRINGS.get(lang, ABOUT_STRINGS["en"]).get(key, ABOUT_STRINGS["en"][key])


class AboutWindow:
    def __init__(self, config: Config):
        self.config = config
        self.lang = config.ui_language

    def open(self) -> None:
        w = ctk.CTk()
        w.title(t("tray.about"))
        w.geometry("440x560")
        w.resizable(False, False)
        # Icon + taskbar
        import ctypes as _ct
        _ct.windll.shell32.SetCurrentProcessExplicitAppUserModelID("voicetype.about")
        try:
            from PIL import Image, ImageTk
            from pathlib import Path
            ico_path = _app_dir() / "voicetype.ico"
            if not ico_path.exists():
                ico_path = Path(__file__).parent.parent / "voicetype.ico"
            if ico_path.exists():
                img = Image.open(ico_path)
                icons = [ImageTk.PhotoImage(img.resize((s, s), Image.LANCZOS)) for s in [48, 32]]
                w.wm_iconphoto(True, *icons)
                self._icon_refs = icons
        except Exception:
            pass

        scroll = ctk.CTkScrollableFrame(w, corner_radius=0, fg_color="gray10")
        scroll.pack(fill="both", expand=True)
        scroll.columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(scroll, text="VoiceType", font=ctk.CTkFont(size=24, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 2)
        )
        ctk.CTkLabel(scroll, text=f"v{VERSION}", font=ctk.CTkFont(size=13), text_color="gray").pack(
            anchor="w", padx=20, pady=(0, 4)
        )
        ctk.CTkLabel(
            scroll, text="Local voice input for Windows — offline, free, GPU-powered",
            font=ctk.CTkFont(size=12), text_color="gray", wraplength=400
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # Current config
        card = ctk.CTkFrame(scroll, fg_color="gray14", corner_radius=10)
        card.pack(fill="x", padx=16, pady=(0, 8))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        info_text = (
            f"Model: {self.config.model}\n"
            f"Hotkey: {self.config.hotkey}\n"
            f"Recognition: {self.config.language}\n"
            f"Device: {'GPU (CUDA)' if self.config.device >= 0 else 'CPU'} / {self.config.compute_type}"
        )
        ctk.CTkLabel(inner, text=info_text, font=ctk.CTkFont(size=12, family="Consolas"),
                      justify="left").pack(anchor="w")

        # System requirements
        ctk.CTkLabel(scroll, text=_s("sys_req", self.lang),
                      font=ctk.CTkFont(size=14, weight="bold"),
                      text_color="#3B8ED0").pack(anchor="w", padx=20, pady=(12, 4))

        # Minimum
        ctk.CTkLabel(scroll, text=f"📋  {_s('minimum', self.lang)}",
                      font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(4, 2))
        ctk.CTkLabel(scroll, text=_s("min_spec", self.lang),
                      font=ctk.CTkFont(size=12), justify="left", wraplength=400).pack(
            anchor="w", padx=20, pady=(0, 8)
        )

        # Recommended
        ctk.CTkLabel(scroll, text=f"⭐  {_s('recommended', self.lang)}",
                      font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(4, 2))
        ctk.CTkLabel(scroll, text=_s("rec_spec", self.lang),
                      font=ctk.CTkFont(size=12), justify="left", wraplength=400).pack(
            anchor="w", padx=20, pady=(0, 4)
        )

        # CPU note
        note_frame = ctk.CTkFrame(scroll, fg_color="gray17", corner_radius=8)
        note_frame.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(note_frame, text=f"ℹ️  {_s('cpu_note', self.lang)}",
                      font=ctk.CTkFont(size=11), text_color="gray",
                      wraplength=380, justify="left").pack(padx=12, pady=8)

        # License + Links
        ctk.CTkLabel(scroll, text=f"{_s('license', self.lang)}: MIT",
                      font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(0, 2))

        link = ctk.CTkLabel(scroll, text=f"GitHub: {GITHUB}",
                             font=ctk.CTkFont(size=12, underline=True),
                             text_color="#3B8ED0", cursor="hand2")
        link.pack(anchor="w", padx=20, pady=(0, 4))
        link.bind("<Button-1>", lambda e: __import__("webbrowser").open(GITHUB))

        # Close
        ctk.CTkButton(scroll, text="OK", width=80, height=30,
                       command=w.destroy).pack(pady=(8, 16))

        w.mainloop()


if __name__ == "__main__":
    config = Config.load()
    set_language(config.ui_language)
    AboutWindow(config).open()
