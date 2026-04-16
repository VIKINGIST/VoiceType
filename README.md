# VoiceType

Local voice input for Windows. Press a hotkey — speak — text appears in any application. Fully offline, free, GPU-powered.

🇺🇦 [Документація українською](README.uk.md)

## Features

- **Voice input** — press hotkey, speak, text gets pasted into the active field
- **Three recording modes** — automatic (silence = stop), hold-to-record, manual toggle
- **Dual hotkey** — main hotkey for pure transcription + processing hotkey for filtered/translated output
- **Post-processing pipeline** — 5 predefined filters (punctuation, filler words, repetitions, paragraphs, professional tone) + custom prompt + LLM translation
- **LLM providers** — DeepSeek or OpenRouter for post-processing (API key required, optional)
- **33 recognition languages** — Ukrainian, English, German, Polish, French, Spanish, and 27 more + auto-detect
- **33 translation languages** — translate transcription output via LLM to any supported language
- **Fully offline** — Whisper model runs on local GPU, no data leaves your machine (post-processing optionally uses external LLM API)
- **GPU accelerated** — ~0.2s to transcribe 10 seconds of audio (NVIDIA CUDA)
- **Non-blocking pipeline** — transcription runs in a background thread, UI stays responsive
- **Model idle unload** — GPU VRAM is freed after configurable timeout, model reloads on next use
- **System tray** — color-coded icon (gray/yellow/red/blue) + quick language submenu
- **Cyrillic hotkey support** — hotkey recorder works with any keyboard layout
- **Modern settings** — dark theme GUI with 5 tabs: Recording, Model, Audio, Behavior, Processing
- **i18n** — UI available in 6 languages
- **Windows installer** — full Setup with shortcuts and uninstaller

## Requirements

- **Windows 10/11** (64-bit)
- **NVIDIA GPU** with CUDA support (GTX 1060+), minimum **2 GB VRAM**
- NVIDIA driver installed (check: run `nvidia-smi` in terminal)
- Works on CPU too, but 10-50x slower
- For post-processing: DeepSeek or OpenRouter API key (optional)

## Installation

### Installer (recommended)

1. Download:
    **[VoiceType-Setup.exe](https://github.com/VIKINGIST/VoiceType/releases/download/v1.0.0/VoiceType-Setup.exe)** (~900 MB) || **[VoiceType-1.0-Portable.zip ](https://github.com/VIKINGIST/VoiceType/releases/download/v1.0.0/VoiceType-1.0-Portable.zip)** (~1.32 GB)
3. Run the installer, choose installation folder
4. Select options: desktop shortcut, Start Menu, autostart
5. Done

> On first launch, the app will prompt to download the Whisper model (~1.5 GB) from the internet. Subsequent launches use the cached model — startup takes 5-10 seconds.

### Build from source

<details>
<summary>For developers</summary>

#### Requirements
- Python 3.12
- NVIDIA GPU + driver

#### Build EXE

```bash
git clone https://github.com/VIKINGIST/VoiceType.git
cd VoiceType
setup.bat
```

`setup.bat` creates a venv (~2.4 GB, no torch — uses ctranslate2 + nvidia-cublas/cudnn packages), installs dependencies, builds `VoiceType.exe` and creates a shortcut.

#### Build installer

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php)
2. Run `build_installer.bat`
3. Output: `installer_output/VoiceType-Setup.exe` (~1.3 GB with compression)

#### Project structure

```
VoiceType/
├── voicetype/              # source code
│   ├── main.py             # tray, orchestration, hotkeys
│   ├── config.py           # configuration dataclass + YAML
│   ├── i18n.py             # translations (6 languages)
│   ├── recorder.py         # audio recording (sounddevice)
│   ├── vad.py              # voice activity detection (sherpa-onnx)
│   ├── transcriber.py      # speech recognition (faster-whisper)
│   ├── postprocessor.py    # filters + custom prompt + LLM translation
│   ├── llm_client.py       # DeepSeek / OpenRouter API client
│   ├── input_handler.py    # text injection (clipboard + paste)
│   ├── notifier.py         # notifications + beeps
│   ├── model_manager.py    # HF cache: download/list/delete with progress
│   ├── settings_window.py  # settings GUI (separate process)
│   └── about_window.py     # about window (separate process)
├── scripts/                # build utilities
├── config.yaml             # default config
├── voicetype.ico           # app icon
├── requirements.txt        # dependencies
├── setup.bat               # build EXE
├── build_installer.bat     # build installer
├── installer.iss           # Inno Setup script
└── .gitignore
```

#### Tech stack

