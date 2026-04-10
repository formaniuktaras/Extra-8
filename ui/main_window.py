from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QStatusBar, QTabWidget

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
from ui.theme_manager import ThemeManager


class MainWindow(QMainWindow):
    def __init__(self, indexing_service, search_service: SearchService, diagnostics_service: DiagnosticsService, settings_service: SettingsService, source_root: Path) -> None:
        super().__init__()
        self.setWindowTitle("Індексація DOCX наказів")
        self.indexing_service = indexing_service
        self.search_service = search_service
        self.diagnostics_service = diagnostics_service
        self.settings_service = settings_service
        self.theme_manager = ThemeManager(QApplication.instance())
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
        self.theme_manager.apply(self.settings_service.settings, self)
        self.search_tab.theme_combo.setCurrentText(self.settings_service.settings.theme_preset)
        self.search_tab.theme_combo.currentTextChanged.connect(self._theme_changed_from_search)

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
        dlg.btn_apply.clicked.connect(lambda: self._apply_settings_dialog(dlg, persist=True))
        dlg.btn_restore.clicked.connect(lambda: self._restore_defaults(dlg))
        dlg.theme_combo.currentTextChanged.connect(lambda: self._apply_settings_dialog(dlg, persist=False))
        dlg.font_edit.textChanged.connect(lambda _v: self._apply_settings_dialog(dlg, persist=False))
        dlg.font_size.valueChanged.connect(lambda _v: self._apply_settings_dialog(dlg, persist=False))
        dlg.scale_edit.valueChanged.connect(lambda _v: self._apply_settings_dialog(dlg, persist=False))
        if dlg.exec():
            self._apply_settings_dialog(dlg, persist=True)

    def _apply_settings_dialog(self, dlg: SettingsDialog, persist: bool) -> None:
        st = dlg.build_settings(self.settings_service.settings)
        self.theme_manager.apply(st, self)
        self.search_tab.theme_combo.setCurrentText(st.theme_preset)
        if persist:
            self.settings_service.save(st)

    def _restore_defaults(self, dlg: SettingsDialog) -> None:
        defaults = self.settings_service.restore_defaults()
        dlg.load_from(defaults)
        self.theme_manager.apply(defaults, self)
        self.search_tab.theme_combo.setCurrentText(defaults.theme_preset)

    def _theme_changed_from_search(self, theme: str) -> None:
        st = self.settings_service.settings
        st.theme_preset = theme
        self.theme_manager.apply(st, self)
        self.settings_service.save(st)
