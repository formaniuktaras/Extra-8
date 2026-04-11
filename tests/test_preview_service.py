from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

from services.preview_cache import PreviewCache
from services.preview_service import PreviewService
from tests.conftest import create_docx


def _fake_doc(paragraphs: list[tuple[int, str]]):
    return SimpleNamespace(paragraphs=[SimpleNamespace(block_index=i, text=t) for i, t in paragraphs])


def test_preview_cache_reuses_same_mtime(tmp_path: Path, monkeypatch):
    path = create_docx(tmp_path / "a.docx")
    service = PreviewService(output_root=tmp_path)
    calls = {"n": 0}

    def fake_read_docx(_path: Path):
        calls["n"] += 1
        return _fake_doc([(0, "A"), (1, "B")])

    monkeypatch.setattr("services.preview_service.read_docx", fake_read_docx)
    first = service.get_source_preview(path)
    second = service.get_source_preview(path)

    assert first == "A\nB"
    assert second == "A\nB"
    assert calls["n"] == 1


def test_preview_cache_invalidates_on_mtime_change(tmp_path: Path, monkeypatch):
    path = create_docx(tmp_path / "a.docx")
    service = PreviewService(output_root=tmp_path)
    calls = {"n": 0}

    def fake_read_docx(_path: Path):
        calls["n"] += 1
        return _fake_doc([(0, f"A-{calls['n']}")])

    monkeypatch.setattr("services.preview_service.read_docx", fake_read_docx)
    assert service.get_source_preview(path) == "A-1"

    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns + 2_000_000_000, st.st_mtime_ns + 2_000_000_000))

    assert service.get_source_preview(path) == "A-2"
    assert calls["n"] == 2


def test_search_tab_preview_comes_from_db_text(tmp_path: Path, monkeypatch):
    source_path = create_docx(tmp_path / "s.docx")
    service = PreviewService(output_root=tmp_path)
    monkeypatch.setattr(service, "_load_source_paragraphs", lambda _p: [(0, "zero"), (3, "three")])
    record = {
        "generated_rel": "missing.docx",
        "source_abs": str(source_path),
        "paragraphs_json": json.dumps([3]),
        "paragraphs_text": json.dumps(["fallback"]),
    }

    assert service.get_extract_preview(record) == "three"
    assert service.last_extract_mode == "paragraphs_json"


def test_extract_preview_falls_back_to_paragraphs_text_json_string(tmp_path: Path):
    service = PreviewService(output_root=tmp_path)
    record = {
        "generated_rel": "missing.docx",
        "paragraphs_json": "[]",
        "paragraphs_text": json.dumps(["line one", "line two"]),
    }

    assert service.get_extract_preview(record) == "line one\nline two"
    assert service.last_extract_mode == "paragraphs_text"


def test_structured_preview_marks_selected_indices(tmp_path: Path, monkeypatch):
    path = create_docx(tmp_path / "a.docx")
    service = PreviewService(output_root=tmp_path)
    monkeypatch.setattr(service, "_load_source_paragraphs", lambda _p: [(0, "one"), (2, "two")])

    structured = service.build_highlighted_source_preview(path, [2])

    assert structured.plain_text == "one\ntwo"
    assert [p.is_selected for p in structured.paragraphs] == [False, True]


def test_preview_cache_clear_and_invalidate(tmp_path: Path):
    cache = PreviewCache[str](max_entries=2)
    p1 = tmp_path / "a.txt"
    p1.write_text("1", encoding="utf-8")
    p2 = tmp_path / "b.txt"
    p2.write_text("2", encoding="utf-8")

    cache.put(p1, "v1")
    cache.put(p2, "v2")
    assert cache.get(p1) == "v1"

    cache.invalidate(p1)
    assert cache.get(p1) is None

    cache.clear()
    assert cache.get(p2) is None
