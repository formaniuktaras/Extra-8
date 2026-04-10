from __future__ import annotations

from PySide6.QtWidgets import QApplication, QWidget

from core.settings import UserSettings


class ThemeManager:
    def __init__(self, app: QApplication) -> None:
        self.app = app

    def apply(self, settings: UserSettings, root: QWidget | None = None) -> None:
        self.app.setStyleSheet(self._stylesheet(settings.theme_preset, settings.colors))
        font = self.app.font()
        font.setFamily(settings.fonts.get("family", "Segoe UI"))
        base_size = float(settings.fonts.get("size", "10"))
        font.setPointSizeF(max(8.0, base_size * settings.scaling))
        self.app.setFont(font)
        if root is not None:
            root.update()

    @staticmethod
    def _stylesheet(theme: str, colors: dict[str, str]) -> str:
        accent = colors.get("accent", "#3a7afe")
        if theme == "dark":
            return (
                "QWidget { background: #1e1e1e; color: #e8e8e8; }"
                f"QPushButton {{ background: #333; border: 1px solid {accent}; padding: 4px; }}"
            )
        if theme == "light":
            return (
                "QWidget { background: #ffffff; color: #111; }"
                f"QPushButton {{ border: 1px solid {accent}; padding: 4px; }}"
            )
        return ""
