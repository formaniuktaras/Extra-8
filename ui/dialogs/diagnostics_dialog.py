from __future__ import annotations

from PySide6.QtWidgets import QDialog, QTextEdit, QVBoxLayout

from domain.models import DiagnosticsReport


class DiagnosticsDialog(QDialog):
    def __init__(self, report: DiagnosticsReport, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Діагностика файлу")
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(
            "\n".join(
                [
                    f"Файл: {report.source_rel}",
                    f"Усього абзаців: {report.total_paragraphs}",
                    f"Абзаців body: {report.body_paragraphs}",
                    f"Імена: {', '.join(report.unique_names)}",
                    f"К-сть блоків: {report.blocks_count}",
                    f"Приклади: {report.matched_examples}",
                    f"Uppercase hints: {report.uppercase_hints}",
                    f"Помилка: {report.error_text or '-'}",
                ]
            )
        )
        layout = QVBoxLayout(self)
        layout.addWidget(txt)
