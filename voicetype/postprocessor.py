"""Пост-обробка транскрибованого тексту — переклад, фільтри, LLM."""

from __future__ import annotations

import logging

from voicetype.config import Config
from voicetype.llm_client import LLMClient

log = logging.getLogger("voicetype")


FILTERS: list[dict] = [
    {
        "id": "punctuation",
        "prompt": "Fix punctuation and capitalization (sentences start with capitals, end with proper punctuation).",
        "name_key": "filter.punctuation",
    },
    {
        "id": "filler_words",
        "prompt": "Remove filler words and verbal tics (um, uh, like, you know, well, basically, so, right, actually, honestly, literally, I mean / ну, типу, е-е, от, значить, короче, як би, ось).",
        "name_key": "filter.filler_words",
    },
    {
        "id": "repetitions",
        "prompt": "Remove accidental word and phrase repetitions, keeping only the final version.",
        "name_key": "filter.repetitions",
    },
    {
        "id": "paragraphs",
        "prompt": "Split text into logical paragraphs based on topic changes.",
        "name_key": "filter.paragraphs",
    },
    {
        "id": "professional",
        "prompt": "Rewrite in a professional, formal tone while preserving meaning.",
        "name_key": "filter.professional",
    },
]


class PostProcessor:
    """Ланцюжок обробки тексту після транскрипції.

    Порядок: custom_prompt → translate_to.
    Якщо обидва вимкнені або API key порожній — повертає текст без змін.
    """

    def __init__(self, config: Config):
        self.config = config
        self._client: LLMClient | None = None
        provider = getattr(config, "llm_provider", "deepseek")
        api_key = (
            getattr(config, "openrouter_api_key", "")
            if provider == "openrouter"
            else config.deepseek_api_key
        )
        if api_key:
            self._client = LLMClient(api_key, provider=provider)

    @property
    def is_enabled(self) -> bool:
        """True якщо є API key і хоча б одна обробка увімкнена."""
        if not self._client or not self._client.is_configured:
            return False
        return (
            bool(self.config.custom_prompt)
            or bool(self.config.translate_to)
            or bool(self.config.active_filters)
        )

    def process(self, text: str) -> str:
        """Обробити текст. Повертає оригінал при помилці або якщо вимкнено."""
        if not text or not self.is_enabled:
            return text

        result = text

        # Крок 1: фільтри + custom_prompt (один LLM call)
        active = [f for f in FILTERS if f["id"] in self.config.active_filters]
        has_filters = bool(active)
        has_prompt = bool(self.config.custom_prompt)

        if has_filters or has_prompt:
            try:
                result = self._client.process_composite(
                    result,
                    filter_prompts=[f["prompt"] for f in active],
                    custom_prompt=self.config.custom_prompt,
                )
                log.info("LLM processed: %d→%d chars, filters=%d", len(text), len(result), len(active))
            except Exception as e:
                log.error("LLM processing failed: %s", e)
                return text  # fallback на оригінал

        # Крок 2: переклад (окремий LLM call)
        # Пропускаємо "English (Whisper)" — Whisper вже переклав на етапі транскрипції
        if self.config.translate_to and self.config.translate_to != "English (Whisper)":
            try:
                result = self._client.translate(result, self.config.translate_to)
                log.info("Translated to %s: %d chars", self.config.translate_to, len(result))
            except Exception as e:
                log.error("Translation failed: %s", e)

        return result.strip() if result else text
