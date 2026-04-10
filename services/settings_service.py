from __future__ import annotations

from core.settings import SettingsManager, UserSettings


class SettingsService:
    def __init__(self, manager: SettingsManager) -> None:
        self.manager = manager
        self.settings = manager.load()

    def save(self, settings: UserSettings) -> None:
        self.manager.save(settings)
        self.settings = settings

    def restore_defaults(self) -> UserSettings:
        self.settings = self.manager.restore_defaults()
        return self.settings
