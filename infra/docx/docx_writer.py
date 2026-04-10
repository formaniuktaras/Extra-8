from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from infra.docx.docx_reader import DocxDocument, NS, clone_body_elements


def write_extract_docx(doc: DocxDocument, indices: list[int], output: Path) -> bytes:
    root = ET.fromstring(doc.zip_entries["word/document.xml"])
    body = root.find("w:body", NS)
    if body is None:
        raise ValueError("body not found")
    for child in list(body):
        body.remove(child)
    for el in clone_body_elements(doc, indices):
        body.append(el)
    updated_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in doc.zip_entries.items():
            if name == "word/document.xml":
                zf.writestr(name, updated_xml)
            else:
                zf.writestr(name, payload)
    data = mem.getvalue()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return data
