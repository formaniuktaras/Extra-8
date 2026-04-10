from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class QuickCheckWorker(QObject):
    finished = Signal(dict)
    errorOccurred = Signal(str)

    def __init__(self, service) -> None:
        super().__init__()
        self.service = service

    def run(self) -> None:
        try:
            diff = self.service.quick_check()
            self.finished.emit(
                {
                    "new": len(diff.new_files),
                    "changed": len(diff.changed_files),
                    "removed": len(diff.removed_source_keys),
                }
            )
        except Exception as exc:
            self.errorOccurred.emit(str(exc))
