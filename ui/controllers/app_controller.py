from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from services.preview_service import EXTRACT_UNAVAILABLE_TEXT, PreviewService, SOURCE_READ_ERROR_TEXT
from services.preview_types import StructuredPreview
from ui.models.progress_state import ProgressState
from ui.workers.indexing_worker import IndexingWorker
from ui.workers.quick_check_worker import QuickCheckWorker
from ui.workers.worker_manager import WorkerManager


class AppController(QObject):
    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self.win = main_window
        self.progress_state = ProgressState()
        self.worker_manager = WorkerManager()
        self._current_preview_source: Path | None = None
        self.preview_service = PreviewService(self.win.indexing_service.output_root)
        self.win.search_tab.extract_preview.setPlainText("Оберіть витяг")
        self.win.data_tab.full_preview.setPlainText("Оберіть документ")
        self._wire_signals()

    def _wire_signals(self) -> None:
        s = self.win.search_tab
        d = self.win.data_tab
        s.queryChanged.connect(lambda _: self.win.search_debounce.start())
        self.win.search_debounce.timeout.connect(self.run_search)
        s.people_list.clicked.connect(self.person_selected)
        s.extracts_list.clicked.connect(self.extract_selected)
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
        d.extractSelectionChanged.connect(self._data_extract_selected)
        d.highlightToggled.connect(self._data_highlight_toggled)

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
        if not extracts:
            self.win.search_tab.extract_preview.setPlainText("Оберіть витяг")
            self.win.search_tab.summary_preview.setPlainText("")
        self.win.statusBar().showMessage(f"Особа: {row['person_name']}. Витягів: {len(extracts)}")

    def extract_selected(self, index) -> None:
        item = index.data(role=256)
        if not item:
            self.win.search_tab.extract_preview.setPlainText("Оберіть витяг")
            self.win.search_tab.summary_preview.setPlainText("")
            return
        preview_text = self.preview_service.get_extract_preview(item)
        if not preview_text:
            preview_text = EXTRACT_UNAVAILABLE_TEXT
        self.win.search_tab.extract_preview.setPlainText(preview_text)
        self.win.search_tab.summary_preview.setPlainText(item.get("summary_text") or "")

    def open_source_docx_from_search(self) -> None:
        idx = self.win.search_tab.extracts_list.currentIndex()
        item = idx.data(role=256) if idx.isValid() else None
        if item and item.get("source_abs"):
            path = Path(item["source_abs"])
            if not path.exists():
                QMessageBox.warning(self.win, "Файл недоступний", f"Оригінальний файл не знайдено:\n{path}")
                return
            self._open_path(path)

    def open_folder_from_search(self) -> None:
        idx = self.win.search_tab.extracts_list.currentIndex()
        item = idx.data(role=256) if idx.isValid() else None
        if not item:
            return
        source_abs = item.get("source_abs")
        if source_abs:
            self._open_path(Path(source_abs).parent)

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
            if path.suffix.lower() == ".docx":
                source_key = path.relative_to(self.win.source_root).as_posix().lower()
                self.win.indexing_service.store.delete_document_by_source_key(source_key)
            self.win.indexing_service.file_ops.remove_file_and_prune_empty_dirs(path, self.win.source_root)
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

    def _start_worker(self, worker, slot_name: str, on_done: Callable[[], None] | None = None) -> None:
        thread = QThread(self.win)
        worker.moveToThread(thread)
        thread.started.connect(getattr(worker, slot_name))

        self.worker_manager.register(worker, thread)

        if on_done is not None:
            worker.finished.connect(lambda _result: on_done())
            worker.cancelled.connect(on_done)
            worker.errorOccurred.connect(lambda _m, _t: on_done())

        worker.errorOccurred.connect(self._on_worker_error)
        worker.statusChanged.connect(self._on_worker_status)
        worker.detailChanged.connect(self._on_worker_detail)
        worker.logMessage.connect(self._on_worker_log)
        worker.progressChanged.connect(self._on_worker_progress)
        worker.finished.connect(self._on_worker_finished)
        worker.cancelled.connect(self._on_worker_cancelled)

        thread.start()

    def rebuild_index(self) -> None:
        self.progress_state = ProgressState(status="Індексація...")
        self.win.progress_dialog.reset(self.progress_state)
        self.win.progress_dialog.show()
        worker = IndexingWorker(self.win.indexing_service)
        worker.finished.connect(lambda _r: self.win.statusBar().showMessage("Індексацію завершено"))
        worker.cancelled.connect(lambda: self.win.statusBar().showMessage("Індексацію скасовано"))
        self._start_worker(worker, "run_full")

    def quick_check(self) -> None:
        worker = QuickCheckWorker(self.win.indexing_service)
        worker.finished.connect(
            lambda d: self.win.statusBar().showMessage(f"Нові: {d['new']}, змінені: {d['changed']}, видалені: {d['removed']}")
        )
        self._start_worker(worker, "run")

    def cancel_current_worker(self) -> None:
        self.worker_manager.cancel_all()

    def _on_worker_status(self, text: str) -> None:
        self.progress_state.set_status(text)
        self.win.progress_dialog.refresh_ui()

    def _on_worker_detail(self, text: str) -> None:
        self.progress_state.set_detail(text)
        self.win.progress_dialog.refresh_ui()

    def _on_worker_log(self, message: str, level: str) -> None:
        self.progress_state.add_log(message, level)
        self.win.progress_dialog.refresh_ui()

    def _on_worker_progress(self, current: int, total: int) -> None:
        self.progress_state.set_progress(current, total)
        self.win.progress_dialog.refresh_ui()
        self.win.statusBar().showMessage(f"Індексація: {current}/{total}")

    def _on_worker_error(self, message: str, trace: str) -> None:
        self.progress_state.add_error(message)
        self.progress_state.add_log(trace, "ERROR")
        self.win.progress_dialog.refresh_ui()
        QMessageBox.critical(self.win, "Помилка", message)

    def _on_worker_finished(self, _result: object) -> None:
        self.progress_state.mark_finished()
        self.win.progress_dialog.refresh_ui()

    def _on_worker_cancelled(self) -> None:
        self.progress_state.mark_cancelled()
        remaining = max(0, self.progress_state.total - self.progress_state.current)
        self.progress_state.set_status("Скасовано")
        self.progress_state.set_detail(f"Оброблено: {self.progress_state.current}; Залишилось: {remaining}")
        self.win.progress_dialog.refresh_ui()

    def load_selected_file_preview(self, index) -> None:
        p = Path(self.win.source_model.filePath(index))
        if not p.is_file() or p.suffix.lower() != ".docx":
            return
        self._current_preview_source = p
        self.win.data_tab.full_preview.setPlainText("Завантаження...")
        full_text = self.preview_service.get_source_preview(p)
        self.win.data_tab.full_preview.setPlainText(full_text)
        self._load_extract_preview_for_path(p)

    def _load_extract_preview_for_path(self, source_path: Path) -> None:
        rel = source_path.relative_to(self.win.source_root).as_posix().lower()
        docs = self.win.search_service.list_extracts_for_source(rel)
        if not docs:
            self.win.data_tab.set_extract_items([])
            self.win.data_tab.extracts_info_label.setText("Для цього документа витягів не знайдено")
            self._render_source_preview(StructuredPreview(paragraphs=[], plain_text=self.preview_service.get_source_preview(source_path)))
            return
        self.win.data_tab.set_extract_items(docs)
        self._render_data_extract_by_index(0, source_path)

    def _data_extract_selected(self, idx: int) -> None:
        if self._current_preview_source is None:
            return
        self._render_data_extract_by_index(idx, self._current_preview_source)

    def _data_highlight_toggled(self, _enabled: bool) -> None:
        if self._current_preview_source is None:
            return
        self._render_data_extract_by_index(self.win.data_tab.extracts_list.currentRow(), self._current_preview_source)

    def _render_data_extract_by_index(self, idx: int, source_path: Path) -> None:
        extract = self.win.data_tab.current_extract(idx)
        if not extract:
            self.win.data_tab.set_extract_summary("", "")
            self._render_source_preview(self.preview_service.build_highlighted_source_preview(source_path, []))
            return
        self.win.data_tab.set_extract_summary(
            extract.get("person_name") or "",
            extract.get("summary_text") or "",
        )
        try:
            selected_indices = json.loads(extract.get("paragraphs_json") or "[]")
            if not isinstance(selected_indices, list):
                selected_indices = []
        except Exception:
            selected_indices = []
        structured = self.preview_service.build_highlighted_source_preview(source_path, selected_indices)
        self._render_source_preview(structured)

    def _render_source_preview(self, structured: StructuredPreview) -> None:
        panel = self.win.data_tab.full_preview
        panel.setPlainText(structured.plain_text or SOURCE_READ_ERROR_TEXT)
        if not self.win.data_tab.highlight_checkbox.isChecked() or not structured.paragraphs:
            return
        doc = panel.document()
        block = doc.begin()
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#fff2a8"))
        selected_flags = [p.is_selected for p in structured.paragraphs if p.text]
        index = 0
        while block.isValid() and index < len(selected_flags):
            if selected_flags[index]:
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.mergeCharFormat(highlight_format)
            index += 1
            block = block.next()
