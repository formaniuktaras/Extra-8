from __future__ import annotations

import copy
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from core.exceptions import DocxParseError
from domain.models import ParagraphDescriptor

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


@dataclass(slots=True)
class DocxDocument:
    path: Path
    zip_entries: dict[str, bytes]
    document_tree: ET.ElementTree
    namespaces: dict[str, str]
    body_elements: list[ET.Element]
    paragraphs: list[ParagraphDescriptor]
    styles_tree: ET.ElementTree | None
    numbering_tree: ET.ElementTree | None


def _text_of_paragraph(p: ET.Element) -> str:
    texts = [n.text or "" for n in p.findall(".//w:t", NS)]
    return "".join(texts).strip()


def read_docx(path: Path) -> DocxDocument:
    try:
        entries: dict[str, bytes] = {}
        with zipfile.ZipFile(path, "r") as zf:
            for info in zf.infolist():
                entries[info.filename] = zf.read(info.filename)
        doc_xml = entries["word/document.xml"]
        doc_tree = ET.ElementTree(ET.fromstring(doc_xml))
        styles = ET.ElementTree(ET.fromstring(entries["word/styles.xml"])) if "word/styles.xml" in entries else None
        numbering = ET.ElementTree(ET.fromstring(entries["word/numbering.xml"])) if "word/numbering.xml" in entries else None
        root = doc_tree.getroot()
        body = root.find("w:body", NS)
        if body is None:
            raise DocxParseError("Документ не містить body")
        body_elements = list(body)
        paragraphs: list[ParagraphDescriptor] = []
        for idx, el in enumerate(body_elements):
            if el.tag.endswith("}p"):
                text = _text_of_paragraph(el)
                paragraphs.append(ParagraphDescriptor(text=text, block_index=idx))
        ns = {"w": W_NS}
        return DocxDocument(path, entries, doc_tree, ns, body_elements, paragraphs, styles, numbering)
    except Exception as exc:
        raise DocxParseError(f"Не вдалося прочитати DOCX {path}: {exc}") from exc


def clone_body_elements(doc: DocxDocument, indices: list[int]) -> list[ET.Element]:
    out: list[ET.Element] = []
    for i in indices:
        if 0 <= i < len(doc.body_elements):
            out.append(copy.deepcopy(doc.body_elements[i]))
    body = doc.document_tree.getroot().find("w:body", NS)
    if body is not None and len(body) > 0:
        last = body[-1]
        if last.tag.endswith("}sectPr"):
            out.append(copy.deepcopy(last))
    return out


def render_plain_text(doc: DocxDocument) -> str:
    return "\n".join(p.text for p in doc.paragraphs if p.text)
