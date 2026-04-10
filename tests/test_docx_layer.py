import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from infra.docx.docx_reader import NS, read_docx
from infra.docx.docx_writer import build_extract_package
from infra.docx.numbering import merge_prefix_if_needed, resolve_numbering_prefix
from tests.conftest import create_docx


def test_docx_numbering_extraction(tmp_path: Path):
    p = create_docx(tmp_path / "a.docx")
    doc = read_docx(p)
    counters = {}
    first_num_p = [e for e in doc.body_elements if e.tag.endswith("}p")][1]
    pref = resolve_numbering_prefix(first_num_p, counters)
    assert pref.startswith("1")


def test_docx_numbering_prefix_with_parent_levels(tmp_path: Path):
    p = create_docx(tmp_path / "a.docx")
    doc = read_docx(p)
    counters = {}
    ps = [e for e in doc.body_elements if e.tag.endswith("}p")]
    p1 = resolve_numbering_prefix(ps[1], counters)
    p2 = resolve_numbering_prefix(ps[2], counters)
    assert p1 == "1. "
    assert p2.startswith("1.1")


def test_regression_child_prefix_includes_parent(tmp_path: Path):
    p = create_docx(tmp_path / "a.docx")
    doc = read_docx(p)
    counters = {}
    ps = [e for e in doc.body_elements if e.tag.endswith("}p")]
    resolve_numbering_prefix(ps[1], counters)
    pref = resolve_numbering_prefix(ps[2], counters)
    assert pref == "1.1. "


def test_write_docx_from_selected_block_indices(tmp_path: Path):
    p = create_docx(tmp_path / "a.docx")
    doc = read_docx(p)
    out = tmp_path / "out.docx"
    out.write_bytes(build_extract_package(doc, [0]))
    od = read_docx(out)
    assert len(od.paragraphs) >= 1


def test_preserving_namespace_declarations(tmp_path: Path):
    p = create_docx(tmp_path / "a.docx")
    doc = read_docx(p)
    out = tmp_path / "out.docx"
    out.write_bytes(build_extract_package(doc, [0]))
    with zipfile.ZipFile(out, "r") as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    assert root.tag.endswith("document")


def test_merge_prefix_no_duplicate():
    assert merge_prefix_if_needed("1. ", "1. Текст") == "1. Текст"
