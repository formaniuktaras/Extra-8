from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)

from core.config import AppConfig
from core.settings import UserSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: UserSettings, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Налаштування")
        self.tabs = QTabWidget()

        # Загальні
        self.summary_unit_edit = QLineEdit(settings.summary_unit)

        # Шляхи
        self.source_dir_edit = QLineEdit(config.source_directory)
        self.output_dir_edit = QLineEdit(config.output_directory)
        self.index_file_edit = QLineEdit(config.index_file)

        # Тема і кольори
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        self.theme_combo.setCurrentText(settings.theme_preset)
        self.accent_edit = QLineEdit(settings.accent_color)
        self.accent_pick_btn = QPushButton("Вибрати…")
        self.accent_preview = QLabel()
        self.accent_preview.setFixedWidth(40)

        # Шрифти
        self.ui_font_edit = QLineEdit(settings.ui_font_family)
        self.ui_font_size = QSpinBox()
        self.ui_font_size.setRange(8, 48)
        self.ui_font_size.setValue(settings.ui_font_size)
        self.preview_font_edit = QLineEdit(settings.preview_font_family)
        self.preview_font_size = QSpinBox()
        self.preview_font_size.setRange(8, 48)
        self.preview_font_size.setValue(settings.preview_font_size)
        self.scale_edit = QDoubleSpinBox()
        self.scale_edit.setRange(0.75, 3.0)
        self.scale_edit.setSingleStep(0.05)
        self.scale_edit.setValue(settings.scale_factor)

        self.rules_edit = QTextEdit(settings.summary_rules_json)

        general = QWidget()
        fg = QFormLayout(general)
        fg.addRow("Одиниця summary", self.summary_unit_edit)

        paths = QWidget()
        fp = QFormLayout(paths)
        fp.addRow("Корінь джерел", self._path_row(self.source_dir_edit, self._browse_source_dir))
        fp.addRow("Каталог результату", self._path_row(self.output_dir_edit, self._browse_output_dir))
        fp.addRow("Файл індексу", self._path_row(self.index_file_edit, self._browse_index_file))

        theme = QWidget()
        ft = QFormLayout(theme)
        ft.addRow("Тема", self.theme_combo)
        ft.addRow("Акцент", self._accent_row())

        fonts = QWidget()
        ff = QFormLayout(fonts)
        ff.addRow("UI шрифт", self.ui_font_edit)
        ff.addRow("UI розмір", self.ui_font_size)
        ff.addRow("Preview шрифт", self.preview_font_edit)
        ff.addRow("Preview розмір", self.preview_font_size)
        ff.addRow("Масштаб", self.scale_edit)

        rules = QWidget()
        fr = QVBoxLayout(rules)
        fr.addWidget(self.rules_edit)

        self.tabs.addTab(general, "Загальні")
        self.tabs.addTab(paths, "Шляхи")
        self.tabs.addTab(theme, "Тема і кольори")
        self.tabs.addTab(fonts, "Шрифти і масштаб")
        self.tabs.addTab(rules, "Summary rules")

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply | QDialogButtonBox.RestoreDefaults)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self.buttons)

        self.accent_pick_btn.clicked.connect(self._pick_accent)
        self.accent_edit.textChanged.connect(self._update_accent_preview)
        self._update_accent_preview(self.accent_edit.text())

    def _path_row(self, edit: QLineEdit, callback) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("…")
        btn.setMaximumWidth(32)
        btn.clicked.connect(callback)
        lay.addWidget(edit)
        lay.addWidget(btn)
        return row

    def _accent_row(self) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.accent_edit)
        lay.addWidget(self.accent_preview)
        lay.addWidget(self.accent_pick_btn)
        return row

    def _browse_source_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Оберіть каталог джерел", self.source_dir_edit.text().strip() or ".")
        if path:
            self.source_dir_edit.setText(path)

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Оберіть каталог результату", self.output_dir_edit.text().strip() or ".")
        if path:
            self.output_dir_edit.setText(path)

    def _browse_index_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Оберіть файл індексу", self.index_file_edit.text().strip() or "index.sqlite3", "SQLite (*.sqlite3)")
        if path:
            self.index_file_edit.setText(path)

    def _pick_accent(self) -> None:
        selected = QColorDialog.getColor(QColor(self.accent_edit.text().strip() or "#3A7AFE"), self, "Оберіть accent color")
        if selected.isValid():
            self.accent_edit.setText(selected.name().upper())

    def _update_accent_preview(self, value: str) -> None:
        color = QColor(value.strip())
        swatch = color.name().upper() if color.isValid() else "#444444"
        self.accent_preview.setStyleSheet(f"background: {swatch}; border: 1px solid #999;")

    def validate(self) -> tuple[bool, str | None]:
        if not QColor(self.accent_edit.text().strip()).isValid():
            return False, "Некоректний accent color"
        if not (0.75 <= float(self.scale_edit.value()) <= 3.0):
            return False, "Scale має бути в межах 0.75..3.0"
        if not (8 <= int(self.ui_font_size.value()) <= 48):
            return False, "Некоректний UI font size"
        if not (8 <= int(self.preview_font_size.value()) <= 48):
            return False, "Некоректний preview font size"

        for label, value, must_exist in [
            ("source directory", self.source_dir_edit.text().strip(), True),
            ("output directory", self.output_dir_edit.text().strip(), False),
            ("index file", self.index_file_edit.text().strip(), False),
        ]:
            if not value:
                return False, f"Поле {label} не може бути порожнім"
            p = Path(value)
            if must_exist and not p.exists():
                return False, f"Шлях не існує: {value}"

        try:
            payload = json.loads(self.rules_edit.toPlainText() or "[]")
            if not isinstance(payload, list):
                return False, "Summary rules мають бути JSON-масивом"
        except Exception:
            return False, "Summary rules містять невалідний JSON"
        return True, None

    def build_settings(self, base: UserSettings) -> UserSettings:
        return UserSettings(
            theme_preset=self.theme_combo.currentText().strip() or "system",
            accent_color=QColor(self.accent_edit.text().strip()).name().upper(),
            ui_font_family=self.ui_font_edit.text().strip() or "Segoe UI",
            ui_font_size=int(self.ui_font_size.value()),
            preview_font_family=self.preview_font_edit.text().strip() or "Consolas",
            preview_font_size=int(self.preview_font_size.value()),
            scale_factor=float(self.scale_edit.value()),
            summary_unit=self.summary_unit_edit.text().strip() or "в/ч",
            summary_rules_json=self.rules_edit.toPlainText(),
            window_geometry_b64=base.window_geometry_b64,
            window_state_b64=base.window_state_b64,
            splitter_states_b64=dict(base.splitter_states_b64),
            last_selected_tab=base.last_selected_tab,
            last_search_text=base.last_search_text,
            recent_source_dirs=list(base.recent_source_dirs),
            recent_output_dirs=list(base.recent_output_dirs),
            recent_index_files=list(base.recent_index_files),
        )

    def build_config(self, base: AppConfig) -> AppConfig:
        return AppConfig(
            source_directory=self.source_dir_edit.text().strip(),
            output_directory=self.output_dir_edit.text().strip(),
            index_file=self.index_file_edit.text().strip(),
            theme_preset_default=base.theme_preset_default,
        )

    def load_from(self, settings: UserSettings, config: AppConfig) -> None:
        self.theme_combo.setCurrentText(settings.theme_preset)
        self.accent_edit.setText(settings.accent_color)
        self.ui_font_edit.setText(settings.ui_font_family)
        self.ui_font_size.setValue(settings.ui_font_size)
        self.preview_font_edit.setText(settings.preview_font_family)
        self.preview_font_size.setValue(settings.preview_font_size)
        self.scale_edit.setValue(settings.scale_factor)
        self.summary_unit_edit.setText(settings.summary_unit)
        self.rules_edit.setPlainText(settings.summary_rules_json)
        self.source_dir_edit.setText(config.source_directory)
        self.output_dir_edit.setText(config.output_directory)
        self.index_file_edit.setText(config.index_file)

    def show_validation_error(self, message: str) -> None:
        QMessageBox.warning(self, "Невалідні налаштування", message)
