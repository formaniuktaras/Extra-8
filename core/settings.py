from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    from PySide6.QtCore import QStandardPaths
except Exception:  # pragma: no cover
    QStandardPaths = None


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
    colors: dict[str, str] = field(default_factory=lambda: {"accent": "#3a7afe"})
    fonts: dict[str, str] = field(default_factory=lambda: {"family": "Segoe UI", "size": "10", "mono": "Consolas"})
    scaling: float = 1.0
    highlight_options: dict[str, bool] = field(default_factory=lambda: {"extract": True})
    summary_unit: str = "в/ч"
    summary_rules_json: str = field(default_factory=_default_rules_json)
    geometry: str = ""
    window_state: str = ""


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

    def load(self) -> UserSettings:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            st = UserSettings()
            self.save(st)
            return st
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return UserSettings(**data)

    def save(self, settings: UserSettings) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")

    def restore_defaults(self) -> UserSettings:
        st = UserSettings()
        self.save(st)
        return st
