from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtWidgets")

from core.config import AppConfig, ConfigManager
from core.settings import UserSettings
from services.app_config_service import AppConfigService
from services.extract_service import ExtractService
from ui.dialogs.settings_dialog import SettingsDialog
from ui.main_window import MainWindow


class _DummySettingsService:
    def __init__(self, settings: UserSettings) -> None:
        self.settings = settings
        self.saved: list[UserSettings] = []
        self.try_save_result = (True, None)

    @staticmethod
    def _push_recent(values: list[str], path: str, max_size: int = 10) -> list[str]:
        cleaned = (path or "").strip()
        if not cleaned:
            return values
        filtered = [p for p in values if p.casefold() != cleaned.casefold()]
        return [cleaned, *filtered][:max_size]

    def try_save(self, settings: UserSettings):
        self.saved.append(settings)
        if self.try_save_result[0]:
            self.settings = settings
        return self.try_save_result

    def save(self, settings: UserSettings) -> None:
        self.saved.append(settings)
        self.settings = settings


class _FailingConfigService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def save(self, _config: AppConfig) -> None:
        raise RuntimeError("config save failed")


class _OkConfigService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config


def _build_window_for_apply(settings: UserSettings, config_service, *, try_save_ok: bool = True) -> MainWindow:
    win = MainWindow.__new__(MainWindow)
    win.settings_service = _DummySettingsService(settings)
    win.settings_service.try_save_result = (try_save_ok, None if try_save_ok else "save failed")
    win.app_config_service = config_service
    win.search_tab = SimpleNamespace(
        theme_combo=SimpleNamespace(blockSignals=lambda *_args: None, setCurrentText=lambda *_args: None)
    )
    win.controller = SimpleNamespace(on_settings_applied=lambda *_args: None)
    win._apply_runtime_paths = lambda: None
    return win


def test_user_settings_apply_not_blocked_by_unchanged_invalid_relative_source_path(qapp, tmp_path: Path):
    cfg = AppConfig(source_directory="./source", output_directory="./output", index_file="./data/index.sqlite3")
    dlg = SettingsDialog(UserSettings(), cfg)
    dlg.ui_font_edit.setText(dlg.ui_font_edit.text() or "Segoe UI")
    dlg.preview_font_edit.setText(dlg.preview_font_edit.text() or "Consolas")
    dlg.rules_edit.setPlainText("[]")

    ok, err = dlg.validate_user_settings()
    assert ok, err


def test_relative_config_path_validation_uses_config_base_dir(tmp_path: Path):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "source").mkdir()
    service = AppConfigService(ConfigManager(), AppConfig(), cfg_dir / "config.json")

    ok, err = service.validate(AppConfig(source_directory="./source", output_directory="./out", index_file="./db/index.sqlite3"))

    assert ok, err


def test_apply_settings_does_not_mutate_live_ui_before_successful_save(monkeypatch):
    from ui import main_window as main_window_module

    calls: list[str] = []
    monkeypatch.setattr(main_window_module.QMessageBox, "critical", lambda *_args, **_kwargs: None)
    win = _build_window_for_apply(UserSettings(theme_preset="light"), _OkConfigService(AppConfig()), try_save_ok=False)
    win.controller = SimpleNamespace(on_settings_applied=lambda *_args: calls.append("live_applied"))

    ok = win.apply_settings(UserSettings(theme_preset="dark"), AppConfig(), persist=True, config_changed=False)

    assert not ok
    assert calls == []


def test_save_config_failure_does_not_leave_partially_applied_settings(monkeypatch):
    from ui import main_window as main_window_module

    monkeypatch.setattr(main_window_module.QMessageBox, "critical", lambda *_args, **_kwargs: None)
    initial = UserSettings(theme_preset="light")
    win = _build_window_for_apply(initial, _FailingConfigService(AppConfig()), try_save_ok=True)

    ok = win.apply_settings(UserSettings(theme_preset="dark"), AppConfig(source_directory="a", output_directory="b", index_file="c"), persist=True, config_changed=True)

    assert not ok
    assert win.settings_service.settings.theme_preset == "light"


def test_restore_defaults_does_not_break_apply_flow(qapp):
    cfg = AppConfig(source_directory="./source", output_directory="./output", index_file="./data/index.sqlite3")
    dlg = SettingsDialog(UserSettings(ui_font_family="Segoe UI"), cfg)
    dlg.load_from(UserSettings(), cfg)

    ok, err = dlg.validate_user_settings()

    assert ok, err


def test_summary_rules_apply_after_successful_settings_save():
    extract_service = ExtractService("[]")
    controller = SimpleNamespace(
        win=SimpleNamespace(
            theme_manager=SimpleNamespace(apply=lambda *_args, **_kwargs: None),
            indexing_service=SimpleNamespace(extract_service=extract_service),
            search_tab=SimpleNamespace(extracts_list=SimpleNamespace(currentIndex=lambda: SimpleNamespace(isValid=lambda: False))),
            data_tab=SimpleNamespace(extracts_list=SimpleNamespace(currentRow=lambda: -1)),
        ),
        _refresh_current_previews=lambda: None,
    )

    from ui.controllers.app_controller import AppController

    AppController.on_settings_applied(
        controller,
        UserSettings(
            summary_rules_json='[{"name":"R","enabled":true,"pattern":"(?P<order_num>№\\\\s*\\\\d+)","flags":"IGNORECASE","template":"{order_num}"}]'
        ),
    )

    out = extract_service.summarize_record(
        {
            "person_name": "ПЕТРЕНКО Іван Іванович",
            "person_name_norm": "петренкоіваніванович",
            "paragraphs_json": "[1]",
            "paragraphs_text": '["Наказ № 55"]',
            "generated_rel": "a.docx",
        }
    )
    assert "№ 55" in out


def test_font_picker_or_font_validation_flow(qapp):
    dlg = SettingsDialog(UserSettings(), AppConfig())
    dlg.ui_font_edit.setText("DefinitelyMissingFontFamily")

    ok, message = dlg.validate_user_settings()

    assert not ok
    assert "UI font" in (message or "")


def test_theme_combo_uses_shared_apply_flow(monkeypatch):
    win = _build_window_for_apply(UserSettings(), _OkConfigService(AppConfig()), try_save_ok=True)
    captured: list[str] = []

    def _apply(new_settings, _new_config, *, persist: bool, config_changed: bool | None = None):
        captured.append(f"{new_settings.theme_preset}:{persist}:{config_changed}")
        return True

    win.apply_settings = _apply

    MainWindow._theme_changed_from_search(win, "dark")

    assert captured == ["dark:True:False"]
