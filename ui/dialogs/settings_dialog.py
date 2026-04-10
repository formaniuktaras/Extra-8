from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.settings import UserSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Налаштування")
        self.tabs = QTabWidget()

        self.path_edit = QLineEdit()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        self.theme_combo.setCurrentText(settings.theme_preset)
        self.accent_edit = QLineEdit(settings.colors.get("accent", "#3a7afe"))

        self.font_edit = QLineEdit(settings.fonts.get("family", "Segoe UI"))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 30)
        self.font_size.setValue(int(float(settings.fonts.get("size", "10"))))
        self.scale_edit = QDoubleSpinBox()
        self.scale_edit.setRange(0.75, 3.0)
        self.scale_edit.setSingleStep(0.05)
        self.scale_edit.setValue(settings.scaling)

        self.rules_edit = QTextEdit(settings.summary_rules_json)

        paths = QWidget()
        fp = QFormLayout(paths)
        fp.addRow("Корінь джерел", self.path_edit)

        theme = QWidget()
        ft = QFormLayout(theme)
        ft.addRow("Тема", self.theme_combo)
        ft.addRow("Акцент", self.accent_edit)

        fonts = QWidget()
        ff = QFormLayout(fonts)
        ff.addRow("Шрифт", self.font_edit)
        ff.addRow("Розмір", self.font_size)
        ff.addRow("Масштаб", self.scale_edit)

        rules = QWidget()
        fr = QVBoxLayout(rules)
        fr.addWidget(self.rules_edit)

        self.tabs.addTab(paths, "Шляхи")
        self.tabs.addTab(theme, "Тема і кольори")
        self.tabs.addTab(fonts, "Шрифти і масштаб")
        self.tabs.addTab(rules, "Summary rules")

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_apply = QPushButton("Apply")
        self.btn_restore = QPushButton("Restore defaults")
        row = QHBoxLayout()
        row.addWidget(self.btn_restore)
        row.addWidget(self.btn_apply)
        row.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addLayout(row)

    def build_settings(self, base: UserSettings) -> UserSettings:
        return UserSettings(
            theme_preset=self.theme_combo.currentText().strip() or "system",
            colors={"accent": self.accent_edit.text().strip() or "#3a7afe"},
            fonts={
                "family": self.font_edit.text().strip() or "Segoe UI",
                "size": str(self.font_size.value()),
                "mono": base.fonts.get("mono", "Consolas"),
            },
            scaling=float(self.scale_edit.value()),
            highlight_options=base.highlight_options,
            summary_unit=base.summary_unit,
            summary_rules_json=self.rules_edit.toPlainText(),
            geometry=base.geometry,
            window_state=base.window_state,
        )

    def load_from(self, settings: UserSettings) -> None:
        self.theme_combo.setCurrentText(settings.theme_preset)
        self.accent_edit.setText(settings.colors.get("accent", "#3a7afe"))
        self.font_edit.setText(settings.fonts.get("family", "Segoe UI"))
        self.font_size.setValue(int(float(settings.fonts.get("size", "10"))))
        self.scale_edit.setValue(settings.scaling)
        self.rules_edit.setPlainText(settings.summary_rules_json)
