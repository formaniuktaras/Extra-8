from __future__ import annotations

import traceback
from typing import Any

from PySide6.QtCore import QObject, Signal


class BaseWorker(QObject):
    started = Signal()
    statusChanged = Signal(str)
    progressChanged = Signal(int, int)
    detailChanged = Signal(str)
    logMessage = Signal(str, str)
    errorOccurred = Signal(str, str)
    finished = Signal(object)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__(parent=None)
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested

    def _emit_error(self, exc: Exception) -> None:
        self.errorOccurred.emit(str(exc), traceback.format_exc())

    def _emit_finished(self, result: Any = None) -> None:
        self.finished.emit(result)
