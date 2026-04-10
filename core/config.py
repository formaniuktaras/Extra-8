from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    source_directory: str = "./source"
    output_directory: str = "./output"
    index_file: str = "./data/index.sqlite3"
    theme_preset_default: str = "system"


class ConfigManager:
    def __init__(self, app_name: str = "DocxExtractUA") -> None:
        self.app_name = app_name

    def locate_config_path(self) -> Path:
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            p = exe_dir / "config.json"
            if p.exists():
                return p
        script_dir = Path(__file__).resolve().parents[1]
        candidate = script_dir / "config.json"
        if candidate.exists():
            return candidate
        return script_dir / "config.json"

    def load_or_create(self) -> tuple[AppConfig, Path]:
        path = self.locate_config_path()
        if not path.exists():
            cfg = AppConfig()
            path.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
            return cfg, path
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig(**data), path

    def save(self, cfg: AppConfig, path: Path) -> None:
        path.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
