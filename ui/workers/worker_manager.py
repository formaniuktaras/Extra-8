from __future__ import annotations

from collections.abc import Iterable


class WorkerManager:
    def __init__(self) -> None:
        self._workers: set[object] = set()
        self._threads: dict[object, object] = {}
        self._cleaned_workers: set[int] = set()

    def register(self, worker, thread) -> None:
        self._workers.add(worker)
        self._threads[worker] = thread
        worker.finished.connect(lambda _result=None, w=worker: self.cleanup(w))
        worker.cancelled.connect(lambda w=worker: self.cleanup(w))
        worker.errorOccurred.connect(lambda _m, _t, w=worker: self.cleanup(w))

    def cleanup(self, worker) -> None:
        worker_id = id(worker)
        if worker_id in self._cleaned_workers:
            return
        self._cleaned_workers.add(worker_id)

        thread = self._threads.pop(worker, None)
        self._workers.discard(worker)

        if thread is not None:
            thread.quit()
            worker.deleteLater()
            thread.deleteLater()

    def cancel_all(self) -> None:
        for worker in list(self._workers):
            cancel = getattr(worker, "cancel", None)
            if callable(cancel):
                cancel()

    def active_workers(self) -> list[object]:
        return list(self._workers)

    def iter_threads(self) -> Iterable[object]:
        return self._threads.values()
