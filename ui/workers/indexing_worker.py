from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class IndexingWorker(QObject):
    progressChanged = Signal(str, int, int)
    statusChanged = Signal(str)
    logMessage = Signal(str)
    finished = Signal()
    errorOccurred = Signal(str)

    def __init__(self, service) -> None:
        super().__init__()
        self.service = service
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run_full(self) -> None:
        try:
            self.statusChanged.emit("Індексація...")

            def on_progress(phase: str, processed: int, total: int) -> None:
                if self._cancelled:
                    raise RuntimeError("Скасовано")
                self.progressChanged.emit(phase, processed, total)

            self.service.full_rebuild(on_progress)
            self.finished.emit()
        except Exception as exc:
            self.errorOccurred.emit(str(exc))
