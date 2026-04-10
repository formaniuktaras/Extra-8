from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QThread, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStatusBar, QTabWidget

from services.diagnostics_service import DiagnosticsService
from services.search_service import SearchService
from services.settings_service import SettingsService
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.diagnostics_dialog import DiagnosticsDialog
from ui.dialogs.progress_dialog import ProgressDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.models.extracts_list_model import ExtractsListModel
from ui.models.people_list_model import PeopleListModel
from ui.models.source_tree_model import SourceTreeModel
from ui.widgets.data_tab import DataTab
from ui.widgets.search_tab import SearchTab
from ui.workers.file_load_worker import FileLoadWorker
from ui.workers.indexing_worker import IndexingWorker
from ui.workers.quick_check_worker import QuickCheckWorker


class MainWindow(QMainWindow):
    def __init__(self, indexing_service, search_service: SearchService, diagnostics_service: DiagnosticsService, settings_service: SettingsService, source_root: Path) -> None:
        super().__init__()
        self.setWindowTitle("Індексація DOCX наказів")
        self.indexing_service = indexing_service
        self.search_service = search_service
        self.diagnostics_service = diagnostics_service
        self.settings_service = settings_service
        self.source_root = source_root

        self.people_model = PeopleListModel()
        self.extracts_model = ExtractsListModel()

        self.tabs = QTabWidget()
        self.search_tab = SearchTab()
        self.data_tab = DataTab()
        self.tabs.addTab(self.search_tab, "Пошук")
        self.tabs.addTab(self.data_tab, "Дані")
        self.setCentralWidget(self.tabs)
        self.setStatusBar(QStatusBar())

        self.search_tab.people_list.setModel(self.people_model)
        self.search_tab.extracts_list.setModel(self.extracts_model)
        self.source_model = SourceTreeModel(source_root)
        self.data_tab.tree.setModel(self.source_model)
        self.data_tab.tree.setRootIndex(self.source_model.index(str(source_root)))

        self.progress_dialog = ProgressDialog(self)
        self.search_debounce = QTimer(self)
        self.search_debounce.setInterval(250)
        self.search_debounce.setSingleShot(True)

        self._connect_signals()
        self._create_menu()

    def _create_menu(self) -> None:
        menu = self.menuBar().addMenu("Файл")
        act_settings = QAction("Налаштування", self)
        act_about = QAction("Про програму", self)
        menu.addAction(act_settings)
        menu.addAction(act_about)
        act_settings.triggered.connect(self.open_settings)
        act_about.triggered.connect(lambda: AboutDialog(self).exec())

    def _connect_signals(self) -> None:
        self.search_tab.queryChanged.connect(lambda _: self.search_debounce.start())
        self.search_debounce.timeout.connect(self.run_search)
        self.search_tab.people_list.clicked.connect(self.person_selected)
        self.search_tab.extracts_list.doubleClicked.connect(self.open_extract)
        self.search_tab.rebuildRequested.connect(self.rebuild_index)
        self.search_tab.quickCheckRequested.connect(self.quick_check)
        self.data_tab.tree.doubleClicked.connect(self.load_selected_file_preview)
        self.data_tab.diagnosticsRequested.connect(self.show_diagnostics)

    def run_search(self) -> None:
        items = self.search_service.search_people(self.search_tab.search_edit.text())
        self.people_model.set_items(items)

    def person_selected(self, index) -> None:
        data = index.data(role=0)
        row = index.data(role=256)
        if not row:
            return
        extracts = self.search_service.list_extracts(row["person_name_norm"])
        self.extracts_model.set_items(extracts)
        self.statusBar().showMessage(f"Особа: {data}")

    def open_extract(self, index) -> None:
        item = index.data(role=256)
        if item:
            path = Path(self.indexing_service.output_root) / item["generated_rel"]
            os.startfile(path) if os.name == "nt" else None

    def rebuild_index(self) -> None:
        self.progress_dialog.show()
        self.index_thread = QThread(self)
        self.index_worker = IndexingWorker(self.indexing_service)
        self.index_worker.moveToThread(self.index_thread)
        self.index_thread.started.connect(self.index_worker.run_full)
        self.index_worker.progressChanged.connect(self.on_index_progress)
        self.index_worker.finished.connect(self.index_thread.quit)
        self.index_worker.finished.connect(lambda: self.statusBar().showMessage("Індексацію завершено"))
        self.index_worker.errorOccurred.connect(lambda e: QMessageBox.critical(self, "Помилка", e))
        self.index_thread.start()

    def on_index_progress(self, phase: str, processed: int, total: int) -> None:
        self.progress_dialog.status_label.setText(phase)
        self.progress_dialog.progress.setMaximum(max(1, total))
        self.progress_dialog.progress.setValue(processed)
        self.progress_dialog.stats.setText(f"{processed} / {total}")

    def quick_check(self) -> None:
        self.quick_thread = QThread(self)
        self.quick_worker = QuickCheckWorker(self.indexing_service)
        self.quick_worker.moveToThread(self.quick_thread)
        self.quick_thread.started.connect(self.quick_worker.run)
        self.quick_worker.finished.connect(lambda d: self.statusBar().showMessage(f"Нові: {d['new']}, змінені: {d['changed']}, видалені: {d['removed']}"))
        self.quick_worker.finished.connect(self.quick_thread.quit)
        self.quick_worker.errorOccurred.connect(lambda e: QMessageBox.critical(self, "Помилка", e))
        self.quick_thread.start()

    def load_selected_file_preview(self, index) -> None:
        p = Path(self.source_model.filePath(index))
        if not p.is_file() or p.suffix.lower() != ".docx":
            return
        self.load_thread = QThread(self)
        self.load_worker = FileLoadWorker(p)
        self.load_worker.moveToThread(self.load_thread)
        self.load_thread.started.connect(self.load_worker.run)
        self.load_worker.finished.connect(self.data_tab.full_preview.setPlainText)
        self.load_worker.finished.connect(self.load_thread.quit)
        self.load_worker.errorOccurred.connect(lambda e: QMessageBox.warning(self, "Помилка", e))
        self.load_thread.start()

    def show_diagnostics(self) -> None:
        idx = self.data_tab.tree.currentIndex()
        p = Path(self.source_model.filePath(idx))
        if not p.is_file():
            return
        rel = p.relative_to(self.source_root).as_posix()
        report = self.diagnostics_service.diagnose_file(p, rel)
        DiagnosticsDialog(report, self).exec()

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.settings_service.settings, self)
        if dlg.exec():
            st = dlg.build_settings(self.settings_service.settings)
            self.settings_service.save(st)
