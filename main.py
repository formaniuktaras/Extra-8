from __future__ import annotations

import sys
from pathlib import Path

from person_extract.app import launch_app


def _hide_console_window() -> None:
    """Hide the console window on Windows when running the GUI app."""

    if sys.platform != "win32":  # Only relevant on Windows
        return

    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        # Best-effort: if hiding fails we simply keep the console visible.
        pass


def _iter_config_directories() -> list[Path]:
    """Return candidate directories that may contain ``config.json``."""

    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass))

    candidates.extend(
        [
            Path(__file__).resolve().parent,
            Path.cwd(),
        ]
    )

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def _locate_config() -> Path:
    for directory in _iter_config_directories():
        candidate = directory / "config.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Не вдалося знайти config.json. Переконайтеся, що файл "
        "знаходиться поруч із виконуваним файлом або в каталозі проєкту."
    )


if __name__ == "__main__":
    _hide_console_window()
    config_path = _locate_config()
    launch_app(config_path)
