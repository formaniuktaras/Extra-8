from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from core.settings import UserSettings
from ui.widgets.preview_panel import PreviewPanel


class ThemeManager:
    def __init__(self, app: QApplication) -> None:
        self.app = app

    def apply(self, settings: UserSettings, root: QWidget | None = None) -> None:
        accent = QColor(settings.accent_color)
        if not accent.isValid():
            accent = QColor("#3A7AFE")
        accent_hex = accent.name().upper()

        palette = self._palette(settings.theme_preset, accent_hex)
        self.app.setPalette(palette)
        self.app.setStyleSheet(self._stylesheet(settings.theme_preset, accent_hex))

        ui_font = QFont(settings.ui_font_family)
        ui_font.setPointSizeF(max(8.0, float(settings.ui_font_size) * float(settings.scale_factor)))
        self.app.setFont(ui_font)

        if root is not None:
            root.setFont(ui_font)
            self._refresh_widget_fonts(root, ui_font)
            self.apply_preview_fonts(root, settings)
            root.update()

    def apply_preview_fonts(self, root: QWidget, settings: UserSettings) -> None:
        preview_font = QFont(settings.preview_font_family)
        preview_font.setPointSizeF(max(8.0, float(settings.preview_font_size) * float(settings.scale_factor)))
        for panel in self.iter_preview_widgets(root):
            panel.setFont(preview_font)

    @staticmethod
    def iter_preview_widgets(root: QWidget) -> Iterable[PreviewPanel]:
        return root.findChildren(PreviewPanel)

    @staticmethod
    def _refresh_widget_fonts(root: QWidget, ui_font: QFont) -> None:
        for widget in root.findChildren(QWidget):
            if isinstance(widget, PreviewPanel):
                continue
            widget.setFont(ui_font)

    @staticmethod
    def _palette(theme: str, accent: str) -> QPalette:
        palette = QPalette()
        if theme == "dark":
            palette.setColor(QPalette.Window, QColor("#1e1e1e"))
            palette.setColor(QPalette.WindowText, QColor("#e8e8e8"))
            palette.setColor(QPalette.Base, QColor("#2a2a2a"))
            palette.setColor(QPalette.AlternateBase, QColor("#333333"))
            palette.setColor(QPalette.Text, QColor("#e8e8e8"))
            palette.setColor(QPalette.Button, QColor("#333333"))
            palette.setColor(QPalette.ButtonText, QColor("#f4f4f4"))
            palette.setColor(QPalette.Highlight, QColor(accent))
        elif theme == "light":
            palette.setColor(QPalette.Window, QColor("#ffffff"))
            palette.setColor(QPalette.WindowText, QColor("#111111"))
            palette.setColor(QPalette.Base, QColor("#ffffff"))
            palette.setColor(QPalette.AlternateBase, QColor("#f6f6f6"))
            palette.setColor(QPalette.Text, QColor("#111111"))
            palette.setColor(QPalette.Button, QColor("#f3f3f3"))
            palette.setColor(QPalette.ButtonText, QColor("#111111"))
            palette.setColor(QPalette.Highlight, QColor(accent))
        else:
            palette.setColor(QPalette.Highlight, QColor(accent))
        return palette

    @staticmethod
    def _stylesheet(theme: str, accent: str) -> str:
        chrome = "#333333" if theme == "dark" else "#d0d7de"
        return (
            f"QPushButton {{ border: 1px solid {accent}; padding: 4px; }}"
            f"QComboBox, QLineEdit, QTextEdit {{ border: 1px solid {chrome}; border-radius: 3px; padding: 2px; }}"
            f"QTabBar::tab:selected {{ border-bottom: 2px solid {accent}; }}"
            f"QCheckBox::indicator:checked {{ background: {accent}; border: 1px solid {accent}; }}"
        )
