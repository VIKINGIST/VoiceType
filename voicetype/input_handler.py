"""Вставка тексту в активне вікно через clipboard + Ctrl+V."""

import time
import pyperclip
import pyautogui


def paste_text(text: str, delay: float = 0.15) -> None:
    """Скопіювати текст у буфер обміну і вставити в активне вікно.

    Args:
        text: текст для вставки
        delay: затримка перед Ctrl+V (щоб фокус повернувся до попереднього вікна)
    """
    pyperclip.copy(text)
    time.sleep(delay)
    pyautogui.hotkey("ctrl", "v")
