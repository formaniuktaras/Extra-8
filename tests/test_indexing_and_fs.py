from pathlib import Path

import pytest

from core.settings import UserSettings
from infra.filesystem.file_ops import SafeFileOperator
from infra.filesystem.temp_manager import TempManager
from infra.storage.sqlite_store import SQLiteStore
from services.extract_service import DefaultContextStrategy, ExtractService
from services.indexing_service import CancellationToken, IndexingService
from tests.conftest import create_docx


def test_changed_new_removed_document_detection(tmp_path: Path):
    source = tmp_path / "s"
    output = tmp_path / "o"
    source.mkdir()
    output.mkdir()
    f1 = create_docx(source / "a.docx")
    store = SQLiteStore(tmp_path / "i.sqlite3")
    file_ops = SafeFileOperator(TempManager())
    ext = ExtractService(file_ops, UserSettings().summary_rules_json)
    svc = IndexingService(store, ext, source, output, file_ops)
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


def test_file_replacement_rollback_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tm = TempManager()
    ops = SafeFileOperator(tm)
    target = tmp_path / "x.bin"
    target.write_bytes(b"old")
    tmp = ops._local_temp_path(target)
    tmp.write_bytes(b"new")

    original_replace = Path.replace

    def failing_replace(self: Path, other: Path):
        if self == tmp:
            raise RuntimeError("boom")
        return original_replace(self, other)

    monkeypatch.setattr(Path, "replace", failing_replace)
    with pytest.raises(RuntimeError):
        ops.safe_replace_file(tmp, target)

    assert target.read_bytes() == b"old"
    assert not tmp.exists()
    assert not target.with_suffix(target.suffix + ".bak").exists()


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
    file_ops = SafeFileOperator(TempManager())
    ext = ExtractService(file_ops, UserSettings().summary_rules_json)
    svc = IndexingService(store, ext, source, output, file_ops)
    token = CancellationToken(is_cancelled=True)
    with pytest.raises(RuntimeError):
        svc.full_rebuild(token=token)


def test_default_context_strategy_includes_heading() -> None:
    class P:
        def __init__(self, text: str) -> None:
            self.text = text

    paragraphs = [P("РОЗДІЛ 1"), P("ПЕТРЕНКО Іван Іванович"), P("службовий текст")]
    strategy = DefaultContextStrategy(include_previous=0, include_next=0)
    selected = strategy.select(paragraphs, {1}, len(paragraphs))
    assert 0 in selected and 1 in selected
