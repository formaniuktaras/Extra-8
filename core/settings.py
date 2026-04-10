from __future__ import annotations

import base64
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from PySide6.QtCore import QStandardPaths
except Exception:  # pragma: no cover
    QStandardPaths = None

logger = logging.getLogger(__name__)

RECENT_PATHS_LIMIT = 10


def _default_rules_json() -> str:
    return json.dumps(
        [
            {
                "name": "Базовий наказ",
                "enabled": True,
                "pattern": r"(?P<surname>[А-ЯІЇЄҐ'’-]+)\\s+(?P<first>[А-ЯІЇЄҐ][а-яіїєґ'’-]+)\\s+(?P<patronymic>[А-ЯІЇЄҐ][а-яіїєґ'’-]+).*(?P<order_num>№\\s*\\d+)",
                "flags": "IGNORECASE",
                "template": "{surname} {first} {patronymic} ({order_num})",
            }
        ],
        ensure_ascii=False,
        indent=2,
    )


@dataclass(slots=True)
class UserSettings:
    theme_preset: str = "system"
    accent_color: str = "#3A7AFE"
    ui_font_family: str = "Segoe UI"
    ui_font_size: int = 10
    preview_font_family: str = "Consolas"
    preview_font_size: int = 10
    scale_factor: float = 1.0
    summary_unit: str = "в/ч"
    summary_rules_json: str = field(default_factory=_default_rules_json)
    window_geometry_b64: str = ""
    window_state_b64: str = ""
    splitter_states_b64: dict[str, str] = field(default_factory=dict)
    last_selected_tab: int = 0
    last_search_text: str = ""
    recent_source_dirs: list[str] = field(default_factory=list)
    recent_output_dirs: list[str] = field(default_factory=list)
    recent_index_files: list[str] = field(default_factory=list)


class SettingsManager:
    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            if QStandardPaths is not None:
                loc = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
            else:
                loc = ""
            if not loc:
                loc = str(Path.home() / ".extra-8")
            base_dir = Path(loc)
        self.base_dir = base_dir
        self.path = base_dir / "user_settings.json"

    @staticmethod
    def _bounded_dedup(paths: list[str], max_size: int = RECENT_PATHS_LIMIT) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for raw in paths:
            value = (raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(value)
            if len(cleaned) >= max_size:
                break
        return cleaned

    @staticmethod
    def _migrate_legacy(data: dict[str, Any]) -> UserSettings:
        fonts = data.get("fonts") or {}
        colors = data.get("colors") or {}
        scaling = data.get("scaling")
        return UserSettings(
            theme_preset=str(data.get("theme_preset") or "system"),
            accent_color=str(data.get("accent_color") or colors.get("accent") or "#3A7AFE"),
            ui_font_family=str(data.get("ui_font_family") or fonts.get("family") or "Segoe UI"),
            ui_font_size=int(float(data.get("ui_font_size") or fonts.get("size") or 10)),
            preview_font_family=str(data.get("preview_font_family") or fonts.get("mono") or "Consolas"),
            preview_font_size=int(float(data.get("preview_font_size") or data.get("ui_font_size") or fonts.get("size") or 10)),
            scale_factor=float(data.get("scale_factor") or scaling or 1.0),
            summary_unit=str(data.get("summary_unit") or "в/ч"),
            summary_rules_json=str(data.get("summary_rules_json") or _default_rules_json()),
            window_geometry_b64=str(data.get("window_geometry_b64") or data.get("geometry") or ""),
            window_state_b64=str(data.get("window_state_b64") or data.get("window_state") or ""),
            splitter_states_b64=dict(data.get("splitter_states_b64") or {}),
            last_selected_tab=int(data.get("last_selected_tab") or 0),
            last_search_text=str(data.get("last_search_text") or ""),
            recent_source_dirs=SettingsManager._bounded_dedup(list(data.get("recent_source_dirs") or [])),
            recent_output_dirs=SettingsManager._bounded_dedup(list(data.get("recent_output_dirs") or [])),
            recent_index_files=SettingsManager._bounded_dedup(list(data.get("recent_index_files") or [])),
        )

    def load(self) -> UserSettings:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            st = UserSettings()
            self.save(st)
            return st
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            settings = self._migrate_legacy(data if isinstance(data, dict) else {})
        except Exception:
            logger.exception("Failed to load settings, using defaults")
            settings = UserSettings()
        self.save(settings)
        return settings

    def save(self, settings: UserSettings) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        payload = asdict(settings)
        payload["recent_source_dirs"] = self._bounded_dedup(settings.recent_source_dirs)
        payload["recent_output_dirs"] = self._bounded_dedup(settings.recent_output_dirs)
        payload["recent_index_files"] = self._bounded_dedup(settings.recent_index_files)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def restore_defaults(self) -> UserSettings:
        st = UserSettings()
        self.save(st)
        return st


def encode_bytes(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii") if value else ""


def decode_bytes(value: str) -> bytes:
    if not value:
        return b""
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except Exception:
        return b""
