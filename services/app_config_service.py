from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from core.config import AppConfig, ConfigManager


class AppConfigService:
    def __init__(self, manager: ConfigManager, config: AppConfig, path: Path) -> None:
        self.manager = manager
        self.config = config
        self.path = path

    def save(self, config: AppConfig) -> None:
        self.manager.save(config, self.path)
        self.config = config

    def resolve_paths(self) -> tuple[Path, Path, Path]:
        root = self.path.parent
        source_root = (root / self.config.source_directory).resolve()
        output_root = (root / self.config.output_directory).resolve()
        db_path = (root / self.config.index_file).resolve()
        return source_root, output_root, db_path

    def with_paths(self, source_directory: str, output_directory: str, index_file: str) -> AppConfig:
        return replace(
            self.config,
            source_directory=source_directory,
            output_directory=output_directory,
            index_file=index_file,
        )
