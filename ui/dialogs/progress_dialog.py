from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QProgressBar, QTextEdit, QVBoxLayout


class ProgressDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Прогрес індексації")
        self.status_label = QLabel("Очікування...")
        self.progress = QProgressBar()
        self.stats = QLabel("0 / 0")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.btn_cancel = QPushButton("Скасувати")
        self.btn_min = QPushButton("Згорнути")
        self.btn_copy = QPushButton("Копіювати помилки")

        btns = QHBoxLayout()
        btns.addWidget(self.btn_min)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_cancel)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.stats)
        layout.addWidget(self.log)
        layout.addLayout(btns)

    def append_log(self, text: str) -> None:
        self.log.append(text)
