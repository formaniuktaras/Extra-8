from __future__ import annotations

import zipfile
import os
from pathlib import Path

import pytest
try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover
    QApplication = None

DOC_XML = """<?xml version='1.0' encoding='UTF-8'?>
<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
  <w:body>
    <w:p><w:r><w:t>ПЕТРЕНКО Іван Іванович призначити</w:t></w:r></w:p>
    <w:p><w:pPr><w:numPr><w:ilvl w:val='0'/><w:numId w:val='1'/></w:numPr></w:pPr><w:r><w:t>Пункт перший</w:t></w:r></w:p>
    <w:p><w:pPr><w:numPr><w:ilvl w:val='1'/><w:numId w:val='1'/></w:numPr></w:pPr><w:r><w:t>Підпункт</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""
STYLES_XML = """<?xml version='1.0' encoding='UTF-8'?><w:styles xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>"""
NUMBERING_XML = """<?xml version='1.0' encoding='UTF-8'?><w:numbering xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>"""
CT = """<?xml version='1.0' encoding='UTF-8'?><Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'></Types>"""


def create_docx(path: Path, doc_xml: str = DOC_XML) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CT)
        zf.writestr("word/document.xml", doc_xml)
        zf.writestr("word/styles.xml", STYLES_XML)
        zf.writestr("word/numbering.xml", NUMBERING_XML)
    return path


@pytest.fixture(scope="session")
def qapp():
    if QApplication is None:
        pytest.skip("PySide6 недоступний у тестовому середовищі")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