| Component | Library |
|---|---|
| STT | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) + [ctranslate2](https://github.com/OpenNMT/CTranslate2) |
| VAD | [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) (Silero VAD) |
| GPU runtime | nvidia-cublas-cu12, nvidia-cudnn-cu12 (no torch) |
| LLM (post-processing) | DeepSeek API / OpenRouter |
| Audio | [sounddevice](https://python-sounddevice.readthedocs.io/) |
| Hotkeys | [keyboard](https://github.com/boppreh/keyboard) |
| Tray | [pystray](https://github.com/moses-palmer/pystray) |
| GUI | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) |
| Notifications | [win11toast](https://github.com/GitHub30/win11toast) |
| Build | [PyInstaller](https://pyinstaller.org/) |
| Installer | [Inno Setup](https://jrsoftware.org/) |

</details>

## Usage

### Automatic mode (default)

1. Press `Alt+Q` — recording starts (red icon, beep)
2. Speak
3. Pause for 2 seconds — recording stops automatically
4. Text gets pasted into the active field

### Hold mode

1. Hold `Alt+Q` — records while held
2. Release — stops and transcribes

### Toggle mode

1. Press `Alt+Q` — start recording
2. Press `Alt+Q` again — stop and transcribe

### Processing hotkey (optional)

If you configure a processing hotkey in Settings → Recording, it works the same way as the main hotkey but runs the transcription through the post-processing pipeline before pasting:

- Active filters are applied (punctuation, filler word removal, etc.)
- Custom prompt is sent to the LLM (if set)
- Output is translated to the selected language (if translation is configured)

The processing hotkey requires a configured LLM provider and API key. Without them, it falls back to plain transcription.

Change mode, hotkeys, and other settings: **right-click tray icon → Settings**.

### Tray menu

- **Settings** — open settings window (raises existing window if already open)
- **Translate to** — quick submenu to switch the LLM translation target language
- **Quit** — stop recording and exit

## Settings

### Recording
| Parameter | Default | Description |
|---|---|---|
| UI language | English | Interface language (6 options). Requires restart. |
| Hotkey | `alt+q` | Click "Record" to capture a new key combination. Supports any layout including Cyrillic. |
| Processing hotkey | (none) | Same as hotkey but output goes through post-processing pipeline |
| Recording mode | Automatic | Automatic / Hold / Toggle |
| Language | Auto-detect | Speech recognition language (33 languages + auto) |

### Model
| Parameter | Default | Description |
|---|---|---|
| Whisper model | large-v3-turbo | Best balance of speed and quality |
| Device | GPU (CUDA) | GPU or CPU |
| Precision | float16 | float16 for GPU, float32 for CPU |
| Idle unload timeout | 5 min | Unload model from VRAM after inactivity. 0 = never unload. |

| Model | VRAM | Speed (10s audio) | Quality |
|---|---|---|---|
| **large-v3-turbo** ★ | ~1.6 GB | ~0.2s | High |
| large-v3 | ~3.0 GB | ~1.0s | Highest |
| medium | ~1.0 GB | ~0.1s | Medium |
| small | ~0.5 GB | ~0.05s | Basic |

Models are downloaded from HuggingFace on first use. You can manage cached models (download, delete) from the Model tab.

### Audio
| Parameter | Default | Description |
|---|---|---|
| Microphone | System default | Input device selection |
| VAD sensitivity | 0.50 | Lower = more sensitive to voice |
| Silence for stop | 2.0s | Silence duration for auto-stop (Automatic mode) |
| Max recording | ∞ | Time limit in seconds (0 = no limit) |

### Behavior
| Parameter | Default | Description |
|---|---|---|
| Auto-paste | On | Ctrl+V after transcription |
| Copy to clipboard | On | Copies text to clipboard |
| Notifications | On | Toast with transcribed text |
| Start/stop sound | On | Audio feedback beeps |
| Autostart with Windows | Off | Launch at system startup |

### Processing
| Parameter | Default | Description |
|---|---|---|
| LLM provider | DeepSeek | DeepSeek or OpenRouter |
| API key | (empty) | Your API key. Use "Test" to verify, "Register" to open the provider site. |
| Translate to | (none) | Translate output to this language via LLM (33 languages) |
| Punctuation | Off | Add punctuation and capitalization |
| Remove filler words | Off | Remove "um", "uh", "like", etc. |
| Remove repetitions | Off | Remove repeated words and phrases |
| Paragraphs | Off | Split into paragraphs by topic |
| Professional tone | Off | Rewrite in formal style |
| Custom prompt | (empty) | Free-form instruction sent to LLM after other filters |

Filters and translation are applied only when using the **processing hotkey**. The main hotkey always produces raw transcription.

All settings are also available in `config.yaml` (next to the executable).

## Troubleshooting

| Problem | Solution |
|---|---|
| "Whisper Error" on startup | Internet required for first-time model download (~1.5 GB). Check VRAM with `nvidia-smi`. Try `medium` or `small` model. |
| Hotkey not working | Make sure VoiceType is running (tray icon). Run as administrator for admin-elevated apps. |
| Text not pasting | Ensure cursor is in a text field. Text is always copied to clipboard — try Ctrl+V manually. |
| Poor recognition | Speak clearly, closer to mic. Check microphone in settings. Try `large-v3` model. |
| "Already running" | Close previous instance: tray icon → right-click → Quit. |
| Processing hotkey does nothing | Check that LLM provider and API key are set in Settings → Processing. Use "Test" to verify the key. |
| LLM translation is slow | DeepSeek/OpenRouter API calls add 1-5 seconds depending on text length and network speed. |

## Logs

`logs/voicetype.log` (next to the executable) — recording events, transcribed text, errors.

## License

MIT — [Viktor Korol](https://github.com/VIKINGIST)
