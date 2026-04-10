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
        self.state = None
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

    def reset(self, state) -> None:
        self.state = state
        self.btn_cancel.setEnabled(True)
        self.btn_copy.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.refresh_ui()

    def refresh_ui(self) -> None:
        if self.state is None:
            return

        state = self.state
        self.status_label.setText(state.status)
        self.detail_label.setText(state.detail)
        self.progress.setMaximum(max(1, state.total))
        self.progress.setValue(state.current)
        self.stats.setText(f"{state.current} / {state.total}")

        eta = state.eta_seconds()
        eta_text = f"{eta:.1f}s" if eta is not None else "-"
        self.metrics.setText(
            f"Elapsed: {state.elapsed():.1f}s | Throughput: {state.throughput():.2f}/s | ETA: {eta_text}"
        )

        self.log.setPlainText("\n".join(state.log_lines))

        issue_lines = []
        if state.warnings:
            issue_lines.append("Warnings:")
            issue_lines.extend(state.warnings)
        if state.errors:
            if issue_lines:
                issue_lines.append("")
            issue_lines.append("Errors:")
            issue_lines.extend(state.errors)
        self.issues.setPlainText("\n".join(issue_lines))

        if state.is_finished or state.is_cancelled:
            self.btn_cancel.setEnabled(False)

    def copy_errors_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self.issues.toPlainText())

    def save_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти лог", str(Path.home() / "indexing-log.txt"), "Text (*.txt)")
        if not path:
            return
        Path(path).write_text(self.log.toPlainText() + "\n\n" + self.issues.toPlainText(), encoding="utf-8")
