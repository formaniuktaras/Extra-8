from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QStatusBar, QTabWidget

from services.diagnostics_service import DiagnosticsService
from services.search_service import SearchService
from services.settings_service import SettingsService
from ui.controllers.app_controller import AppController
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.diagnostics_dialog import DiagnosticsDialog
from ui.dialogs.progress_dialog import ProgressDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.models.extracts_list_model import ExtractsListModel
from ui.models.people_list_model import PeopleListModel
from ui.models.source_tree_model import SourceTreeModel
from ui.widgets.data_tab import DataTab
from ui.widgets.search_tab import SearchTab


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

        self._create_menu()
        self.controller = AppController(self)

    def _create_menu(self) -> None:
        menu = self.menuBar().addMenu("Файл")
        act_settings = QAction("Налаштування", self)
        act_about = QAction("Про програму", self)
        menu.addAction(act_settings)
        menu.addAction(act_about)
        act_settings.triggered.connect(self.open_settings)
        act_about.triggered.connect(lambda: AboutDialog(self).exec())

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
