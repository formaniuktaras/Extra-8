from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

JSONDict = dict[str, Any]


@dataclass(slots=True)
class FileFingerprint:
    path: Path
    mtime: float
    size: int
    sha1: str | None = None
