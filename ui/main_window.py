from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStatusBar

from core.settings import decode_bytes, encode_bytes
from services.app_config_service import AppConfigService
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
from ui.theme_manager import ThemeManager
from ui.widgets.data_tab import DataTab
from ui.widgets.search_tab import SearchTab

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        indexing_service,
        search_service: SearchService,
        diagnostics_service: DiagnosticsService,
        settings_service: SettingsService,
        app_config_service: AppConfigService,
        source_root: Path,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Індексація DOCX наказів")
        self.indexing_service = indexing_service
        self.search_service = search_service
        self.diagnostics_service = diagnostics_service
        self.settings_service = settings_service
        self.app_config_service = app_config_service
        self.theme_manager = ThemeManager(QApplication.instance())
        self.source_root = source_root

        self.people_model = PeopleListModel()
        self.extracts_model = ExtractsListModel()

        from PySide6.QtWidgets import QTabWidget

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
        self._restore_ui_state()

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

    def _validate_and_apply_from_dialog(self, dlg: SettingsDialog, persist: bool) -> bool:
        ok, error = dlg.validate()
        if not ok:
            dlg.show_validation_error(error or "Невалідні налаштування")
            return False

        new_settings = dlg.build_settings(self.settings_service.settings)
        new_config = dlg.build_config(self.app_config_service.config)

        self.theme_manager.apply(new_settings, self)
        self.search_tab.theme_combo.blockSignals(True)
        self.search_tab.theme_combo.setCurrentText(new_settings.theme_preset)
        self.search_tab.theme_combo.blockSignals(False)

        if persist:
            self.settings_service.add_recent_source_dir(new_config.source_directory)
            self.settings_service.add_recent_output_dir(new_config.output_directory)
            self.settings_service.add_recent_index_file(new_config.index_file)
            new_settings.recent_source_dirs = self.settings_service.settings.recent_source_dirs
            new_settings.recent_output_dirs = self.settings_service.settings.recent_output_dirs
            new_settings.recent_index_files = self.settings_service.settings.recent_index_files
            saved, reason = self.settings_service.try_save(new_settings)
            if not saved:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти settings: {reason or 'невідома помилка'}")
                return False
            try:
                self.app_config_service.save(new_config)
            except Exception as exc:
                logger.exception("Failed to save app config")
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти config: {exc}")
                return False
            self._apply_runtime_paths()
        return True

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.settings_service.settings, self.app_config_service.config, self)
        apply_btn = dlg.buttons.button(dlg.buttons.StandardButton.Apply)
        restore_btn = dlg.buttons.button(dlg.buttons.StandardButton.RestoreDefaults)

        apply_btn.clicked.connect(lambda: self._validate_and_apply_from_dialog(dlg, persist=True))
        restore_btn.clicked.connect(lambda: dlg.load_from(type(self.settings_service.settings)(), self.app_config_service.config))

        dlg.theme_combo.currentTextChanged.connect(lambda _v: self._validate_and_apply_from_dialog(dlg, persist=False))
        dlg.accent_edit.textChanged.connect(lambda _v: self._validate_and_apply_from_dialog(dlg, persist=False))
        dlg.ui_font_edit.textChanged.connect(lambda _v: self._validate_and_apply_from_dialog(dlg, persist=False))
        dlg.ui_font_size.valueChanged.connect(lambda _v: self._validate_and_apply_from_dialog(dlg, persist=False))
        dlg.preview_font_edit.textChanged.connect(lambda _v: self._validate_and_apply_from_dialog(dlg, persist=False))
        dlg.preview_font_size.valueChanged.connect(lambda _v: self._validate_and_apply_from_dialog(dlg, persist=False))
        dlg.scale_edit.valueChanged.connect(lambda _v: self._validate_and_apply_from_dialog(dlg, persist=False))

        if dlg.exec() and not self._validate_and_apply_from_dialog(dlg, persist=True):
            return

    def _apply_runtime_paths(self) -> None:
        source_root, output_root, _db_path = self.app_config_service.resolve_paths()
        source_root.mkdir(parents=True, exist_ok=True)
        output_root.mkdir(parents=True, exist_ok=True)
        self.source_root = source_root
        self.indexing_service.source_root = source_root
        self.indexing_service.output_root = output_root
        self.controller.preview_service.output_root = output_root
        self.source_model.setRootPath(str(source_root))
        self.data_tab.tree.setRootIndex(self.source_model.index(str(source_root)))

    def _theme_changed_from_search(self, theme: str) -> None:
        st = self.settings_service.settings
        st.theme_preset = theme
        self.theme_manager.apply(st, self)
        self.settings_service.save(st)

    def _restore_ui_state(self) -> None:
        st = self.settings_service.settings
        try:
            if st.window_geometry_b64:
                self.restoreGeometry(decode_bytes(st.window_geometry_b64))
            if st.window_state_b64:
                self.restoreState(decode_bytes(st.window_state_b64))
            if st.splitter_states_b64:
                if self.search_tab.center_splitter.objectName() in st.splitter_states_b64:
                    self.search_tab.center_splitter.restoreState(decode_bytes(st.splitter_states_b64[self.search_tab.center_splitter.objectName()]))
                if self.search_tab.right_splitter.objectName() in st.splitter_states_b64:
                    self.search_tab.right_splitter.restoreState(decode_bytes(st.splitter_states_b64[self.search_tab.right_splitter.objectName()]))
                if self.data_tab.main_splitter.objectName() in st.splitter_states_b64:
                    self.data_tab.main_splitter.restoreState(decode_bytes(st.splitter_states_b64[self.data_tab.main_splitter.objectName()]))
                if self.data_tab.right_splitter.objectName() in st.splitter_states_b64:
                    self.data_tab.right_splitter.restoreState(decode_bytes(st.splitter_states_b64[self.data_tab.right_splitter.objectName()]))
        except Exception:
            logger.exception("Failed to restore window UI state")

        self.tabs.setCurrentIndex(max(0, min(st.last_selected_tab, self.tabs.count() - 1)))
        self.search_tab.search_edit.setText(st.last_search_text)

    def _persist_ui_state(self) -> None:
        st = self.settings_service.settings
        st.window_geometry_b64 = encode_bytes(self.saveGeometry().data())
        st.window_state_b64 = encode_bytes(self.saveState().data())
        st.splitter_states_b64 = {
            self.search_tab.center_splitter.objectName(): encode_bytes(self.search_tab.center_splitter.saveState().data()),
            self.search_tab.right_splitter.objectName(): encode_bytes(self.search_tab.right_splitter.saveState().data()),
            self.data_tab.main_splitter.objectName(): encode_bytes(self.data_tab.main_splitter.saveState().data()),
            self.data_tab.right_splitter.objectName(): encode_bytes(self.data_tab.right_splitter.saveState().data()),
        }
        self.settings_service.capture_session_state(last_tab=self.tabs.currentIndex(), search_text=self.search_tab.search_edit.text())
        self.settings_service.save(st)

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self._persist_ui_state()
        except Exception:
            logger.exception("Failed to persist window UI state")
        super().closeEvent(event)
