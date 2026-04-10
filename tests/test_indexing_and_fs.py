from pathlib import Path

from core.settings import UserSettings
from infra.filesystem.file_ops import SafeFileOperator
from infra.filesystem.temp_manager import TempManager
from infra.storage.sqlite_store import SQLiteStore
from services.extract_service import ExtractService
from services.indexing_service import CancellationToken, IndexingService
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
    ops.atomic_write_bytes(target, b"new")
    assert target.read_bytes() == b"new"


def test_cleanup_empty_nested_dirs(tmp_path: Path):
    tm = TempManager()
    ops = SafeFileOperator(tm)
    root = tmp_path / "generated"
    nested = root / "a" / "b" / "c.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("x", encoding="utf-8")
    ops.remove_file_and_prune_empty_dirs(nested, root)
    assert not (root / "a").exists()


def test_cancellation_during_indexing(tmp_path: Path):
    source = tmp_path / "s"
    output = tmp_path / "o"
    source.mkdir()
    output.mkdir()
    create_docx(source / "a.docx")
    store = SQLiteStore(tmp_path / "i.sqlite3")
    ext = ExtractService(SafeFileOperator(TempManager()), UserSettings().summary_rules_json)
    svc = IndexingService(store, ext, source, output)
    token = CancellationToken(is_cancelled=True)
    try:
        svc.full_rebuild(token=token)
        assert False, "expected cancellation"
    except RuntimeError:
        assert True
