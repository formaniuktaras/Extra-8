from __future__ import annotations

from pathlib import Path

from infra.docx.docx_reader import read_docx, render_plain_text
from ui.workers.base_worker import BaseWorker


class FileLoadWorker(BaseWorker):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def run(self) -> None:
        self.started.emit()
        self.statusChanged.emit("Завантаження документа")
        self.logMessage.emit(f"Читання файлу: {self.path}", "INFO")
        try:
            doc = read_docx(self.path)
            if self.is_cancel_requested():
                self.logMessage.emit("Завантаження скасовано", "WARN")
                self.cancelled.emit()
                return
            self._emit_finished(render_plain_text(doc))
        except Exception as exc:
            self._emit_error(exc)
