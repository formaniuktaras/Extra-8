from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QPushButton = QtWidgets.QPushButton
QWidget = QtWidgets.QWidget

from core.config import AppConfig
from core.settings import SettingsManager, UserSettings, encode_bytes
from services.extract_service import ExtractService
from services.settings_service import SettingsService
from ui.controllers.app_controller import AppController
from ui.dialogs.settings_dialog import SettingsDialog
from ui.theme_manager import ThemeManager
from ui.widgets.preview_panel import PreviewPanel


class _FakeDialog:
    def __init__(self, *_args, **_kwargs):
        self._exec_result = 0

    def exec(self):
        return self._exec_result


def test_build_settings_includes_all_live_font_controls(qapp):
    base = UserSettings()
    cfg = AppConfig(source_directory="./source", output_directory="./output", index_file="./index.sqlite3")
    dlg = SettingsDialog(base, cfg)

    dlg.theme_combo.setCurrentText("dark")
    dlg.accent_edit.setText("#112233")
    dlg.ui_font_edit.setText("Arial")
    dlg.ui_font_size.setValue(13)
    dlg.preview_font_edit.setText("Courier New")
    dlg.preview_font_size.setValue(15)
    dlg.scale_edit.setValue(1.25)
    dlg.summary_unit_edit.setText("бригада")
    dlg.rules_edit.setPlainText("[]")

    settings = dlg.build_settings(base)
    assert settings.theme_preset == "dark"
    assert settings.accent_color == "#112233"
    assert settings.ui_font_family == "Arial"
    assert settings.ui_font_size == 13
    assert settings.preview_font_family == "Courier New"
    assert settings.preview_font_size == 15
    assert settings.scale_factor == 1.25
    assert settings.summary_unit == "бригада"
    assert settings.summary_rules_json == "[]"


def test_theme_apply_changes_ui_font(qapp):
    root = QWidget()
    button = QPushButton("b", root)
    line = QLineEdit(root)
    label = QLabel("l", root)
    preview = PreviewPanel()
    preview.setParent(root)

    st = UserSettings(ui_font_family="Arial", ui_font_size=12, preview_font_family="Consolas", preview_font_size=10)
    ThemeManager(qapp).apply(st, root)

    assert qapp.font().family() == "Arial"
    assert button.font().family() == "Arial"
    assert line.font().family() == "Arial"
    assert label.font().family() == "Arial"
    assert preview.font().family() == "Consolas"


def test_theme_apply_changes_preview_font(qapp):
    root = QWidget()
    preview = PreviewPanel()
    preview.setParent(root)

    st = UserSettings(ui_font_family="Arial", preview_font_family="Courier New", ui_font_size=11, preview_font_size=16)
    ThemeManager(qapp).apply(st, root)

    assert qapp.font().family() == "Arial"
    assert preview.font().family() == "Courier New"


def test_scale_factor_affects_font_sizes(qapp):
    root = QWidget()
    preview = PreviewPanel()
    preview.setParent(root)

    st = UserSettings(ui_font_size=10, preview_font_size=12, scale_factor=1.5)
    ThemeManager(qapp).apply(st, root)

    assert qapp.font().pointSizeF() == pytest.approx(15.0)
    assert preview.font().pointSizeF() == pytest.approx(18.0)


def test_apply_updates_summary_rules_in_memory(qapp):
    controller = AppController.__new__(AppController)
    controller.win = SimpleNamespace(
        theme_manager=SimpleNamespace(apply=lambda *_args, **_kwargs: None),
        indexing_service=SimpleNamespace(extract_service=ExtractService("[]")),
        search_tab=SimpleNamespace(extracts_list=SimpleNamespace(currentIndex=lambda: SimpleNamespace(isValid=lambda: False))),
        data_tab=SimpleNamespace(extracts_list=SimpleNamespace(currentRow=lambda: -1)),
    )
    controller._current_preview_source = None

    rules = """[
      {"name":"R1","enabled":true,"pattern":"(?P<order_num>№\\\\s*\\\\d+)","flags":"IGNORECASE","template":"{surname} {order_num}"}
    ]"""
    new_settings = UserSettings(summary_rules_json=rules)
    controller.on_settings_applied(new_settings)

    out = controller.win.indexing_service.extract_service.summarize_record(
        {
            "person_name": "ПЕТРЕНКО Іван Іванович",
            "person_name_norm": "петренкоіваніванович",
            "paragraphs_json": "[1]",
            "paragraphs_text": '["Наказ № 55"]',
            "generated_rel": "a.docx",
        }
    )
    assert "№ 55" in out


