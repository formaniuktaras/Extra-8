from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from infra.filesystem.temp_manager import TempManager


class SafeFileOperator:
    def __init__(self, temp_manager: TempManager) -> None:
        self.temp_manager = temp_manager

    def _local_temp_path(self, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        return target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"

    def safe_replace_file(self, temp_path: Path, target: Path) -> None:
        backup = target.with_suffix(target.suffix + ".bak")
        try:
            if target.exists():
                if backup.exists():
                    backup.unlink()
                target.replace(backup)
            temp_path.replace(target)
            backup.unlink(missing_ok=True)
        except Exception:
            if backup.exists() and not target.exists():
                backup.replace(target)
            raise
        finally:
            temp_path.unlink(missing_ok=True)

    def atomic_write_bytes(self, target: Path, payload: bytes) -> None:
        temp_path = self._local_temp_path(target)
        temp_path.write_bytes(payload)
        self.safe_replace_file(temp_path, target)


    def atomic_replace_bytes(self, target: Path, payload: bytes) -> None:
        self.atomic_write_bytes(target, payload)

    def remove_file_and_prune_empty_dirs(self, path: Path, stop: Path) -> None:
        if path.exists():
            path.unlink()
        cur = path.parent
        while cur != stop and cur.exists() and not any(cur.iterdir()):
            cur.rmdir()
            cur = cur.parent

    def cleanup_stale_generated_outputs(self, root: Path, stale_paths: list[Path]) -> None:
        for stale in stale_paths:
            try:
                self.remove_file_and_prune_empty_dirs(stale, root)
            except FileNotFoundError:
                continue

    def cleanup_empty_parents(self, path: Path, stop: Path) -> None:
        cur = path.parent
        while cur != stop and cur.exists() and not any(cur.iterdir()):
            cur.rmdir()
            cur = cur.parent

    def delete_path(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
