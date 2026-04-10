from pathlib import Path

from core.settings import UserSettings
from infra.filesystem.file_ops import SafeFileOperator
from infra.filesystem.temp_manager import TempManager
from infra.storage.sqlite_store import SQLiteStore
from services.extract_service import ExtractService
from services.indexing_service import IndexingService
from tests.conftest import create_docx


def test_changed_new_removed_document_detection(tmp_path: Path):
    source = tmp_path / "s"
    output = tmp_path / "o"
    source.mkdir()
    output.mkdir()
    f1 = create_docx(source / "a.docx")
    store = SQLiteStore(tmp_path / "i.sqlite3")
    ext = ExtractService(SafeFileOperator(TempManager()), UserSettings().summary_rules_json)
    svc = IndexingService(store, ext, source, output)
    d1 = svc.detect_changes()
    assert len(d1.new_files) == 1
    svc.full_rebuild()
    d2 = svc.detect_changes()
    assert not d2.new_files and not d2.changed_files
    f1.write_bytes(f1.read_bytes() + b"x")
    d3 = svc.detect_changes()
    assert len(d3.changed_files) == 1
    f1.unlink()
    d4 = svc.detect_changes()
    assert d4.removed_source_keys


def test_file_replacement_rollback_behavior(tmp_path: Path):
    tm = TempManager()
    ops = SafeFileOperator(tm)
    target = tmp_path / "x.bin"
    target.write_bytes(b"old")
    ops.atomic_replace_bytes(target, b"new")
    assert target.read_bytes() == b"new"


def test_temp_cleanup_behavior(tmp_path: Path):
    tm = TempManager()
    p = tm.alloc()
    p.write_text("x", encoding="utf-8")
    assert tm.root.exists()
    tm.cleanup()
    assert not tm.root.exists()
