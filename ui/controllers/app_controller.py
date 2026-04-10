from __future__ import annotations

import json
import shutil
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from infra.docx.docx_reader import read_docx
from ui.workers.file_load_worker import FileLoadWorker
from ui.workers.indexing_worker import IndexingWorker
from ui.workers.quick_check_worker import QuickCheckWorker


@dataclass(slots=True)
class ProgressState:
    started_at: float = field(default_factory=time.monotonic)
    processed: int = 0
    total: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)

    def elapsed(self) -> float:
        return max(0.0, time.monotonic() - self.started_at)

    def throughput(self) -> float:
        elapsed = self.elapsed()
        return self.processed / elapsed if elapsed > 0 else 0.0

    def eta_seconds(self) -> float | None:
        if self.total <= 0 or self.processed <= 0:
            return None
        rate = self.throughput()
        if rate <= 0:
            return None
        return max(0.0, (self.total - self.processed) / rate)


class AppController(QObject):
    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self.win = main_window
        self.progress_state = ProgressState()
        self._index_worker: IndexingWorker | None = None
        self._quick_worker: QuickCheckWorker | None = None
        self._load_worker: FileLoadWorker | None = None
        self._thread: QThread | None = None
        self._wire_signals()

    def _wire_signals(self) -> None:
        s = self.win.search_tab
        d = self.win.data_tab
        s.queryChanged.connect(lambda _: self.win.search_debounce.start())
        self.win.search_debounce.timeout.connect(self.run_search)
        s.people_list.clicked.connect(self.person_selected)
        s.extracts_list.clicked.connect(self.extract_selected)
        s.extracts_list.doubleClicked.connect(self.open_generated_extract)
        s.rebuildRequested.connect(self.rebuild_index)
        s.quickCheckRequested.connect(self.quick_check)
        s.openSourceRequested.connect(self.open_source_docx_from_search)
        s.openFolderRequested.connect(self.open_folder_from_search)

        d.tree.doubleClicked.connect(self.load_selected_file_preview)
        d.refreshRequested.connect(self.refresh_tree)
        d.openRequested.connect(self.open_selected_source_file)
        d.diagnosticsRequested.connect(self.show_diagnostics)
        d.addFilesRequested.connect(self.add_files)
        d.newFolderRequested.connect(self.create_folder)
        d.renameRequested.connect(self.rename_selected)
        d.deleteRequested.connect(self.delete_selected)
        d.openFolderRequested.connect(self.open_selected_containing_folder)

        self.win.progress_dialog.btn_cancel.clicked.connect(self.cancel_current_worker)
        self.win.progress_dialog.btn_copy.clicked.connect(self.win.progress_dialog.copy_errors_to_clipboard)
        self.win.progress_dialog.btn_save.clicked.connect(self.win.progress_dialog.save_log)
        self.win.progress_dialog.btn_min.clicked.connect(self.win.progress_dialog.hide)

    def _ensure_under_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.win.source_root.resolve())
            return True
        except Exception:
            return False

    def run_search(self) -> None:
        items = self.win.search_service.search_people(self.win.search_tab.search_edit.text())
        self.win.people_model.set_items(items)
        self.win.search_tab.set_people_count(len(items))

    def person_selected(self, index) -> None:
        row = index.data(role=256)
        if not row:
            return
        extracts = self.win.search_service.list_extracts(row["person_name_norm"])
        self.win.extracts_model.set_items(extracts)
        self.win.statusBar().showMessage(f"Особа: {row['person_name']}. Витягів: {len(extracts)}")

    def extract_selected(self, index) -> None:
        item = index.data(role=256)
        if not item:
            return
        extract_path = Path(self.win.indexing_service.output_root) / item["generated_rel"]
        if extract_path.exists():
            self.win.search_tab.extract_preview.setPlainText(str(extract_path))
        self.win.search_tab.summary_preview.setPlainText(item.get("summary_text") or "")

    def open_generated_extract(self, index) -> None:
        item = index.data(role=256)
        if item:
            self._open_path(Path(self.win.indexing_service.output_root) / item["generated_rel"])

    def open_source_docx_from_search(self) -> None:
        idx = self.win.search_tab.extracts_list.currentIndex()
        item = idx.data(role=256) if idx.isValid() else None
        if item and item.get("source_abs"):
            self._open_path(Path(item["source_abs"]))

    def open_folder_from_search(self) -> None:
        idx = self.win.search_tab.extracts_list.currentIndex()
        item = idx.data(role=256) if idx.isValid() else None
        if not item:
            return
        path = Path(item.get("source_abs") or (Path(self.win.indexing_service.output_root) / item["generated_rel"]))
        self._open_path(path.parent)

    def refresh_tree(self) -> None:
        self.win.source_model.setRootPath(str(self.win.source_root))

    def open_selected_source_file(self) -> None:
        idx = self.win.data_tab.tree.currentIndex()
        if not idx.isValid():
            return
        path = Path(self.win.source_model.filePath(idx))
        if path.exists() and path.is_file() and self._ensure_under_root(path):
            self._open_path(path)

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self.win, "Додати DOCX", str(self.win.source_root), "DOCX Files (*.docx)")
        for p in [Path(x) for x in files]:
            if p.exists() and p.is_file():
                target = self.win.source_root / p.name
                if target != p:
                    shutil.copy2(p, target)
        self.refresh_tree()

    def create_folder(self) -> None:
        name, ok = QInputDialog.getText(self.win, "Нова папка", "Назва папки")
        if ok and name.strip():
            (self.win.source_root / name.strip()).mkdir(parents=True, exist_ok=True)
            self.refresh_tree()

    def rename_selected(self) -> None:
        idx = self.win.data_tab.tree.currentIndex()
        if not idx.isValid():
            return
        src = Path(self.win.source_model.filePath(idx))
        if not self._ensure_under_root(src):
            return
        name, ok = QInputDialog.getText(self.win, "Перейменувати", "Нова назва", text=src.name)
        if ok and name.strip():
            src.rename(src.with_name(name.strip()))
            self.refresh_tree()

    def delete_selected(self) -> None:
        idx = self.win.data_tab.tree.currentIndex()
        if not idx.isValid():
            return
        path = Path(self.win.source_model.filePath(idx))
        if not self._ensure_under_root(path):
            return
        if QMessageBox.question(self.win, "Видалення", f"Видалити {path.name}?") != QMessageBox.Yes:
            return
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        self.refresh_tree()

    def open_selected_containing_folder(self) -> None:
        idx = self.win.data_tab.tree.currentIndex()
        if not idx.isValid():
            return
        path = Path(self.win.source_model.filePath(idx))
        self._open_path(path.parent if path.is_file() else path)

    def _open_path(self, path: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def show_diagnostics(self) -> None:
        self.win.show_diagnostics()

    def _start_worker(self, worker, slot_name: str) -> None:
        self._thread = QThread(self.win)
        worker.moveToThread(self._thread)
        self._thread.started.connect(getattr(worker, slot_name))
        worker.finished.connect(self._thread.quit)
        worker.cancelled.connect(self._thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        worker.errorOccurred.connect(self._on_worker_error)
        worker.logMessage.connect(lambda m, _lvl: self.win.progress_dialog.append_log(m))
        worker.progressChanged.connect(self._on_worker_progress)
        self._thread.start()

    def rebuild_index(self) -> None:
        self.progress_state = ProgressState()
        self.win.progress_dialog.reset(self.progress_state)
        self.win.progress_dialog.show()
        self._index_worker = IndexingWorker(self.win.indexing_service)
        self._index_worker.finished.connect(lambda _r: self.win.statusBar().showMessage("Індексацію завершено"))
        self._index_worker.finished.connect(lambda _r: self.win.progress_dialog.mark_completed())
        self._index_worker.cancelled.connect(lambda: self.win.statusBar().showMessage("Індексацію скасовано"))
        self._start_worker(self._index_worker, "run_full")

    def quick_check(self) -> None:
        self._quick_worker = QuickCheckWorker(self.win.indexing_service)
        self._quick_worker.finished.connect(
            lambda d: self.win.statusBar().showMessage(f"Нові: {d['new']}, змінені: {d['changed']}, видалені: {d['removed']}")
        )
        self._start_worker(self._quick_worker, "run")

    def cancel_current_worker(self) -> None:
        for worker in [self._index_worker, self._quick_worker, self._load_worker]:
            if worker is not None:
                worker.request_cancel()

    def _on_worker_progress(self, processed: int, total: int) -> None:
        self.progress_state.processed = processed
        self.progress_state.total = total
        self.win.progress_dialog.update_state(self.progress_state)
        self.win.statusBar().showMessage(f"Індексація: {processed}/{total}")

    def _on_worker_error(self, message: str, trace: str) -> None:
        self.progress_state.errors.append(message)
        self.win.progress_dialog.append_error(message)
        self.win.progress_dialog.append_log(trace)
        QMessageBox.critical(self.win, "Помилка", message)

    def load_selected_file_preview(self, index) -> None:
        p = Path(self.win.source_model.filePath(index))
        if not p.is_file() or p.suffix.lower() != ".docx":
            return
        self._load_worker = FileLoadWorker(p)
        self._load_worker.finished.connect(lambda txt: self.win.data_tab.full_preview.setPlainText(txt))
        self._load_worker.finished.connect(lambda _txt: self._load_extract_preview_for_path(p))
        self._start_worker(self._load_worker, "run")

    def _load_extract_preview_for_path(self, source_path: Path) -> None:
        rel = source_path.relative_to(self.win.source_root).as_posix().lower()
        docs = self.win.search_service.list_extracts_for_source(rel)
        if not docs:
            self.win.data_tab.extract_preview.setPlainText("")
            return
        first = docs[0]
        indices = json.loads(first.get("paragraphs_json", "[]"))
        src_doc = read_docx(source_path)
        selected = [p.text for p in src_doc.paragraphs if p.block_index in set(indices)]
        self.win.data_tab.extract_preview.setPlainText("\n".join(selected))

