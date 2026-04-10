from __future__ import annotations

from services.indexing_service import CancellationToken
from ui.workers.base_worker import BaseWorker


class IndexingWorker(BaseWorker):
    def __init__(self, service) -> None:
        super().__init__()
        self.service = service
        self._token = CancellationToken()

    def request_cancel(self) -> None:
        super().request_cancel()
        self._token.cancel()

    def run_full(self) -> None:
        self.started.emit()
        self.statusChanged.emit("Індексація...")
        try:
            def on_progress(_phase: str, processed: int, total: int) -> None:
                if self.is_cancel_requested():
                    self._token.cancel()
                self.progressChanged.emit(processed, total)

            self.service.full_rebuild(on_progress=on_progress, token=self._token)
            if self.is_cancel_requested():
                self.cancelled.emit()
                return
            self._emit_finished({"status": "ok"})
        except RuntimeError as exc:
            if "cancelled" in str(exc).lower() or "скасовано" in str(exc).lower():
                self.cancelled.emit()
            else:
                self._emit_error(exc)
        except Exception as exc:
            self._emit_error(exc)
