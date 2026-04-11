from pathlib import Path

import pytest

from core.settings import UserSettings
from infra.filesystem.file_ops import SafeFileOperator
from infra.filesystem.temp_manager import TempManager
from infra.storage.sqlite_store import SQLiteStore
from services.extract_service import DefaultContextStrategy, ExtractService
from services.indexing_service import CancellationToken, IndexingService
from tests.conftest import create_docx


def _services(tmp_path: Path) -> tuple[Path, Path, SQLiteStore, SafeFileOperator, ExtractService, IndexingService]:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    store = SQLiteStore(tmp_path / "index.sqlite3")
    file_ops = SafeFileOperator(TempManager())
    ext = ExtractService(file_ops, UserSettings().summary_rules_json)
    idx = IndexingService(store, ext, source, output, file_ops)
    return source, output, store, file_ops, ext, idx


def _doc_xml_for_person(person_line: str) -> str:
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
  <w:body>
    <w:p><w:r><w:t>{person_line}</w:t></w:r></w:p>
    <w:p><w:r><w:t>Службовий текст</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""


def test_atomic_write_bytes_rolls_back_on_replace_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _, _, _, ops, _, _ = _services(tmp_path)
    target = tmp_path / "x.bin"
    target.write_bytes(b"old")

    original_replace = Path.replace

    def failing_replace(self: Path, other: Path):
        if self.name.startswith(f".{target.name}.") and self.suffix == ".tmp":
            raise RuntimeError("boom")
        return original_replace(self, other)

    monkeypatch.setattr(Path, "replace", failing_replace)
    with pytest.raises(RuntimeError):
        ops.atomic_write_bytes(target, b"new")

    assert target.read_bytes() == b"old"
    assert not any(target.parent.glob(f".{target.name}.*.tmp"))
    assert not target.with_suffix(target.suffix + ".bak").exists()


def test_atomic_write_bytes_does_not_leave_partial_file_on_new_target_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _, _, _, ops, _, _ = _services(tmp_path)
    target = tmp_path / "new.bin"

    original_replace = Path.replace

    def failing_replace(self: Path, other: Path):
        if self.name.startswith(f".{target.name}.") and self.suffix == ".tmp":
            raise RuntimeError("boom")
        return original_replace(self, other)

    monkeypatch.setattr(Path, "replace", failing_replace)
    with pytest.raises(RuntimeError):
        ops.atomic_write_bytes(target, b"payload")

    assert not target.exists()
    assert not any(target.parent.glob(f".{target.name}.*.tmp"))
    assert not target.with_suffix(target.suffix + ".bak").exists()


def test_remove_file_and_prune_empty_dirs_stops_at_boundary(tmp_path: Path):
    _, _, _, ops, _, _ = _services(tmp_path)
    root = tmp_path / "generated"
    nested_file = root / "a" / "b" / "c" / "x.docx"
    nested_file.parent.mkdir(parents=True)
    nested_file.write_bytes(b"x")

    ops.remove_file_and_prune_empty_dirs(nested_file, stop_at=root)

    assert root.exists()
    assert not (root / "a").exists()


def test_cleanup_orphan_generated_outputs_removes_unreferenced_files_only(tmp_path: Path):
    _, _, _, ops, _, _ = _services(tmp_path)
    output = tmp_path / "generated"
    (output / "keep").mkdir(parents=True)
    (output / "drop" / "sub").mkdir(parents=True)
    keep = output / "keep" / "one.docx"
    orphan = output / "drop" / "sub" / "old.docx"
    keep.write_bytes(b"k")
    orphan.write_bytes(b"o")

    ops.cleanup_orphan_generated_outputs(output, {Path("keep/one.docx")})

    assert keep.exists()
    assert not orphan.exists()
    assert not (output / "drop").exists()


def test_changed_document_replaces_outputs_without_leaving_stale_files(tmp_path: Path):
    source, output, store, _ops, _ext, idx = _services(tmp_path)
    source_file = create_docx(source / "a.docx", _doc_xml_for_person("ПЕТРЕНКО Іван Іванович"))
    idx.full_rebuild()
    source_key = "a.docx"
    first_rels = set(store.list_generated_rels_for_source_key(source_key))
    assert first_rels

    create_docx(source_file, _doc_xml_for_person("ІВАНЕНКО Петро Петрович"))
    idx.full_rebuild()

    second_rels = set(store.list_generated_rels_for_source_key(source_key))
    assert second_rels
    assert second_rels != first_rels
    for rel in second_rels:
        assert (output / rel).exists()
    for rel in first_rels - second_rels:
        assert not (output / rel).exists()


def test_removed_document_cleans_db_and_generated_outputs(tmp_path: Path):
    source, output, store, _ops, _ext, idx = _services(tmp_path)
    source_file = create_docx(source / "a.docx")
    idx.full_rebuild()
    generated = set(store.list_generated_rels_for_source_key("a.docx"))
    assert generated

    source_file.unlink()
    idx.full_rebuild()

    assert not store.list_documents()
    for rel in generated:
        assert not (output / rel).exists()


def test_full_rebuild_cleans_orphan_outputs_after_success(tmp_path: Path):
    source, output, store, _ops, _ext, idx = _services(tmp_path)
    create_docx(source / "a.docx")
    idx.full_rebuild()

    orphan = output / "orphan" / "ghost.docx"
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"ghost")
    assert orphan.exists()

    idx.full_rebuild()

    assert not orphan.exists()
    assert not (output / "orphan").exists()
    assert store.list_all_generated_rels()


def test_cancelled_rebuild_does_not_destroy_previous_valid_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, output, store, _ops, ext, idx = _services(tmp_path)
    source_file = create_docx(source / "a.docx", _doc_xml_for_person("ПЕТРЕНКО Іван Іванович"))
    idx.full_rebuild()
    old_rels = set(store.list_generated_rels_for_source_key("a.docx"))
    assert old_rels

    create_docx(source_file, _doc_xml_for_person("ІВАНЕНКО Петро Петрович"))

    original_build = ext.build_extracts_for_doc

    def cancelled_build(*args, **kwargs):
        extracts = original_build(*args, **kwargs)
        raise RuntimeError("Operation cancelled")

    monkeypatch.setattr(ext, "build_extracts_for_doc", cancelled_build)
    token = CancellationToken()
    with pytest.raises(RuntimeError):
        idx.full_rebuild(token=token)

    assert set(store.list_generated_rels_for_source_key("a.docx")) == old_rels
    for rel in old_rels:
        assert (output / rel).exists()


def test_db_never_points_to_missing_generated_file_after_successful_rebuild(tmp_path: Path):
    source, output, store, _ops, _ext, idx = _services(tmp_path)
    create_docx(source / "a.docx")
    create_docx(source / "b.docx", _doc_xml_for_person("ІВАНЕНКО Петро Петрович"))

    idx.full_rebuild()

    for rel in store.list_all_generated_rels():
        assert (output / rel).exists()


def test_default_context_strategy_includes_heading() -> None:
    class P:
        def __init__(self, text: str) -> None:
            self.text = text

    paragraphs = [P("РОЗДІЛ 1"), P("ПЕТРЕНКО Іван Іванович"), P("службовий текст")]
    strategy = DefaultContextStrategy(include_previous=0, include_next=0)
    selected = strategy.select(paragraphs, {1}, len(paragraphs))
    assert 0 in selected and 1 in selected