def test_invalid_summary_rules_json_is_rejected(qapp):
    dlg = SettingsDialog(UserSettings(), AppConfig())
    dlg.source_dir_edit.setText(str(Path.cwd()))
    dlg.rules_edit.setPlainText("{broken")
    ok, message = dlg.validate()
    assert not ok
    assert "JSON" in (message or "")


def test_restore_defaults_updates_controls_but_not_saved_state_until_apply(qapp, tmp_path: Path):
    src = tmp_path / "source"
    src.mkdir()
    service = SettingsService(SettingsManager(tmp_path / "settings"))
    service.settings.ui_font_family = "Arial"
    service.save(service.settings)

    dlg = SettingsDialog(service.settings, AppConfig(source_directory=str(src), output_directory="./out", index_file="./index.sqlite3"))
    dlg.ui_font_edit.setText("Courier New")
    dlg.load_from(UserSettings(), AppConfig(source_directory=str(src), output_directory="./out", index_file="./index.sqlite3"))

    assert dlg.ui_font_edit.text() == UserSettings().ui_font_family
    assert service.settings.ui_font_family == "Arial"


def test_cancel_does_not_apply_unsaved_changes(monkeypatch):
    from ui import main_window as main_window_module

    fake_window = main_window_module.MainWindow.__new__(main_window_module.MainWindow)
    calls: list[str] = []
    fake_window.settings_service = SimpleNamespace(settings=UserSettings())
    fake_window.app_config_service = SimpleNamespace(config=AppConfig())
    fake_window._validate_and_apply_from_dialog = lambda *_args, **_kwargs: calls.append("applied")

    monkeypatch.setattr(main_window_module, "SettingsDialog", _FakeDialog)
    main_window_module.MainWindow.open_settings(fake_window)

    assert calls == []


def test_accent_color_roundtrip_and_apply(qapp):
    root = QWidget()
    st = UserSettings(accent_color="#AA22CC")
    ThemeManager(qapp).apply(st, root)

    assert "#AA22CC" in qapp.styleSheet()


def test_window_state_persistence_roundtrip(tmp_path: Path):
    mgr = SettingsManager(tmp_path)
    settings = UserSettings(
        window_geometry_b64=encode_bytes(b"geom"),
        window_state_b64=encode_bytes(b"state"),
        splitter_states_b64={"a": encode_bytes(b"split")},
        last_selected_tab=1,
        last_search_text="foo",
    )
    mgr.save(settings)

    loaded = mgr.load()
    assert loaded.window_geometry_b64 == settings.window_geometry_b64
    assert loaded.window_state_b64 == settings.window_state_b64
    assert loaded.splitter_states_b64["a"] == settings.splitter_states_b64["a"]
    assert loaded.last_selected_tab == 1
    assert loaded.last_search_text == "foo"


def test_recent_paths_bounded_and_deduplicated(tmp_path: Path):
    service = SettingsService(SettingsManager(tmp_path))
    for i in range(15):
        service.add_recent_source_dir(f"/tmp/source-{i}")
    service.add_recent_source_dir("/tmp/source-14")

    assert len(service.settings.recent_source_dirs) == 10
    assert service.settings.recent_source_dirs[0] == "/tmp/source-14"
    assert service.settings.recent_source_dirs.count("/tmp/source-14") == 1


def test_path_fields_roundtrip(qapp, tmp_path: Path):
    src = tmp_path / "source"
    src.mkdir()
    cfg = AppConfig(source_directory=str(src), output_directory=str(tmp_path / "out"), index_file=str(tmp_path / "index.sqlite3"))
    dlg = SettingsDialog(UserSettings(), cfg)

    dlg.source_dir_edit.setText(str(src))
    dlg.output_dir_edit.setText(str(tmp_path / "out2"))
    dlg.index_file_edit.setText(str(tmp_path / "index2.sqlite3"))
    built = dlg.build_config(cfg)

    assert built.source_directory == str(src)
    assert built.output_directory.endswith("out2")
    assert built.index_file.endswith("index2.sqlite3")
