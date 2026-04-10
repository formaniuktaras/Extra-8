from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from infra.docx.docx_reader import read_docx, render_plain_text


class FileLoadWorker(QObject):
    finished = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def run(self) -> None:
        try:
            doc = read_docx(self.path)
            self.finished.emit(render_plain_text(doc))
        except Exception as exc:
            self.errorOccurred.emit(str(exc))
