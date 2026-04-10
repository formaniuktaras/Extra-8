from pathlib import Path

from services.diagnostics_service import DiagnosticsService
from tests.conftest import create_docx


def test_diagnostics_for_good_file(tmp_path: Path):
    p = create_docx(tmp_path / "a.docx")
    svc = DiagnosticsService()
    r = svc.diagnose_file(p, "a.docx")
    assert r.error_text is None
    assert r.total_paragraphs > 0


def test_diagnostics_for_broken_file(tmp_path: Path):
    p = tmp_path / "bad.docx"
    p.write_bytes(b"broken")
    svc = DiagnosticsService()
    r = svc.diagnose_file(p, "bad.docx")
    assert r.error_text
