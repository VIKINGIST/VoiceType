"""Переклад i18n рядків через DeepSeek API.

Використання:
    python scripts/translate.py

Потрібна змінна середовища DEEPSEEK_API_KEY або файл .env з ключем.
"""

import json
import os
import sys
import time
from pathlib import Path

# Додати корінь проєкту в path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from voicetype.i18n import STRINGS

API_URL = "https://api.deepseek.com/v1/chat/completions"
TARGET_LANGS = {
    "en": "English",
    "de": "German",
    "pl": "Polish",
    "fr": "French",
    "es": "Spanish",
}


def get_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        print("ERROR: DEEPSEEK_API_KEY not found.")
        print("Set it as env variable or add to .env file:")
        print('  DEEPSEEK_API_KEY="sk-..."')
        sys.exit(1)
    return key


def translate_batch(texts: dict[str, str], target_lang: str, target_name: str, api_key: str) -> dict[str, str]:
    """Перекласти batch рядків з української на цільову мову."""

    # Формуємо JSON для перекладу
    items = {k: v for k, v in texts.items()}

    prompt = f"""Translate the following UI strings from Ukrainian to {target_name}.
Rules:
- Keep the EXACT same keys, only translate values
- Keep {{placeholders}} like {{hotkey}}, {{model}}, {{error}} etc. unchanged
- Keep technical terms: GPU, CUDA, CPU, VRAM, VAD, Whisper, Ctrl+V, float16, int8
- Keep emoji and special characters (★, ⚙, ✓) unchanged
- Keep "VoiceType" unchanged
- Be concise — these are UI labels, not literature
- Return ONLY valid JSON, no markdown, no explanation

Input JSON:
{json.dumps(items, ensure_ascii=False, indent=2)}"""

    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 4096,
        },
        timeout=60,
    )
    resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"]
    # Очистити від можливого markdown
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]

    return json.loads(content)


def main():
    api_key = get_api_key()

    # Зібрати всі українські рядки
    uk_texts = {}
    for key, translations in STRINGS.items():
        if "uk" in translations:
            uk_texts[key] = translations["uk"]

    print(f"Translating {len(uk_texts)} strings to {len(TARGET_LANGS)} languages...")
    print(f"Total API calls: {len(TARGET_LANGS)}")
    print()

    all_translations: dict[str, dict[str, str]] = {}

    for lang_code, lang_name in TARGET_LANGS.items():
        print(f"  [{lang_code}] {lang_name}...", end=" ", flush=True)
        try:
            result = translate_batch(uk_texts, lang_code, lang_name, api_key)
            all_translations[lang_code] = result
            print(f"OK ({len(result)} strings)")
        except Exception as e:
            print(f"FAILED: {e}")
            continue
        time.sleep(0.5)  # rate limit

    # Генеруємо оновлений i18n.py
    print()
    print("Generating voicetype/i18n.py...")

    # Мержимо переклади в STRINGS
    for key in STRINGS:
        for lang_code, translations in all_translations.items():
            if key in translations:
                STRINGS[key][lang_code] = translations[key]

    # Записуємо оновлений файл
    i18n_path = Path(__file__).parent.parent / "voicetype" / "i18n.py"
    lines = [
        '"""Інтернаціоналізація VoiceType."""',
        "",
        "from __future__ import annotations",
        "",
        "# Всі рядки UI — ключ: {мова: переклад}",
        "# Згенеровано scripts/translate.py (DeepSeek API)",
        "",
        "STRINGS: dict[str, dict[str, str]] = {",
    ]

    for key, translations in STRINGS.items():
        lines.append(f"    {key!r}: {{")
        for lang, text in sorted(translations.items()):
            lines.append(f"        {lang!r}: {text!r},")
        lines.append("    },")

    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("_current_lang = \"uk\"")
    lines.append("")
    lines.append("")
    lines.append("def set_language(lang: str) -> None:")
    lines.append('    """Встановити мову UI."""')
    lines.append("    global _current_lang")
    lines.append("    _current_lang = lang")
    lines.append("")
    lines.append("")
    lines.append("def t(key: str, **kwargs) -> str:")
    lines.append('    """Отримати переклад за ключем. Fallback: uk → en → key."""')
    lines.append("    entry = STRINGS.get(key, {})")
    lines.append('    text = entry.get(_current_lang) or entry.get("uk") or entry.get("en") or key')
    lines.append("    if kwargs:")
    lines.append("        try:")
    lines.append("            text = text.format(**kwargs)")
    lines.append("        except (KeyError, IndexError):")
    lines.append("            pass")
    lines.append("    return text")
    lines.append("")

    i18n_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written to {i18n_path}")
    print("Done!")


if __name__ == "__main__":
    main()
