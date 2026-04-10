from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
)


class ProgressDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Прогрес індексації")
        self.setModal(False)
        self.status_label = QLabel("Очікування...")
        self.detail_label = QLabel("")
        self.progress = QProgressBar()
        self.stats = QLabel("0 / 0")
        self.metrics = QLabel("Elapsed: 0s | Throughput: 0/s | ETA: -")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.issues = QTextEdit()
        self.issues.setReadOnly(True)
        self.btn_cancel = QPushButton("Скасувати")
        self.btn_min = QPushButton("Згорнути в статус")
        self.btn_copy = QPushButton("Копіювати помилки")
        self.btn_save = QPushButton("Зберегти лог")

        btns = QHBoxLayout()
        btns.addWidget(self.btn_min)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.detail_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.stats)
        layout.addWidget(self.metrics)
        layout.addWidget(self.log)
        layout.addWidget(self.issues)
        layout.addLayout(btns)

    def reset(self, _state) -> None:
        self.status_label.setText("Індексація...")
        self.progress.setValue(0)
        self.progress.setMaximum(1)
        self.stats.setText("0 / 0")
        self.metrics.setText("Elapsed: 0s | Throughput: 0/s | ETA: -")
        self.log.clear()
        self.issues.clear()
        self.detail_label.setText("")
        self.btn_cancel.setEnabled(True)
        self.btn_copy.setEnabled(True)
        self.btn_save.setEnabled(True)

    def append_log(self, text: str, level: str = "INFO") -> None:
        self.log.append(f"[{level}] {text}")

    def append_error(self, text: str) -> None:
        self.issues.append(text)

    def update_state(self, state) -> None:
        self.progress.setMaximum(max(1, state.total))
        self.progress.setValue(state.processed)
        self.stats.setText(f"{state.processed} / {state.total}")
        eta = state.eta_seconds()
        eta_text = f"{eta:.1f}s" if eta is not None else "-"
        self.metrics.setText(
            f"Elapsed: {state.elapsed():.1f}s | Throughput: {state.throughput():.2f}/s | ETA: {eta_text}"
        )

    def copy_errors_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self.issues.toPlainText())

    def save_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти лог", str(Path.home() / "indexing-log.txt"), "Text (*.txt)")
        if not path:
            return
        Path(path).write_text(self.log.toPlainText() + "\n\n" + self.issues.toPlainText(), encoding="utf-8")

    def mark_completed(self) -> None:
        self.status_label.setText("Завершено")
        self.detail_label.setText("Операція успішно завершена")
        self.btn_cancel.setEnabled(False)

    def mark_cancelled(self, processed: int, total: int) -> None:
        self.status_label.setText("Скасовано")
        self.detail_label.setText(f"Оброблено: {processed}; Залишилось: {max(0, total - processed)}")
        self.btn_cancel.setEnabled(False)

    def mark_completed_with_errors(self, errors: list[str]) -> None:
        self.status_label.setText("Завершено з помилками")
        self.detail_label.setText(f"Кількість помилок: {len(errors)}")
        for err in errors:
            self.append_error(err)
        self.btn_cancel.setEnabled(False)
