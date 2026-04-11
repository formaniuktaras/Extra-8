from __future__ import annotations

from pathlib import Path

from core.config import ConfigManager
from core.logging_setup import setup_logging
from core.settings import SettingsManager
from infra.filesystem.file_ops import SafeFileOperator
from infra.filesystem.temp_manager import TempManager
from infra.storage.sqlite_store import SQLiteStore
from services.diagnostics_service import DiagnosticsService
from services.extract_service import ExtractService
from services.indexing_service import IndexingService
from services.search_service import SearchService
from services.app_config_service import AppConfigService
from services.settings_service import SettingsService


def bootstrap():
    cfg_mgr = ConfigManager()
    cfg, cfg_path = cfg_mgr.load_or_create()
    app_config_service = AppConfigService(cfg_mgr, cfg, cfg_path)

    source_root, output_root, db_path = app_config_service.resolve_paths()
    root = cfg_path.parent

    source_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    setup_logging(root / "logs" / "app.log")

    settings_mgr = SettingsManager()
    settings_service = SettingsService(settings_mgr)

    store = SQLiteStore(db_path)
    temp_manager = TempManager()
    file_ops = SafeFileOperator(temp_manager)
    extract_service = ExtractService(settings_service.settings.summary_rules_json)
    indexing_service = IndexingService(store, extract_service, source_root, output_root, file_ops)
    search_service = SearchService(store)
    diagnostics_service = DiagnosticsService()

    return {
        "source_root": source_root,
        "indexing_service": indexing_service,
        "search_service": search_service,
        "diagnostics_service": diagnostics_service,
        "settings_service": settings_service,
        "app_config_service": app_config_service,
    }
