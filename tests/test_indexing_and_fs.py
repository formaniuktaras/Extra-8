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
    ext = ExtractService(UserSettings().summary_rules_json)
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


def test_indexing_rebuild_without_extract_file_output(tmp_path: Path):
    source, output, store, _ops, _ext, idx = _services(tmp_path)
    create_docx(source / "a.docx", _doc_xml_for_person("ПЕТРЕНКО Іван Іванович"))

    idx.full_rebuild()

    person = store.search_people({"петренк"})
    assert person
    extracts = store.list_extracts_for_person(person[0]["person_name_norm"])
    assert extracts
    assert not list(output.rglob("*.docx"))


def test_removed_document_cleans_db(tmp_path: Path):
    source, _output, store, _ops, _ext, idx = _services(tmp_path)
    source_file = create_docx(source / "a.docx")
    idx.full_rebuild()

    source_file.unlink()
    idx.full_rebuild()

    assert not store.list_documents()


def test_cancelled_rebuild_keeps_previous_extract_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, _output, store, _ops, ext, idx = _services(tmp_path)
    source_file = create_docx(source / "a.docx", _doc_xml_for_person("ПЕТРЕНКО Іван Іванович"))
    idx.full_rebuild()
    people = store.search_people({"петренк"})
    assert people
    person_norm = people[0]["person_name_norm"]
    old_rows = store.list_extracts_for_person(person_norm)
    assert old_rows

    create_docx(source_file, _doc_xml_for_person("ІВАНЕНКО Петро Петрович"))

    original_build = ext.build_extracts_for_doc

    def cancelled_build(*args, **kwargs):
        _ = original_build(*args, **kwargs)
        raise RuntimeError("Operation cancelled")

    monkeypatch.setattr(ext, "build_extracts_for_doc", cancelled_build)
    token = CancellationToken()
    with pytest.raises(RuntimeError):
        idx.full_rebuild(token=token)

    assert store.list_extracts_for_person(person_norm)


def test_default_context_strategy_includes_heading() -> None:
    class P:
        def __init__(self, text: str) -> None:
            self.text = text

    paragraphs = [P("РОЗДІЛ 1"), P("ПЕТРЕНКО Іван Іванович"), P("службовий текст")]
    strategy = DefaultContextStrategy(include_previous=0, include_next=0)
    selected = strategy.select(paragraphs, {1}, len(paragraphs))
    assert 0 in selected and 1 in selected
