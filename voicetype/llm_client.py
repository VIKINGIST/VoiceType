"""DeepSeek API клієнт для пост-обробки тексту."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger("voicetype")

PROVIDER_CONFIGS = {
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openai/gpt-4o-mini",
    },
}
TIMEOUT = 15  # секунд — пост-обробка має бути швидкою


class LLMClient:
    """Клієнт для LLM API (DeepSeek, OpenRouter)."""

    def __init__(self, api_key: str, provider: str = "deepseek", model: str | None = None):
        self.api_key = api_key
        self.provider = provider
        cfg = PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS["deepseek"])
        self._api_url = cfg["url"]
        self.model = model or cfg["model"]

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _call(self, system: str, user: str, temperature: float = 0.1) -> str:
        """Виклик DeepSeek API. Повертає текст відповіді."""
        if not self.api_key:
            raise RuntimeError("API key not configured")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        resp = requests.post(
            self._api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2048,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]
        return content.strip()

    def process(self, text: str, prompt: str) -> str:
        """Обробити текст за допомогою custom prompt."""
        system = (
            "You are a text post-processor. "
            "Apply the user's instructions to the given text. "
            "Return ONLY the processed text, no explanations, no quotes, no markdown."
        )
        user = f"Instructions: {prompt}\n\nText: {text}"
        return self._call(system, user)

    def process_composite(
        self,
        text: str,
        filter_prompts: list[str],
        custom_prompt: str = "",
    ) -> str:
        """Обробити текст: фільтри + custom_prompt за один API виклик."""
        system = (
            "You are a text post-processor for voice transcription. "
            "Apply ALL listed instructions to the text. "
            "Return ONLY the processed text, no explanations, no quotes, no markdown."
        )
        instructions = list(filter_prompts)
        if custom_prompt:
            instructions.append(custom_prompt)
        if not instructions:
            return text
        numbered = "\n".join(f"{i+1}. {inst}" for i, inst in enumerate(instructions))
        user = f"Instructions:\n{numbered}\n\nText: {text}"
        return self._call(system, user)

    def translate(self, text: str, target_language: str) -> str:
        """Перекласти текст на цільову мову."""
        system = (
            "You are a translator. "
            "Translate the text to the specified language. "
            "Return ONLY the translation, no explanations, no quotes, no markdown. "
            "Preserve the original meaning and tone."
        )
        user = f"Translate to {target_language}:\n\n{text}"
        return self._call(system, user)
