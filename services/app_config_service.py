from __future__ import annotations

import os
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

    def resolve_paths_for(self, config: AppConfig) -> tuple[Path, Path, Path]:
        root = self.path.parent
        source_root = (root / config.source_directory).resolve()
        output_root = (root / config.output_directory).resolve()
        db_path = (root / config.index_file).resolve()
        return source_root, output_root, db_path

    def validate(self, config: AppConfig) -> tuple[bool, str | None]:
        if not config.source_directory.strip():
            return False, "Поле source directory не може бути порожнім"
        if not config.output_directory.strip():
            return False, "Поле output directory не може бути порожнім"
        if not config.index_file.strip():
            return False, "Поле index file не може бути порожнім"

        source_root, output_root, db_path = self.resolve_paths_for(config)
        source_ok, source_error = self._validate_directory_path(source_root, "source directory", allow_create=True)
        if not source_ok:
            return False, source_error
        output_ok, output_error = self._validate_directory_path(output_root, "output directory", allow_create=True)
        if not output_ok:
            return False, output_error
        index_ok, index_error = self._validate_index_path(db_path)
        if not index_ok:
            return False, index_error
        return True, None

    @staticmethod
    def _validate_directory_path(path: Path, label: str, *, allow_create: bool) -> tuple[bool, str | None]:
        if path.exists():
            if not path.is_dir():
                return False, f"Некоректний {label}: очікується каталог ({path})"
            return True, None
        if not allow_create:
            return False, f"Шлях не існує: {path}"
        parent = AppConfigService._nearest_existing_parent(path)
        if parent is None:
            return False, f"Неможливо створити каталог {label}: {path}"
        if not parent.is_dir():
            return False, f"Некоректний батьківський шлях для {label}: {parent}"
        if not os.access(parent, os.W_OK):
            return False, f"Немає прав на створення каталогу {label}: {path}"
        return True, None

    @staticmethod
    def _validate_index_path(index_path: Path) -> tuple[bool, str | None]:
        if index_path.exists() and index_path.is_dir():
            return False, f"Некоректний index file: шлях вказує на каталог ({index_path})"
        parent = AppConfigService._nearest_existing_parent(index_path.parent)
        if parent is None:
            return False, f"Неможливо створити каталог для index file: {index_path.parent}"
        if not parent.is_dir():
            return False, f"Некоректний батьківський шлях для index file: {parent}"
        if not os.access(parent, os.W_OK):
            return False, f"Немає прав на створення каталогу для index file: {index_path.parent}"
        return True, None

    @staticmethod
    def _nearest_existing_parent(path: Path) -> Path | None:
        current = path
        while not current.exists():
            if current == current.parent:
                return None
            current = current.parent
        return current

    def with_paths(self, source_directory: str, output_directory: str, index_file: str) -> AppConfig:
        return replace(
            self.config,
            source_directory=source_directory,
            output_directory=output_directory,
            index_file=index_file,
        )
