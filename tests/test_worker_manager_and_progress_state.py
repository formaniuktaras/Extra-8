from ui.models.progress_state import ProgressState
from ui.workers.worker_manager import WorkerManager


class Signal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs) -> None:
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class MockWorker:
    def __init__(self) -> None:
        self.finished = Signal()
        self.cancelled = Signal()
        self.errorOccurred = Signal()
        self.cancel_calls = 0
        self.delete_later_calls = 0

    def cancel(self) -> None:
        self.cancel_calls += 1

    def deleteLater(self) -> None:
        self.delete_later_calls += 1


class MockThread:
    def __init__(self) -> None:
        self.quit_calls = 0
        self.delete_later_calls = 0

    def quit(self) -> None:
        self.quit_calls += 1

    def deleteLater(self) -> None:
        self.delete_later_calls += 1


def test_worker_manager_cleanup() -> None:
    manager = WorkerManager()
    worker = MockWorker()
    thread = MockThread()

    manager.register(worker, thread)
    assert manager.active_workers() == [worker]

    worker.finished.emit({"ok": True})

    assert manager.active_workers() == []
    assert worker.delete_later_calls == 1
    assert thread.quit_calls == 1
    assert thread.delete_later_calls == 1

    manager.cleanup(worker)
    assert worker.delete_later_calls == 1
    assert thread.quit_calls == 1


def test_cancel_all() -> None:
    manager = WorkerManager()
    worker_a = MockWorker()
    worker_b = MockWorker()
    thread_a = MockThread()
    thread_b = MockThread()

    manager.register(worker_a, thread_a)
    manager.register(worker_b, thread_b)

    manager.cancel_all()

    assert worker_a.cancel_calls == 1
    assert worker_b.cancel_calls == 1


def test_progress_state_updates() -> None:
    state = ProgressState()

    state.add_log("Step started")
    state.add_warning("Potential issue")
    state.add_error("Fatal issue")
    state.set_status("Processing")
    state.set_detail("Running")
    state.set_progress(3, 10)

    assert state.status == "Processing"
    assert state.detail == "Running"
    assert state.current == 3
    assert state.total == 10
    assert "[INFO] Step started" in state.log_lines
    assert "Potential issue" in state.warnings
    assert "Fatal issue" in state.errors

    state.mark_finished()
    assert state.is_finished is True
    assert state.is_cancelled is False

    state.mark_cancelled()
    assert state.is_cancelled is True
    assert state.is_finished is False
