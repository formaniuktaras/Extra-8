from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class ProgressState:
    status: str = "Очікування..."
    detail: str = ""
    current: int = 0
    total: int = 0
    start_time: float = field(default_factory=time.monotonic)
    log_lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    is_cancelled: bool = False
    is_finished: bool = False

    def elapsed(self) -> float:
        return max(0.0, time.monotonic() - self.start_time)

    def throughput(self) -> float:
        elapsed = self.elapsed()
        return self.current / elapsed if elapsed > 0 else 0.0

    def eta_seconds(self) -> float | None:
        if self.total <= 0 or self.current <= 0:
            return None
        rate = self.throughput()
        if rate <= 0:
            return None
        return max(0.0, (self.total - self.current) / rate)

    def add_log(self, message: str, level: str = "INFO") -> None:
        line = f"[{level}] {message}"
        self.log_lines.append(line)
        if level.upper() in {"WARN", "WARNING"}:
            self.warnings.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)
        self.log_lines.append(f"[WARN] {message}")

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.log_lines.append(f"[ERROR] {message}")

    def set_progress(self, current: int, total: int) -> None:
        self.current = current
        self.total = total

    def set_status(self, text: str) -> None:
        self.status = text

    def set_detail(self, text: str) -> None:
        self.detail = text

    def mark_finished(self) -> None:
        self.is_finished = True
        self.is_cancelled = False

    def mark_cancelled(self) -> None:
        self.is_cancelled = True
        self.is_finished = False
