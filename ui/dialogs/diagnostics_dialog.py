from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout

from domain.models import DiagnosticsReport


class DiagnosticsDialog(QDialog):
    def __init__(self, report: DiagnosticsReport, parent=None) -> None:
        super().__init__(parent)
        self.report = report
        self.setWindowTitle("Діагностика файлу")
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setPlainText(self._build_report_text())
        self.btn_copy = QPushButton("Копіювати")
        self.btn_export = QPushButton("Експорт JSON")
        controls = QHBoxLayout()
        controls.addWidget(self.btn_copy)
        controls.addWidget(self.btn_export)
        layout = QVBoxLayout(self)
        layout.addWidget(self.txt)
        layout.addLayout(controls)
        self.btn_copy.clicked.connect(self._copy_report)
        self.btn_export.clicked.connect(self._export_report)

    def _build_report_text(self) -> str:
        report = self.report
        return "\n".join(
            [
                f"Файл: {report.source_rel}",
                f"Абсолютний шлях: {report.source_abs}",
                f"Розмір: {report.file_size} bytes",
                f"mtime: {report.mtime}",
                f"styles.xml: {'так' if report.has_styles_xml else 'ні'}",
                f"numbering.xml: {'так' if report.has_numbering_xml else 'ні'}",
                f"Усього абзаців: {report.total_paragraphs}",
                f"Абзаців body: {report.body_paragraphs}",
                f"Індекси абзаців: {report.paragraph_indices}",
                f"Matched indices: {report.matched_indices}",
                f"Імена: {', '.join(report.unique_names)}",
                f"К-сть блоків: {report.blocks_count}",
                f"Приклади: {report.matched_examples}",
                f"Uppercase hints: {report.uppercase_hints}",
                f"Помилка: {report.error_text or '-'}",
            ]
        )

    def _copy_report(self) -> None:
        QGuiApplication.clipboard().setText(self.txt.toPlainText())

    def _export_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Експорт діагностики", str(Path.home() / "diagnostics.json"), "JSON (*.json)")
        if not path:
            return
        Path(path).write_text(json.dumps(asdict(self.report), ensure_ascii=False, indent=2), encoding="utf-8")
