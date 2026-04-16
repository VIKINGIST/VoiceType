"""Нотифікації та звукові сигнали."""

from __future__ import annotations

import logging
import threading
import winsound
from pathlib import Path

log = logging.getLogger("voicetype")


def _get_icon_path() -> str | None:
    """Шлях до іконки для toast нотифікації."""
    from voicetype.config import _app_dir
    ico = _app_dir() / "voicetype.ico"
    if ico.exists():
        return str(ico)
    ico = Path(__file__).parent.parent / "voicetype.ico"
    if ico.exists():
        return str(ico)
    return None


def notify(title: str, message: str, duration: int = 3) -> None:
    """Показати Windows toast нотифікацію (неблокуючу)."""
    def _show():
        try:
            import pythoncom
            pythoncom.CoInitializeEx(0)
        except Exception:
            pass
        try:
            from win11toast import notify as win_notify
            icon_path = _get_icon_path()
            kwargs = {"duration": duration * 1000}
            if icon_path:
                kwargs["icon"] = icon_path
            win_notify(title, message, **kwargs)
        except Exception as e:
            log.warning("Toast notification failed: %s", e)
    threading.Thread(target=_show, daemon=True).start()


def beep_start() -> None:
    """Короткий високий біп — початок запису."""
    try:
        winsound.Beep(800, 150)
    except Exception:
        pass


def beep_stop() -> None:
    """Короткий низький біп — кінець запису."""
    try:
        winsound.Beep(400, 150)
    except Exception:
        pass
