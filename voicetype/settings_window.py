"""GUI вікно налаштувань VoiceType (CustomTkinter)."""

from __future__ import annotations

from typing import Callable
from pathlib import Path

import customtkinter as ctk
import sounddevice as sd

from voicetype.config import Config, LANGUAGES, MODELS, MODEL_INFO, COMPUTE_TYPES, RECORDING_MODES, UI_LANGUAGES, LLM_PROVIDERS
from voicetype.i18n import t, set_language


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PAD = 12           # зовнішній padding
CARD_COLOR = "gray14"
CARD_INNER = 14    # внутрішній padding карти
ACCENT = "#3B8ED0"
LABEL_W = 130      # стандартна ширина label

_GPU_COMPUTE_TYPES = ["float16", "int8_float16", "int8"]
_CPU_COMPUTE_TYPES = ["float32", "int8"]


class SettingsWindow:
    """Компактне вікно налаштувань."""

    def __init__(self, config: Config, on_save: Callable[[Config], None] | None = None):
        self.config = config
        self.on_save = on_save
        self._window: ctk.CTk | None = None

    def open(self) -> None:
        if self._window is not None:
            try:
                self._window.lift()
                self._window.focus_force()
                return
            except Exception:
                self._window = None

        self._window = ctk.CTk()
        self._window.title(t("settings.title"))
        self._window.geometry("520x600")
        self._window.minsize(460, 500)
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_icon()

        self._build_ui()
        self._window.mainloop()

    # ── UI ──

    def _build_ui(self) -> None:
        w = self._window
        set_language(self.config.ui_language)

        # Tabview замість ScrollableFrame
        self._tabview = ctk.CTkTabview(w, corner_radius=8, fg_color="gray10",
                                        segmented_button_fg_color="gray14",
                                        segmented_button_selected_color=ACCENT)
        self._tabview.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        tab_rec = self._tabview.add(t("settings.tab_recording"))
        tab_model = self._tabview.add(t("settings.tab_model"))
        tab_audio = self._tabview.add(t("settings.tab_audio"))
        tab_behavior = self._tabview.add(t("settings.tab_behavior"))
        tab_llm = self._tabview.add(t("settings.tab_llm"))

        self._build_tab_recording(tab_rec)
        self._build_tab_model(tab_model)
        self._build_tab_audio(tab_audio)
        self._build_tab_behavior(tab_behavior)
        self._build_tab_llm(tab_llm)

        # Buttons
        btn_frame = ctk.CTkFrame(w, fg_color="gray10", height=50)
        btn_frame.pack(fill="x", side="bottom")
        btn_inner = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_inner.pack(pady=10)
        ctk.CTkButton(btn_inner, text=t("settings.save"), width=130, height=34, command=self._save).pack(side="left", padx=6)
        ctk.CTkButton(btn_inner, text=t("settings.cancel"), width=100, height=34,
                       fg_color="gray25", hover_color="gray35", command=self._on_close).pack(side="left", padx=6)

    # ── Tab builders ─────────────────────────────────────────

    def _build_tab_recording(self, parent) -> None:
        """Вкладка Recording: мова UI, хоткей, режим, хоткей обробки, мова розпізнавання."""
        c = self._tab_card(parent)

        # UI Language
        uilang_row = self._inline_frame(c)
        ctk.CTkLabel(uilang_row, text="UI", width=LABEL_W, anchor="w").pack(side="left")
        uilang_display = [f"{k}  —  {v}" for k, v in UI_LANGUAGES.items()]
        current_uilang = next((d for d in uilang_display if d.startswith(self.config.ui_language)), uilang_display[0])
        self._uilang_var = ctk.StringVar(value=current_uilang)
        ctk.CTkOptionMenu(uilang_row, variable=self._uilang_var, values=uilang_display,
                           height=28, font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)

        # Hotkey
        hk_row = self._inline_frame(c)
        ctk.CTkLabel(hk_row, text=t("settings.hotkey"), width=LABEL_W, anchor="w").pack(side="left")
        self._hotkey_var = ctk.StringVar(value=self.config.hotkey)
        self._hotkey_display = ctk.CTkEntry(hk_row, textvariable=self._hotkey_var, width=130, state="readonly")
        self._hotkey_display.pack(side="left", padx=(0, 6))
        self._hotkey_btn = ctk.CTkButton(hk_row, text=t("settings.hotkey_record"), width=80, height=28,
                                          font=ctk.CTkFont(size=12), command=self._start_hotkey_capture)
        self._hotkey_btn.pack(side="left")
        self._hotkey_hint = ctk.CTkLabel(hk_row, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self._hotkey_hint.pack(side="left", padx=(6, 0))
        self._capturing_hotkey = False

        # Recording mode
        mode_row = self._inline_frame(c)
        ctk.CTkLabel(mode_row, text=t("settings.mode"), width=LABEL_W, anchor="w").pack(side="left")
        mode_display = [t(f"mode.{k}") for k in RECORDING_MODES]
        current_mode = t(f"mode.{self.config.recording_mode}")
        self._mode_var = ctk.StringVar(value=current_mode)
        ctk.CTkOptionMenu(mode_row, variable=self._mode_var, values=mode_display,
                           height=28, font=ctk.CTkFont(size=12),
                           command=self._on_mode_change).pack(side="left", fill="x", expand=True)

        # Process hotkey
        thk_row = self._inline_frame(c)
        ctk.CTkLabel(thk_row, text=t("settings.translate_hotkey"), width=LABEL_W, anchor="w").pack(side="left")
        self._translate_hotkey_var = ctk.StringVar(value=self.config.translate_hotkey)
        self._translate_hotkey_display = ctk.CTkEntry(thk_row, textvariable=self._translate_hotkey_var, width=130, state="readonly")
        self._translate_hotkey_display.pack(side="left", padx=(0, 6))
        self._translate_hotkey_btn = ctk.CTkButton(thk_row, text=t("settings.hotkey_record"), width=80, height=28,
                                                    font=ctk.CTkFont(size=12), command=self._start_translate_hotkey_capture)
        self._translate_hotkey_btn.pack(side="left")
        self._translate_hotkey_hint = ctk.CTkLabel(thk_row, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self._translate_hotkey_hint.pack(side="left", padx=(6, 0))
        self._capturing_translate_hotkey = False

        # Hint
        ctk.CTkLabel(c, text=t("settings.translate_hotkey_hint"),
                      font=ctk.CTkFont(size=10), text_color="gray50", wraplength=430).pack(anchor="w", pady=(0, 4))

        # Recognition language
        lang_row = self._inline_frame(c)
        ctk.CTkLabel(lang_row, text=t("settings.language"), width=LABEL_W, anchor="w").pack(side="left")
        lang_display = [f"{k}  —  {v}" for k, v in LANGUAGES.items()]
        current_lang = next((d for d in lang_display if d.startswith(self.config.language)), lang_display[0])
        self._lang_var = ctk.StringVar(value=current_lang)
        ctk.CTkOptionMenu(lang_row, variable=self._lang_var, values=lang_display,
                           height=28, font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)

    def _build_tab_model(self, parent) -> None:
        """Вкладка Model: device/compute, idle timeout, models list."""
        c = self._tab_card(parent)

        # Model selection via radio buttons in models list
        self._model_var = ctk.StringVar(value=self.config.model)

        # Device + Compute
        dc_row = self._inline_frame(c)

        ctk.CTkLabel(dc_row, text=t("settings.device"), font=ctk.CTkFont(size=12), width=70, anchor="w").pack(side="left")
        is_gpu = self.config.device >= 0
        self._device_var = ctk.StringVar(value="GPU (CUDA)" if is_gpu else "CPU")
        ctk.CTkSegmentedButton(dc_row, values=["GPU (CUDA)", "CPU"], variable=self._device_var,
                                width=180, height=28, font=ctk.CTkFont(size=12),
                                command=self._on_device_change).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(dc_row, text=t("settings.precision"), font=ctk.CTkFont(size=12), width=60, anchor="w").pack(side="left")
        valid_ctypes = _GPU_COMPUTE_TYPES if is_gpu else _CPU_COMPUTE_TYPES
        compute_labels = [t(f"compute.{k}.label") for k in valid_ctypes]
        if self.config.compute_type not in valid_ctypes:
            default_ct = "float16" if is_gpu else "float32"
        else:
            default_ct = self.config.compute_type
        current_compute_label = t(f"compute.{default_ct}.label")
        self._compute_var = ctk.StringVar(value=current_compute_label)
        self._compute_menu = ctk.CTkOptionMenu(dc_row, variable=self._compute_var, values=compute_labels,
                                               width=160, height=28, font=ctk.CTkFont(size=11),
                                               command=self._on_compute_change)
        self._compute_menu.pack(side="left")

        self._compute_desc = ctk.CTkLabel(c, text="", font=ctk.CTkFont(size=11),
                                           text_color="gray", wraplength=430, justify="left")
        self._compute_desc.pack(anchor="w", pady=(4, 0))
        self._update_compute_info(default_ct)

        # Idle timeout
        idle_row = self._inline_frame(c, top_pad=6)
        ctk.CTkLabel(idle_row, text=t("settings.idle_timeout"), width=LABEL_W, anchor="w",
                      font=ctk.CTkFont(size=12)).pack(side="left")
        self._idle_var = ctk.IntVar(value=self.config.model_idle_timeout)
        ctk.CTkSlider(idle_row, from_=0, to=30, variable=self._idle_var, width=150,
                       number_of_steps=6,
                       command=lambda v: self._idle_lbl.configure(
                           text=t("settings.idle_timeout_off") if int(v) == 0 else f"{int(v)} min"
                       )).pack(side="left")
        idle_text = t("settings.idle_timeout_off") if self.config.model_idle_timeout == 0 else f"{self.config.model_idle_timeout} min"
        self._idle_lbl = ctk.CTkLabel(idle_row, text=idle_text, width=40, font=ctk.CTkFont(size=12))
        self._idle_lbl.pack(side="left", padx=(6, 0))

        # Separator
        ctk.CTkFrame(c, height=1, fg_color="gray25").pack(fill="x", pady=(8, 4))

        # Models list
        self._models_tab = c
        self._build_models_list(c)

    def _build_tab_audio(self, parent) -> None:
        """Вкладка Audio: мікрофон, VAD, тиша, макс. запис."""
        c = self._tab_card(parent)

        input_devices = self._get_input_devices()
        device_names = [f"{d['index']}: {d['name']}" for d in input_devices]
        self._mic_var = ctk.StringVar(value=device_names[0] if device_names else "—")
        mic_row = self._inline_frame(c)
        ctk.CTkLabel(mic_row, text=t("settings.microphone"), width=LABEL_W, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(mic_row, variable=self._mic_var,
                           values=device_names if device_names else ["—"],
                           height=28, font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)

        vad_row = self._inline_frame(c)
        ctk.CTkLabel(vad_row, text=t("settings.vad_sensitivity"), width=LABEL_W, anchor="w").pack(side="left")
        self._vad_var = ctk.DoubleVar(value=self.config.vad_threshold)
        ctk.CTkSlider(vad_row, from_=0.1, to=0.9, variable=self._vad_var, width=180,
                       command=lambda v: self._vad_lbl.configure(text=f"{v:.2f}")).pack(side="left")
        self._vad_lbl = ctk.CTkLabel(vad_row, text=f"{self.config.vad_threshold:.2f}",
                                      width=40, font=ctk.CTkFont(size=12))
        self._vad_lbl.pack(side="left", padx=(6, 0))

        self._sil_row = self._inline_frame(c)
        ctk.CTkLabel(self._sil_row, text=t("settings.silence_stop"), width=LABEL_W, anchor="w").pack(side="left")
        self._silence_var = ctk.DoubleVar(value=self.config.silence_duration)
        self._sil_slider = ctk.CTkSlider(self._sil_row, from_=0.5, to=10.0, variable=self._silence_var, width=180,
                                          number_of_steps=19,
                                          command=lambda v: self._sil_lbl.configure(text=f"{v:.1f}s"))
        self._sil_slider.pack(side="left")
        self._sil_lbl = ctk.CTkLabel(self._sil_row, text=f"{self.config.silence_duration:.1f}s",
                                      width=40, font=ctk.CTkFont(size=12))
        self._sil_lbl.pack(side="left", padx=(6, 0))
        if self.config.recording_mode != "auto":
            self._set_silence_enabled(False)

        max_row = self._inline_frame(c)
        ctk.CTkLabel(max_row, text=t("settings.max_recording"), width=LABEL_W, anchor="w").pack(side="left")
        self._maxrec_var = ctk.IntVar(value=self.config.max_recording)
        ctk.CTkSlider(max_row, from_=0, to=120, variable=self._maxrec_var, width=180,
                       number_of_steps=24,
                       command=lambda v: self._max_lbl.configure(
                           text="∞" if int(v) == 0 else f"{int(v)}s"
                       )).pack(side="left")
        max_text = "∞" if self.config.max_recording == 0 else f"{self.config.max_recording}s"
        self._max_lbl = ctk.CTkLabel(max_row, text=max_text, width=40, font=ctk.CTkFont(size=12))
        self._max_lbl.pack(side="left", padx=(6, 0))

    def _build_tab_behavior(self, parent) -> None:
        """Вкладка Behavior: звуки, нотифікації, автозапуск."""
        c = self._tab_card(parent)

        sw_grid = ctk.CTkFrame(c, fg_color="transparent")
        sw_grid.pack(fill="x")
        sw_grid.columnconfigure((0, 1), weight=1)

        self._sound_start_var = ctk.BooleanVar(value=self.config.sound_on_start)
        ctk.CTkSwitch(sw_grid, text=t("settings.sound_start"), variable=self._sound_start_var,
                       font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=3)

        self._sound_stop_var = ctk.BooleanVar(value=self.config.sound_on_stop)
        ctk.CTkSwitch(sw_grid, text=t("settings.sound_stop"), variable=self._sound_stop_var,
                       font=ctk.CTkFont(size=12)).grid(row=0, column=1, sticky="w", pady=3)

        self._notif_var = ctk.BooleanVar(value=self.config.show_notification)
        ctk.CTkSwitch(sw_grid, text=t("settings.notifications"), variable=self._notif_var,
                       font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", pady=3)

        self._autostart_var = ctk.BooleanVar(value=self._is_autostart_enabled())
        ctk.CTkSwitch(sw_grid, text=t("settings.autostart"), variable=self._autostart_var,
                       font=ctk.CTkFont(size=12)).grid(row=1, column=1, sticky="w", pady=3)

        notif_row = self._inline_frame(c, top_pad=6)
        ctk.CTkLabel(notif_row, text=t("settings.notif_duration"), width=LABEL_W, anchor="w",
                      font=ctk.CTkFont(size=12)).pack(side="left")
        self._notifdur_var = ctk.IntVar(value=self.config.notification_duration)
        ctk.CTkSlider(notif_row, from_=1, to=10, variable=self._notifdur_var, width=140,
                       number_of_steps=9,
                       command=lambda v: self._dur_lbl.configure(text=f"{int(v)}s")).pack(side="left")
        self._dur_lbl = ctk.CTkLabel(notif_row, text=f"{self.config.notification_duration}s",
                                      width=40, font=ctk.CTkFont(size=12))
        self._dur_lbl.pack(side="left", padx=(6, 0))

    def _build_tab_llm(self, parent) -> None:
        """Вкладка Processing/LLM: provider, API key, translate, filters, prompt."""
        from voicetype.config import TRANSLATE_LANGUAGES, LLM_PROVIDERS
        import webbrowser

        c = self._tab_card(parent)

        # Provider selector
        provider_row = self._inline_frame(c)
        ctk.CTkLabel(provider_row, text=t("settings.llm_provider"), width=LABEL_W, anchor="w").pack(side="left")
        provider_names = [v["name"] for v in LLM_PROVIDERS.values()]
        provider_keys = list(LLM_PROVIDERS.keys())
        current_provider = getattr(self.config, "llm_provider", "deepseek")
        current_provider_name = LLM_PROVIDERS.get(current_provider, LLM_PROVIDERS["deepseek"])["name"]
        self._provider_var = ctk.StringVar(value=current_provider_name)
        ctk.CTkSegmentedButton(
            provider_row, values=provider_names, variable=self._provider_var,
            height=28, font=ctk.CTkFont(size=12),
            command=self._on_provider_change,
        ).pack(side="left", fill="x", expand=True)

        # API Key rows wrapper (keeps layout position stable when switching providers)
        self._api_wrapper = ctk.CTkFrame(c, fg_color="transparent")
        self._api_wrapper.pack(fill="x", pady=(0, 4))

        # DeepSeek API Key row
        self._deepseek_row = ctk.CTkFrame(self._api_wrapper, fg_color="transparent")
        ctk.CTkLabel(self._deepseek_row, text=t("settings.api_key"), width=LABEL_W, anchor="w").pack(side="left")
        self._apikey_var = ctk.StringVar(value=self.config.deepseek_api_key)
        ctk.CTkEntry(self._deepseek_row, textvariable=self._apikey_var, width=180, show="•",
                      font=ctk.CTkFont(size=12), placeholder_text="sk-...").pack(side="left", padx=(0, 6))
        self._test_btn = ctk.CTkButton(self._deepseek_row, text="Test", width=50, height=28,
                                        font=ctk.CTkFont(size=12),
                                        fg_color="gray25", hover_color="gray35",
                                        command=self._test_api_key)
        self._test_btn.pack(side="left", padx=(0, 4))
        ctk.CTkButton(self._deepseek_row, text=t("settings.register"), width=80, height=28,
                       font=ctk.CTkFont(size=12),
                       fg_color="gray25", hover_color="gray35",
                       command=lambda: webbrowser.open("https://platform.deepseek.com")).pack(side="left")

        # OpenRouter API Key row
        self._openrouter_row = ctk.CTkFrame(self._api_wrapper, fg_color="transparent")
        ctk.CTkLabel(self._openrouter_row, text=t("settings.openrouter_api_key"), width=LABEL_W, anchor="w").pack(side="left")
        self._or_apikey_var = ctk.StringVar(value=getattr(self.config, "openrouter_api_key", ""))
        ctk.CTkEntry(self._openrouter_row, textvariable=self._or_apikey_var, width=180, show="•",
                      font=ctk.CTkFont(size=12), placeholder_text="sk-or-...").pack(side="left", padx=(0, 6))
        self._or_test_btn = ctk.CTkButton(self._openrouter_row, text="Test", width=50, height=28,
                                           font=ctk.CTkFont(size=12),
                                           fg_color="gray25", hover_color="gray35",
                                           command=self._test_api_key)
        self._or_test_btn.pack(side="left", padx=(0, 4))
        ctk.CTkButton(self._openrouter_row, text=t("settings.register"), width=80, height=28,
                       font=ctk.CTkFont(size=12),
                       fg_color="gray25", hover_color="gray35",
                       command=lambda: webbrowser.open("https://openrouter.ai")).pack(side="left")

        # Show correct row based on current provider
        self._on_provider_change(current_provider_name)

        # Translate to
        trans_row = self._inline_frame(c)
        ctk.CTkLabel(trans_row, text=t("settings.translate_to"), width=LABEL_W, anchor="w").pack(side="left")
        trans_display = [f"{k}  —  {v}" if k else v for k, v in TRANSLATE_LANGUAGES.items()]
        current_trans = next(
            (d for d in trans_display if d.startswith(self.config.translate_to)),
            trans_display[0]
        )
        self._translate_var = ctk.StringVar(value=current_trans)
        ctk.CTkOptionMenu(trans_row, variable=self._translate_var, values=trans_display,
                           height=28, font=ctk.CTkFont(size=12),
                           command=lambda _: self._update_translate_warning()).pack(side="left", fill="x", expand=True)

        # Warning label
        self._translate_warn = ctk.CTkLabel(c, text="", font=ctk.CTkFont(size=11),
                                             text_color="#f9e2af", wraplength=430, justify="left")
        self._translate_warn.pack(anchor="w", pady=(0, 4))

        # Predefined filters
        from voicetype.postprocessor import FILTERS
        filters_row = self._inline_frame(c, top_pad=2)
        ctk.CTkLabel(filters_row, text=t("settings.filters_label"),
                      width=LABEL_W, anchor="w").pack(side="left")

        self._filter_vars: dict[str, ctk.BooleanVar] = {}
        filters_grid = ctk.CTkFrame(c, fg_color="transparent")
        filters_grid.pack(fill="x", pady=(0, 6))
        filters_grid.columnconfigure((0, 1), weight=1)

        for i, flt in enumerate(FILTERS):
            var = ctk.BooleanVar(value=flt["id"] in self.config.active_filters)
            self._filter_vars[flt["id"]] = var
            ctk.CTkCheckBox(
                filters_grid,
                text=t(flt["name_key"]),
                variable=var,
                font=ctk.CTkFont(size=12),
            ).grid(row=i // 2, column=i % 2, sticky="w", pady=3, padx=(0, 8))

        # Custom prompt
        prompt_lbl = self._inline_frame(c)
        ctk.CTkLabel(prompt_lbl, text=t("settings.custom_prompt"), width=LABEL_W, anchor="w").pack(side="left")
        ctk.CTkLabel(prompt_lbl, text=t("settings.custom_prompt_hint"),
                      font=ctk.CTkFont(size=10), text_color="gray50", wraplength=300).pack(side="left")
        self._prompt_var = ctk.StringVar(value=self.config.custom_prompt)
        self._prompt_textbox = ctk.CTkTextbox(c, height=60, font=ctk.CTkFont(size=12),
                        fg_color="gray17", border_width=1, border_color="gray30",
                        wrap="word")
        self._prompt_textbox.pack(fill="x", pady=(0, 4))
        if self.config.custom_prompt:
            self._prompt_textbox.insert("1.0", self.config.custom_prompt)

        self._update_translate_warning()

    # ── Models list ──

    def _build_models_list(self, parent) -> None:
        """Побудувати список моделей — завантажені + доступні для скачування."""
        from voicetype.model_manager import list_cached_models, is_model_cached, get_model_size_mb

        if hasattr(self, "_models_card_widget"):
            self._models_card_widget.destroy()

        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=10)
        card.pack(fill="x", pady=(0, 4))
        self._models_card_widget = card

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        cached = list_cached_models()
        cached_names = {m["name"] for m in cached}

        total_mb = sum(m["size_mb"] for m in cached)
        if cached:
            ctk.CTkLabel(inner, text=f"{len(cached)} models  ·  {self._fmt_size(total_mb)}",
                          font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(0, 6))

        # Всі моделі — завантажені і доступні
        all_models = list(MODELS.keys())
        for name in all_models:
            row_frame = ctk.CTkFrame(inner, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            is_cached = name in cached_names
            is_active = name == self.config.model
            cached_info = next((m for m in cached if m["name"] == name), None)

            if is_cached:
                # Радіокнопка для вибору активної моделі
                ctk.CTkRadioButton(
                    row_frame, text="",
                    variable=self._model_var, value=name,
                    width=20, radiobutton_width=16, radiobutton_height=16,
                    command=lambda n=name: self._on_model_select(n),
                ).pack(side="left", padx=(0, 4))
                # Назва
                label_text = t(f"model.{name}.label")
                name_color = ACCENT if is_active else "white"
                ctk.CTkLabel(row_frame, text=label_text,
                              font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
                              text_color=name_color).pack(side="left")
                # Розмір
                ctk.CTkLabel(row_frame, text=self._fmt_size(cached_info["size_mb"]),
                              font=ctk.CTkFont(size=11), text_color="gray",
                              width=70).pack(side="left", padx=(8, 0))
                # Кнопка видалення (не для активної моделі)
                if not is_active:
                    ctk.CTkButton(
                        row_frame, text="✕", width=28, height=24,
                        font=ctk.CTkFont(size=12),
                        fg_color="gray25", hover_color="#c0392b",
                        command=lambda p=cached_info["path"]: self._delete_model(p)
                    ).pack(side="right")
            else:
                # Відступ для вирівнювання з радіокнопками
                ctk.CTkFrame(row_frame, width=24, height=1, fg_color="transparent").pack(side="left")
                # Назва (сіра — не завантажена)
                ctk.CTkLabel(row_frame, text=t(f"model.{name}.label"),
                              font=ctk.CTkFont(size=12),
                              text_color="gray50").pack(side="left")
                # Правий контейнер (стане зоною прогресу при завантаженні)
                right_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                right_frame.pack(side="right", fill="x", expand=True)

                expected = get_model_size_mb(name)
                ctk.CTkLabel(right_frame, text=f"~{self._fmt_size(expected)}",
                              font=ctk.CTkFont(size=11), text_color="gray40").pack(
                    side="left", padx=(8, 0))
                ctk.CTkButton(
                    right_frame, text="⬇", width=28, height=24,
                    font=ctk.CTkFont(size=12),
                    fg_color="gray25", hover_color="#27ae60",
                    command=lambda n=name, rf=right_frame: self._download_model_ui(n, rf)
                ).pack(side="right")

        # Model info під списком
        current_model = self._model_var.get()
        info = MODEL_INFO.get(current_model, {})
        info_text = f"{t(f'model.{current_model}.desc')}  ·  VRAM: {info.get('vram', '?')}  ·  {info.get('speed', '')}"
        self._model_info = ctk.CTkLabel(card, text=info_text, font=ctk.CTkFont(size=11),
                                         text_color="gray", wraplength=430, justify="left")
        self._model_info.pack(anchor="w", padx=14, pady=(0, 10))

    def _download_model_ui(self, model_name: str, right_frame: ctk.CTkFrame) -> None:
        """Трансформує рядок моделі в inline прогрес завантаження."""
        import threading
        import logging
        import queue as _queue
        import time as _time
        from voicetype.model_manager import download_model

        _log = logging.getLogger("voicetype")
        _ui_q: _queue.Queue = _queue.Queue()
        _start_time = _time.monotonic()
        _cancel_event = threading.Event()
        _has_real_progress = [False]

        # ── Очистити right_frame і побудувати inline прогрес ──
        for w in right_frame.winfo_children():
            w.destroy()

        # Cancel кнопка — праворуч
        cancel_btn = ctk.CTkButton(
            right_frame, text="✕", width=26, height=22,
            font=ctk.CTkFont(size=11),
            fg_color="gray22", hover_color="#c0392b",
        )
        cancel_btn.pack(side="right", padx=(4, 0))

        # Info лейбл (%, швидкість, ETA) — праворуч від прогрес-бару
        info_label = ctk.CTkLabel(
            right_frame, text="⬇  0s",
            font=ctk.CTkFont(size=11), text_color="gray",
            width=148, anchor="e",
        )
        info_label.pack(side="right", padx=(2, 4))

        # Прогрес-бар — заповнює простір що залишився
        progress_bar = ctk.CTkProgressBar(right_frame, height=10, mode="indeterminate",
                                          progress_color=ACCENT)
        progress_bar.pack(side="left", fill="x", expand=True, padx=(8, 0))
        progress_bar.start()

        def _cancel() -> None:
            _cancel_event.set()
            try:
                progress_bar.stop()
            except Exception:
                pass
            if self._window is not None:
                self._window.after(500, lambda: self._build_models_list(self._models_tab))

        cancel_btn.configure(command=_cancel)

        # ── Poll: головний потік вичитує черги оновлень UI ──
        def _poll() -> None:
            try:
                while True:
                    fn = _ui_q.get_nowait()
                    fn()
            except _queue.Empty:
                pass
            except Exception:
                pass
            if self._window is not None and not _cancel_event.is_set():
                self._window.after(50, _poll)

        self._window.after(50, _poll)

        # ── Tick: оновлює elapsed коли реального прогресу немає ──
        def _tick() -> None:
            if _cancel_event.is_set() or self._window is None:
                return
            if not _has_real_progress[0]:
                try:
                    if info_label.winfo_exists():
                        elapsed = int(_time.monotonic() - _start_time)
                        m, s = divmod(elapsed, 60)
                        elapsed_str = f"{m}:{s:02d}" if m else f"{s}s"
                        info_label.configure(text=f"⬇  {elapsed_str}")
                except Exception:
                    pass
            if not _cancel_event.is_set() and self._window is not None:
                self._window.after(1000, _tick)

        self._window.after(1000, _tick)

        # ── on_progress: фоновий потік → черга → main thread ──
        def on_progress(p) -> None:
            def _apply() -> None:
                if _cancel_event.is_set():
                    return
                try:
                    if not progress_bar.winfo_exists() or not info_label.winfo_exists():
                        return
                    pct = p.percent
                    if pct > 0.005:
                        _has_real_progress[0] = True
                        progress_bar.stop()
                        progress_bar.configure(mode="determinate")
                        progress_bar.set(pct)

                    if p.speed_mbps > 0:
                        spd = f"↓{p.speed_str}"
                    else:
                        spd = "..."

                    if pct > 0.005:
                        pct_txt = f"{pct * 100:.0f}%"
                        if p.eta_seconds > 0:
                            info_label.configure(text=f"{pct_txt}  {spd}  ~{p.eta_str}")
                        else:
                            info_label.configure(text=f"{pct_txt}  {spd}")
                    else:
                        info_label.configure(text=f"⬇  {spd}")
                except Exception:
                    pass
            _ui_q.put(_apply)

        # ── _finish: викликається після завершення ──
        def _finish(status: str, success: bool) -> None:
            if _cancel_event.is_set():
                return
            _cancel_event.set()
            try:
                progress_bar.stop()
                progress_bar.configure(mode="determinate")
                progress_bar.set(1.0 if success else 0.0)
                if not success:
                    progress_bar.configure(progress_color="#e74c3c")
            except Exception:
                pass
            try:
                if info_label.winfo_exists():
                    info_label.configure(
                        text=status,
                        text_color="#2ecc71" if success else "#e74c3c",
                    )
                if cancel_btn.winfo_exists():
                    cancel_btn.destroy()
            except Exception:
                pass
            if self._window is not None:
                self._window.after(2500, lambda: self._build_models_list(self._models_tab))

        # ── do_download: фоновий потік ──
        def do_download() -> None:
            errs: list[str] = []
            try:
                result = download_model(model_name, on_progress=on_progress, errors=errs, cancel_event=_cancel_event)
                if _cancel_event.is_set():
                    return
                if result:
                    _ui_q.put(lambda: _finish("✓ done", True))
                else:
                    detail = (": " + errs[0][:40]) if errs else ""
                    _ui_q.put(lambda: _finish(f"✕ failed{detail}", False))
            except Exception:
                _log.error("Download thread error for %s", model_name, exc_info=True)
                if not _cancel_event.is_set():
                    _ui_q.put(lambda: _finish("✕ error", False))

        threading.Thread(target=do_download, daemon=True).start()

    def _delete_model(self, model_path) -> None:
        """Видалити модель і оновити список."""
        from voicetype.model_manager import delete_model
        import ctypes
        result = ctypes.windll.user32.MessageBoxW(
            0,
            t("settings.delete_confirm", path=model_path.name),
            "VoiceType",
            0x04 | 0x30  # MB_YESNO | MB_ICONWARNING
        )
        if result == 6:  # Yes
            delete_model(model_path)
            self._build_models_list(self._models_tab)

    @staticmethod
    def _fmt_size(mb: int) -> str:
        if mb >= 1000:
            return f"{mb / 1000:.1f} GB"
        return f"{mb} MB"

    # ── Layout helpers ──

    def _set_icon(self) -> None:
        """Встановити іконку вікна + taskbar (через PhotoImage для чіткості)."""
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("voicetype.settings")
        try:
            from PIL import Image, ImageTk
            from voicetype.config import _app_dir
            ico_path = _app_dir() / "voicetype.ico"
            if not ico_path.exists():
                ico_path = Path(__file__).parent.parent / "voicetype.ico"
            if ico_path.exists():
                img = Image.open(ico_path)
                # Завантажити кілька розмірів для title bar (32) + taskbar (48)
                icons = []
                for size in [48, 32]:
                    resized = img.resize((size, size), Image.LANCZOS)
                    icons.append(ImageTk.PhotoImage(resized))
                self._window.wm_iconphoto(True, *icons)
                self._icon_refs = icons  # тримати reference щоб GC не зібрав
        except Exception:
            pass

    def _tab_card(self, parent) -> ctk.CTkFrame:
        """Створити card-фон для вкладки."""
        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=10)
        card.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=CARD_INNER, pady=CARD_INNER)
        return inner

    @staticmethod
    def _inline_frame(parent, top_pad: int = 0) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(top_pad, 4))
        return f

    # ── Hotkey capture ──

    def _start_translate_hotkey_capture(self) -> None:
        if self._capturing_translate_hotkey:
            return
        self._capturing_translate_hotkey = True
        self._translate_hotkey_btn.configure(text="...", state="disabled")
        self._translate_hotkey_hint.configure(text=t("settings.hotkey_recording"))
        self._pressed_keys: set[str] = set()
        self._window.bind("<KeyPress>", self._on_translate_key_press)
        self._window.bind("<KeyRelease>", self._on_translate_key_release)

    def _on_translate_key_press(self, event) -> None:
        if not self._capturing_translate_hotkey:
            return
        key = self._normalize_key(event)
        if key:
            self._pressed_keys.add(key)
            combo = self._build_combo()
            if combo:
                self._translate_hotkey_var.set(combo)

    def _on_translate_key_release(self, event) -> None:
        if not self._capturing_translate_hotkey:
            return
        combo = self._build_combo()
        modifiers = {"ctrl", "alt", "shift", "win"}
        has_modifier = any(k in modifiers for k in self._pressed_keys)
        has_key = any(k not in modifiers for k in self._pressed_keys)
        if has_modifier and has_key and combo:
            self._finish_translate_hotkey_capture(combo)
        else:
            key = self._normalize_key(event)
            if key:
                self._pressed_keys.discard(key)

    def _finish_translate_hotkey_capture(self, combo: str) -> None:
        self._capturing_translate_hotkey = False
        self._translate_hotkey_var.set(combo)
        self._translate_hotkey_btn.configure(text=t("settings.hotkey_record"), state="normal")
        self._translate_hotkey_hint.configure(text=f"OK {combo}")
        self._window.unbind("<KeyPress>")
        self._window.unbind("<KeyRelease>")
        self._pressed_keys.clear()

    def _start_hotkey_capture(self) -> None:
        if self._capturing_hotkey:
            return
        self._capturing_hotkey = True
        self._hotkey_btn.configure(text="...", state="disabled")
        self._hotkey_hint.configure(text=t("settings.hotkey_recording"))
        self._pressed_keys: set[str] = set()
        self._window.bind("<KeyPress>", self._on_key_press)
        self._window.bind("<KeyRelease>", self._on_key_release)

    def _on_key_press(self, event) -> None:
        if not self._capturing_hotkey:
            return
        key = self._normalize_key(event)
        if key:
            self._pressed_keys.add(key)
            combo = self._build_combo()
            if combo:
                self._hotkey_var.set(combo)

    def _on_key_release(self, event) -> None:
        if not self._capturing_hotkey:
            return
        combo = self._build_combo()
        modifiers = {"ctrl", "alt", "shift", "win"}
        has_modifier = any(k in modifiers for k in self._pressed_keys)
        has_key = any(k not in modifiers for k in self._pressed_keys)
        if has_modifier and has_key and combo:
            self._finish_hotkey_capture(combo)
        else:
            key = self._normalize_key(event)
            if key:
                self._pressed_keys.discard(key)

    def _build_combo(self) -> str:
        modifiers = {"ctrl", "alt", "shift", "win"}
        order = ["ctrl", "alt", "shift", "win"]
        mods = [k for k in order if k in self._pressed_keys]
        keys = sorted(k for k in self._pressed_keys if k not in modifiers)
        if mods and keys:
            return "+".join(mods + keys)
        if mods:
            return "+".join(mods) + "+..."
        return ""

    def _finish_hotkey_capture(self, combo: str) -> None:
        self._capturing_hotkey = False
        self._hotkey_var.set(combo)
        self._hotkey_btn.configure(text=t("settings.hotkey_record"), state="normal")
        self._hotkey_hint.configure(text=f"✓ {combo}")
        self._window.unbind("<KeyPress>")
        self._window.unbind("<KeyRelease>")
        self._pressed_keys.clear()

    @staticmethod
    def _normalize_key(event) -> str | None:
        keysym = event.keysym.lower()
        mapping = {
            "control_l": "ctrl", "control_r": "ctrl",
            "alt_l": "alt", "alt_r": "alt",
            "shift_l": "shift", "shift_r": "shift",
            "super_l": "win", "super_r": "win",
            "escape": None,
            "return": "enter", "space": "space",
            "tab": "tab", "backspace": "backspace",
        }
        if keysym in mapping:
            return mapping[keysym]
        # Function keys
        if keysym.startswith("f") and keysym[1:].isdigit():
            return keysym
        # Latin alphanumeric — keysym is reliable
        if len(keysym) == 1 and keysym.isascii() and keysym.isalnum():
            return keysym
        # Non-Latin layout (Cyrillic, etc.): fall back to Windows VK code
        # VK codes are layout-independent physical key positions
        vk = getattr(event, "keycode", 0)
        if 0x41 <= vk <= 0x5A:  # A-Z
            return chr(vk + 32)  # lowercase
        if 0x30 <= vk <= 0x39:  # 0-9
            return chr(vk)
        return None

    # ── Device / Mode callbacks ──

    def _set_silence_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        color = "gray" if enabled else "gray40"
        try:
            self._sil_slider.configure(state=state)
            self._sil_lbl.configure(text_color=color)
            for w in self._sil_row.winfo_children():
                if isinstance(w, ctk.CTkLabel):
                    w.configure(text_color=color)
        except Exception:
            pass

    def _on_mode_change(self, value: str) -> None:
        mode_key = next((k for k in RECORDING_MODES if t(f"mode.{k}") == value), "auto")
        self._set_silence_enabled(mode_key == "auto")

    def _on_provider_change(self, value: str) -> None:
        """Show/hide API key rows based on selected provider."""
        from voicetype.config import LLM_PROVIDERS
        provider_key = next((k for k, v in LLM_PROVIDERS.items() if v["name"] == value), "deepseek")
        # Hide both first, then show the active one
        self._deepseek_row.pack_forget()
        self._openrouter_row.pack_forget()
        if provider_key == "openrouter":
            self._openrouter_row.pack(fill="x")
        else:
            self._deepseek_row.pack(fill="x")
        if hasattr(self, '_translate_warn'):
            self._update_translate_warning()

    # ── Model/Compute info ──

    def _get_active_api_key(self) -> str:
        """Get the API key for the currently selected provider."""
        from voicetype.config import LLM_PROVIDERS
        if not hasattr(self, '_provider_var'):
            return self._apikey_var.get().strip()
        provider_name = self._provider_var.get()
        provider_key = next((k for k, v in LLM_PROVIDERS.items() if v["name"] == provider_name), "deepseek")
        if provider_key == "openrouter":
            return self._or_apikey_var.get().strip()
        return self._apikey_var.get().strip()

    def _update_translate_warning(self) -> None:
        """Оновити warning під translate dropdown залежно від моделі та API key."""
        trans_val = self._translate_var.get().split("  —  ")[0].strip()
        model_key = self._model_var.get()
        api_key = self._get_active_api_key()

        # Збираємо активні фільтри
        has_filters = any(var.get() for var in self._filter_vars.values()) if hasattr(self, '_filter_vars') else False
        has_prompt = bool(self._prompt_textbox.get("1.0", "end-1c").strip()) if hasattr(self, '_prompt_textbox') else False

        if not trans_val and not has_filters and not has_prompt:
            # Нічого не налаштовано — без warning
            self._translate_warn.configure(text="")
            return

        if trans_val == "English (Whisper)":
            if "turbo" in model_key:
                self._translate_warn.configure(
                    text=t("settings.translate_warn_turbo"),
                    text_color="#f38ba8",
                )
                return

        # Перевірка API key для LLM-залежних функцій
        needs_api = bool(trans_val and trans_val != "English (Whisper)") or has_filters or has_prompt
        if needs_api and not api_key:
            self._translate_warn.configure(
                text=t("settings.warn_no_apikey_filters"),
                text_color="#f9e2af",
            )
            return

        # Все ОК
        self._translate_warn.configure(text="")

    def _test_api_key(self) -> None:
        """Перевірити API key для обраного провайдера."""
        import threading
        from voicetype.config import LLM_PROVIDERS

        provider_name = self._provider_var.get()
        provider_key = next((k for k, v in LLM_PROVIDERS.items() if v["name"] == provider_name), "deepseek")

        if provider_key == "openrouter":
            key = self._or_apikey_var.get().strip()
            btn = self._or_test_btn
        else:
            key = self._apikey_var.get().strip()
            btn = self._test_btn

        if not key:
            btn.configure(text="✕", text_color="#e74c3c")
            self._window.after(2000, lambda: btn.configure(text="Test", text_color="white"))
            return

        btn.configure(text="...", state="disabled")

        def _do_test():
            from voicetype.llm_client import LLMClient
            try:
                client = LLMClient(key, provider=provider_key)
                result = client._call("", "Say OK", temperature=0)
                success = bool(result)
            except Exception:
                success = False

            if self._window is None:
                return
            self._window.after(0, lambda: self._show_test_result(success, btn))

        threading.Thread(target=_do_test, daemon=True).start()

    def _show_test_result(self, success: bool, btn: ctk.CTkButton | None = None) -> None:
        btn = btn or self._test_btn
        if success:
            btn.configure(text="✓", text_color="#2ecc71", state="normal")
        else:
            btn.configure(text="✕", text_color="#e74c3c", state="normal")
        self._window.after(3000, lambda: btn.configure(text="Test", text_color="white"))

    def _on_model_select(self, model_key: str) -> None:
        """Обробити вибір моделі через радіокнопку."""
        info = MODEL_INFO.get(model_key, {})
        info_text = f"{t(f'model.{model_key}.desc')}  ·  VRAM: {info.get('vram', '?')}  ·  {info.get('speed', '')}"
        if hasattr(self, '_model_info') and self._model_info.winfo_exists():
            self._model_info.configure(text=info_text)
        self._update_translate_warning()

    def _on_compute_change(self, value: str) -> None:
        self._update_compute_info(self._label_to_compute_key(value))

    def _update_compute_info(self, key: str) -> None:
        self._compute_desc.configure(text=t(f"compute.{key}.desc"))

    def _on_device_change(self, value: str) -> None:
        is_gpu = value == "GPU (CUDA)"
        valid = _GPU_COMPUTE_TYPES if is_gpu else _CPU_COMPUTE_TYPES
        valid_labels = [t(f"compute.{k}.label") for k in valid]
        self._compute_menu.configure(values=valid_labels)
        current_key = self._label_to_compute_key(self._compute_var.get())
        if current_key not in valid:
            default = "float16" if is_gpu else "float32"
            self._compute_var.set(t(f"compute.{default}.label"))
            self._update_compute_info(default)
        else:
            self._update_compute_info(current_key)

    def _label_to_compute_key(self, label: str) -> str:
        for k in COMPUTE_TYPES:
            if t(f"compute.{k}.label") == label:
                return k
        return COMPUTE_TYPES[0]

    @staticmethod
    def _get_input_devices() -> list[dict]:
        result = []
        try:
            for i, d in enumerate(sd.query_devices()):
                if d["max_input_channels"] > 0:
                    result.append({"index": i, "name": d["name"]})
        except Exception:
            pass
        return result

    # ── Autostart ──

    _SHORTCUT_NAME = "VoiceType.lnk"

    @classmethod
    def _startup_folder(cls) -> str:
        import os
        return os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")

    @classmethod
    def _shortcut_path(cls) -> str:
        import os
        return os.path.join(cls._startup_folder(), cls._SHORTCUT_NAME)

    @classmethod
    def _is_autostart_enabled(cls) -> bool:
        import os
        return os.path.exists(cls._shortcut_path())

    @classmethod
    def _set_autostart(cls, enabled: bool) -> None:
        import os, sys
        from pathlib import Path
        from voicetype.config import _app_dir
        shortcut = cls._shortcut_path()
        if enabled:
            app_dir = _app_dir()
            # PyInstaller EXE або start.bat
            if getattr(sys, "frozen", False):
                target = Path(sys.executable)
            else:
                target = app_dir / "start.bat"
            ps_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{shortcut}"); '
                f'$s.TargetPath = "{target}"; '
                f'$s.WorkingDirectory = "{app_dir}"; '
                f'$s.WindowStyle = 7; '
                f'$s.Description = "VoiceType"; '
                f'$s.Save()'
            )
            os.system(f'powershell -Command "{ps_cmd}"')
        else:
            if os.path.exists(shortcut):
                os.remove(shortcut)

    # ── Save ──

    _RESTART_FIELDS = {"model", "device", "compute_type", "language", "recording_mode", "ui_language", "translate_hotkey"}

    def _save(self) -> None:
        old = self._snapshot()

        self.config.hotkey = self._hotkey_var.get().strip()
        self.config.ui_language = self._uilang_var.get().split("  —  ")[0].strip()
        mode_val = self._mode_var.get()
        self.config.recording_mode = next(
            (k for k in RECORDING_MODES if t(f"mode.{k}") == mode_val), "auto"
        )
        self.config.language = self._lang_var.get().split("  —  ")[0].strip()
        self.config.model = self._model_var.get()
        self.config.device = 0 if self._device_var.get() == "GPU (CUDA)" else -1
        self.config.compute_type = self._label_to_compute_key(self._compute_var.get())
        self.config.vad_threshold = round(self._vad_var.get(), 2)
        self.config.silence_duration = round(self._silence_var.get(), 1)
        self.config.max_recording = int(self._maxrec_var.get())
        self.config.model_idle_timeout = int(self._idle_var.get())
        self.config.auto_paste = True
        self.config.copy_to_clipboard = True
        self.config.show_notification = self._notif_var.get()
        self.config.notification_duration = int(self._notifdur_var.get())
        self.config.sound_on_start = self._sound_start_var.get()
        self.config.sound_on_stop = self._sound_stop_var.get()
        self.config.start_minimized = True
        self.config.deepseek_api_key = self._apikey_var.get().strip()
        # Provider fields
        from voicetype.config import LLM_PROVIDERS
        provider_name = self._provider_var.get()
        self.config.llm_provider = next(
            (k for k, v in LLM_PROVIDERS.items() if v["name"] == provider_name), "deepseek"
        )
        self.config.openrouter_api_key = self._or_apikey_var.get().strip()
        trans_val = self._translate_var.get().split("  —  ")[0].strip()
        self.config.translate_to = trans_val
        self.config.translate_hotkey = self._translate_hotkey_var.get().strip()
        self.config.custom_prompt = self._prompt_textbox.get("1.0", "end-1c").strip()
        self.config.active_filters = [
            flt_id for flt_id, var in self._filter_vars.items() if var.get()
        ]

        new = self._snapshot()
        changed = {k for k in old if old[k] != new[k]}

        if not changed:
            self._on_close()
            return

        self.config.save()

        # Autostart — окремо від конфігу (це системний ярлик)
        autostart_wanted = self._autostart_var.get()
        if autostart_wanted != self._is_autostart_enabled():
            self._set_autostart(autostart_wanted)

        needs_restart = changed & self._RESTART_FIELDS

        if self.on_save:
            self.on_save(self.config)

        ui_lang_changed = "ui_language" in changed

        dialog = ctk.CTkToplevel(self._window)
        dialog.title("VoiceType")
        dialog.resizable(False, False)
        dialog.transient(self._window)
        dialog.grab_set()

        dialog.geometry("300x110")
        ctk.CTkLabel(dialog, text=t("settings.saved"),
                      font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(16, 2))
        if ui_lang_changed:
            ctk.CTkLabel(dialog, text=t("settings.restart_prompt"),
                          text_color="gray", font=ctk.CTkFont(size=11)).pack()
        elif needs_restart:
            ctk.CTkLabel(dialog, text=t("settings.reloading"), text_color="gray", font=ctk.CTkFont(size=11)).pack()
        ctk.CTkButton(dialog, text="OK", width=70, height=28,
                       command=lambda: (dialog.destroy(), self._on_close())).pack(pady=8)

    def _snapshot(self) -> dict:
        return {f: getattr(self.config, f) for f in self.config.__dataclass_fields__}

    def _on_close(self) -> None:
        if self._window:
            self._window.destroy()
            self._window = None


if __name__ == "__main__":
    config = Config.load()
    win = SettingsWindow(config)
    win.open()
