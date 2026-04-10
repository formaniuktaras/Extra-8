from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from infra.filesystem.temp_manager import TempManager


@dataclass(slots=True)
class ReplaceTransaction:
    created: list[Path]
    backups: list[tuple[Path, Path]]


class SafeFileOperator:
    def __init__(self, temp_manager: TempManager) -> None:
        self.temp_manager = temp_manager

    def atomic_replace_bytes(self, target: Path, payload: bytes) -> None:
        tx = ReplaceTransaction(created=[], backups=[])
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.temp_manager.alloc(suffix=target.suffix)
        tmp.write_bytes(payload)
        tx.created.append(tmp)
        bak = target.with_suffix(target.suffix + ".bak")
        try:
            if target.exists():
                if bak.exists():
                    bak.unlink()
                target.replace(bak)
                tx.backups.append((target, bak))
            tmp.replace(target)
            for _, b in tx.backups:
                b.unlink(missing_ok=True)
        except Exception:
            if target.exists() and bak.exists():
                target.unlink(missing_ok=True)
                bak.replace(target)
            raise
        finally:
            tmp.unlink(missing_ok=True)

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
