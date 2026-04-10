from __future__ import annotations

import logging
from pathlib import Path

from core.settings import RECENT_PATHS_LIMIT, SettingsManager, UserSettings

logger = logging.getLogger(__name__)


class SettingsService:
    def __init__(self, manager: SettingsManager) -> None:
        self.manager = manager
        self.settings = manager.load()

    @staticmethod
    def _push_recent(values: list[str], path: str, max_size: int = RECENT_PATHS_LIMIT) -> list[str]:
        cleaned = (path or "").strip()
        if not cleaned:
            return values
        filtered = [p for p in values if p.casefold() != cleaned.casefold()]
        return [cleaned, *filtered][:max_size]

    def save(self, settings: UserSettings) -> None:
        self.manager.save(settings)
        self.settings = settings

    def restore_defaults(self) -> UserSettings:
        self.settings = self.manager.restore_defaults()
        return self.settings

    def add_recent_source_dir(self, path: str) -> None:
        self.settings.recent_source_dirs = self._push_recent(self.settings.recent_source_dirs, path)

    def add_recent_output_dir(self, path: str) -> None:
        self.settings.recent_output_dirs = self._push_recent(self.settings.recent_output_dirs, path)

    def add_recent_index_file(self, path: str) -> None:
        self.settings.recent_index_files = self._push_recent(self.settings.recent_index_files, path)

    def capture_session_state(self, *, last_tab: int, search_text: str) -> None:
        self.settings.last_selected_tab = max(0, int(last_tab))
        self.settings.last_search_text = search_text or ""

    def try_save(self, settings: UserSettings) -> tuple[bool, str | None]:
        try:
            self.save(settings)
            return True, None
        except Exception as exc:  # pragma: no cover - filesystem failure path
            logger.exception("Failed to persist settings")
            return False, str(exc)
