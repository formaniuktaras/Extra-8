from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from domain.models import SourceDocument
from infra.docx.docx_reader import read_docx
from infra.filesystem.file_ops import SafeFileOperator
from infra.filesystem.source_scanner import scan_docx_files
from infra.storage.sqlite_store import SQLiteStore
from services.extract_service import ExtractService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DiffResult:
    new_files: list[Path]
    changed_files: list[Path]
    removed_source_keys: list[str]


@dataclass(slots=True)
class CancellationToken:
    is_cancelled: bool = False

    def cancel(self) -> None:
        self.is_cancelled = True

    def throw_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise RuntimeError("Operation cancelled")


def file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


class IndexingService:
    def __init__(
        self,
        store: SQLiteStore,
        extract_service: ExtractService,
        source_root: Path,
        output_root: Path,
        file_ops: SafeFileOperator,
    ) -> None:
        self.store = store
        self.extract_service = extract_service
        self.source_root = source_root
        self.output_root = output_root
        self.file_ops = file_ops

    def detect_changes(self) -> DiffResult:
        files = scan_docx_files(self.source_root)
        db_docs = {row["source_key"]: row for row in self.store.list_documents()}
        seen_keys: set[str] = set()
        new_files: list[Path] = []
        changed_files: list[Path] = []
        for f in files:
            rel = f.relative_to(self.source_root).as_posix()
            key = rel.lower()
            seen_keys.add(key)
            st = f.stat()
            row = db_docs.get(key)
            if row is None:
                new_files.append(f)
                continue
            if abs(float(row["mtime"]) - st.st_mtime) > 0.0001 or int(row["size"]) != st.st_size:
                changed_files.append(f)
        removed = [k for k in db_docs.keys() if k not in seen_keys]
        return DiffResult(new_files, changed_files, removed)

    def quick_check(self, token: CancellationToken | None = None) -> DiffResult:
        if token:
            token.throw_if_cancelled()
        return self.detect_changes()

    def full_rebuild(
        self,
        on_progress: Callable[[str, int, int], None] | None = None,
        token: CancellationToken | None = None,
    ) -> None:
        diff = self.detect_changes()
        for key in diff.removed_source_keys:
            if token:
                token.throw_if_cancelled()
            self.store.delete_document_by_source_key(key)

        files = diff.new_files + diff.changed_files
        total = len(files)
        for i, path in enumerate(files, 1):
            if token:
                token.throw_if_cancelled()
            rel = path.relative_to(self.source_root).as_posix()
            source_key = rel.lower()
            doc_model = SourceDocument(
                source_key=source_key,
                source_rel=rel,
                source_abs=path,
                mtime=path.stat().st_mtime,
                size=path.stat().st_size,
                sha1=file_sha1(path),
            )
            doc_id = self.store.upsert_document(doc_model)

            try:
                parsed = read_docx(path)
                extracts = self.extract_service.build_extracts_for_doc(parsed, self.output_root, rel)
                if token:
                    token.throw_if_cancelled()
                self.store.replace_extracts_for_document(doc_id, extracts)
            except RuntimeError:
                if token and token.is_cancelled:
                    logger.info("Indexing cancelled while processing source: %s", rel)
                raise

            if on_progress:
                on_progress("indexing", i, total)
