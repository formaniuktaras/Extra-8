from __future__ import annotations

from pathlib import Path

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QLabel = QtWidgets.QLabel
QWidget = QtWidgets.QWidget

from core.config import AppConfig
from core.settings import SettingsManager, UserSettings, encode_bytes
from services.settings_service import SettingsService
from ui.dialogs.settings_dialog import SettingsDialog
from ui.theme_manager import ThemeManager
from ui.widgets.preview_panel import PreviewPanel


def test_settings_dialog_build_settings_uses_all_live_controls(qapp):
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


def test_theme_manager_applies_updated_settings(qapp):
    root = QWidget()
    preview = PreviewPanel()
    preview.setParent(root)

    st = UserSettings(theme_preset="dark", accent_color="#AA22CC", ui_font_family="Arial", ui_font_size=12, preview_font_family="Consolas", preview_font_size=14, scale_factor=1.2)
    ThemeManager(qapp).apply(st, root)

    assert qapp.font().family() == "Arial"
    assert "#AA22CC" in qapp.styleSheet()
    assert preview.font().family() == "Consolas"


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


def test_invalid_color_validation(qapp):
    dlg = SettingsDialog(UserSettings(), AppConfig())
    dlg.source_dir_edit.setText(str(Path.cwd()))
    dlg.accent_edit.setText("not-a-color")
    ok, message = dlg.validate()
    assert not ok
    assert "accent" in (message or "")


def test_invalid_summary_rules_validation(qapp):
    dlg = SettingsDialog(UserSettings(), AppConfig())
    dlg.source_dir_edit.setText(str(Path.cwd()))
    dlg.rules_edit.setPlainText("{broken")
    ok, message = dlg.validate()
    assert not ok
    assert "JSON" in (message or "")


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


def test_preview_font_applied_separately_from_ui_font(qapp):
    root = QWidget()
    preview = PreviewPanel()
    preview.setParent(root)
    label = QLabel("UI")
    label.setParent(root)

    st = UserSettings(ui_font_family="Arial", preview_font_family="Courier New", ui_font_size=11, preview_font_size=16)
    ThemeManager(qapp).apply(st, root)

    assert qapp.font().family() == "Arial"
    assert preview.font().family() == "Courier New"
