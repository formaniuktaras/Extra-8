from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class IndexingProgress:
    phase: str
    processed: int
    total: int
    speed_per_sec: float
    eta_sec: float
