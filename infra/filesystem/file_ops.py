from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Iterable
from pathlib import Path

from infra.filesystem.temp_manager import TempManager

logger = logging.getLogger(__name__)


class SafeFileOperator:
    def __init__(self, temp_manager: TempManager) -> None:
        self.temp_manager = temp_manager

    def _local_temp_path(self, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        return target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"

    @staticmethod
    def _fsync_file(path: Path) -> None:
        with path.open("rb") as fh:
            os.fsync(fh.fileno())

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        try:
            fd = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        path_resolved = path.resolve(strict=False)
        root_resolved = root.resolve(strict=False)
        return path_resolved == root_resolved or root_resolved in path_resolved.parents

    def _cleanup_stale_sidecars(self, target: Path) -> None:
        backup = target.with_suffix(target.suffix + ".bak")
        if backup.exists() and not target.exists():
            logger.warning("Found stale backup without target, restoring: %s", target)
            backup.replace(target)
        elif backup.exists() and target.exists():
            logger.warning("Found stale backup with healthy target, removing backup: %s", backup)
            backup.unlink(missing_ok=True)

        for stale in target.parent.glob(f".{target.name}.*.tmp"):
            logger.warning("Removing stale temp artifact: %s", stale)
            stale.unlink(missing_ok=True)

    def safe_replace_file(self, temp_path: Path, target: Path) -> None:
        backup = target.with_suffix(target.suffix + ".bak")
        backup_created = False
        replacement_done = False
        try:
            if target.exists():
                target.replace(backup)
                backup_created = True
            temp_path.replace(target)
            replacement_done = True
        except Exception:
            logger.exception("Atomic replace failed, rollback triggered: %s", target)
            if backup_created and backup.exists():
                try:
                    if target.exists():
                        target.unlink()
                    backup.replace(target)
                except Exception:
                    logger.exception("Rollback failed while restoring backup for: %s", target)
            raise
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    logger.warning("Failed to remove temp file: %s", temp_path, exc_info=True)

        if replacement_done and backup.exists():
            try:
                backup.unlink()
            except Exception:
                logger.warning("Failed to remove backup file after successful replace: %s", backup, exc_info=True)

    def atomic_write_bytes(self, path: Path, payload: bytes) -> None:
        self._cleanup_stale_sidecars(path)
        temp_path = self._local_temp_path(path)
        logger.debug("Creating temp file for atomic write: %s", temp_path)
        try:
            with temp_path.open("wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            self._fsync_dir(temp_path.parent)
            self.safe_replace_file(temp_path, path)
            self._fsync_dir(path.parent)
            logger.debug("Atomic replace success: %s", path)
        except Exception:
            if not path.exists():
                logger.warning("Atomic write failed for new target, no file left behind: %s", path)
            raise

    def remove_file_and_prune_empty_dirs(self, path: Path, stop_at: Path) -> None:
        stop_at_resolved = stop_at.resolve(strict=False)
        target = path.resolve(strict=False)
        if not self._is_within(target, stop_at_resolved):
            logger.warning("Cleanup skipped because path outside boundary: %s (boundary=%s)", target, stop_at_resolved)
            return

        if path.exists() and path.is_file():
            try:
                path.unlink()
            except Exception:
                logger.warning("Failed to remove file during cleanup: %s", path, exc_info=True)
                return

        cur = path.parent.resolve(strict=False)
        while cur.exists() and cur != stop_at_resolved and self._is_within(cur, stop_at_resolved):
            try:
                next(cur.iterdir())
                break
            except StopIteration:
                try:
                    cur.rmdir()
                except Exception:
                    logger.warning("Failed to prune empty directory: %s", cur, exc_info=True)
                    break
                cur = cur.parent

    def cleanup_stale_generated_outputs(self, output_root: Path, stale_paths: Iterable[Path]) -> None:
        removed = 0
        skipped = 0
        for stale in stale_paths:
            stale_path = stale if stale.is_absolute() else output_root / stale
            if not self._is_within(stale_path, output_root):
                skipped += 1
                logger.warning("Skipped stale output cleanup for unsafe path: %s", stale)
                continue
            existed = stale_path.exists()
            self.remove_file_and_prune_empty_dirs(stale_path, output_root)
            if existed and not stale_path.exists():
                removed += 1
        logger.info("Removed generated outputs summary: removed=%s skipped=%s", removed, skipped)

    def cleanup_orphan_generated_outputs(
        self,
        output_root: Path,
        referenced_generated_paths: Iterable[Path | str],
    ) -> None:
        root = output_root.resolve(strict=False)
        if not root.exists():
            logger.info("Orphan cleanup skipped because output root does not exist: %s", root)
            return

        referenced_abs: set[Path] = set()
        skipped_refs = 0
        for ref in referenced_generated_paths:
            ref_path = Path(ref)
            abs_ref = ref_path.resolve(strict=False) if ref_path.is_absolute() else (root / ref_path).resolve(strict=False)
            if not self._is_within(abs_ref, root):
                skipped_refs += 1
                logger.warning("Skipping unsafe referenced path outside output root: %s", ref)
                continue
            referenced_abs.add(abs_ref)

        found = 0
        removed = 0
        skipped = 0
        for candidate in list(root.rglob("*.docx")):
            candidate_resolved = candidate.resolve(strict=False)
            if not self._is_within(candidate_resolved, root):
                skipped += 1
                logger.warning("Skipping cleanup candidate outside root: %s", candidate)
                continue
            found += 1
            if candidate_resolved in referenced_abs:
                continue
            existed = candidate.exists()
            self.remove_file_and_prune_empty_dirs(candidate, root)
            if existed and not candidate.exists():
                removed += 1

        logger.info(
            "Orphan cleanup summary: found=%s removed=%s skipped=%s skipped_references=%s",
            found,
            removed,
            skipped,
            skipped_refs,
        )
