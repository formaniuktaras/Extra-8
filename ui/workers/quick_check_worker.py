from __future__ import annotations

from services.indexing_service import CancellationToken
from ui.workers.base_worker import BaseWorker


class QuickCheckWorker(BaseWorker):
    def __init__(self, service) -> None:
        super().__init__()
        self.service = service
        self._token = CancellationToken()

    def request_cancel(self) -> None:
        super().request_cancel()
        self._token.cancel()

    def run(self) -> None:
        self.started.emit()
        self.statusChanged.emit("Швидка перевірка...")
        try:
            diff = self.service.quick_check(token=self._token)
            if self.is_cancel_requested():
                self.cancelled.emit()
                return
            self._emit_finished(
                {
                    "new": len(diff.new_files),
                    "changed": len(diff.changed_files),
                    "removed": len(diff.removed_source_keys),
                }
            )
        except RuntimeError as exc:
            if "cancelled" in str(exc).lower() or "скасовано" in str(exc).lower():
                self.cancelled.emit()
            else:
                self._emit_error(exc)
        except Exception as exc:
            self._emit_error(exc)
