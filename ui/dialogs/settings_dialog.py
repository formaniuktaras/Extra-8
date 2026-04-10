from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QTabWidget, QTextEdit, QVBoxLayout, QWidget

from core.settings import UserSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Налаштування")
        self.tabs = QTabWidget()
        self.theme_edit = QLineEdit(settings.theme_preset)
        self.font_edit = QLineEdit(settings.fonts.get("family", ""))
        self.scale_edit = QLineEdit(str(settings.scaling))
        self.rules_edit = QTextEdit(settings.summary_rules_json)

        general = QWidget()
        fg = QFormLayout(general)
        fg.addRow("Тема", self.theme_edit)
        fg.addRow("Шрифт", self.font_edit)
        fg.addRow("Масштаб", self.scale_edit)

        rules = QWidget()
        fr = QVBoxLayout(rules)
        fr.addWidget(self.rules_edit)

        self.tabs.addTab(general, "Загальні")
        self.tabs.addTab(rules, "Шаблони / Summary rules")

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self.buttons)

    def build_settings(self, base: UserSettings) -> UserSettings:
        return UserSettings(
            theme_preset=self.theme_edit.text().strip() or "system",
            colors=base.colors,
            fonts={"family": self.font_edit.text().strip() or "Segoe UI", "size": base.fonts.get("size", "10")},
            scaling=float(self.scale_edit.text() or 1.0),
            highlight_options=base.highlight_options,
            summary_unit=base.summary_unit,
            summary_rules_json=self.rules_edit.toPlainText(),
            geometry=base.geometry,
            window_state=base.window_state,
        )
