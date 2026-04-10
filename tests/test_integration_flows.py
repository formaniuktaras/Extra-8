from pathlib import Path

from core.settings import UserSettings
from infra.filesystem.file_ops import SafeFileOperator
from infra.filesystem.temp_manager import TempManager
from infra.storage.sqlite_store import SQLiteStore
from services.diagnostics_service import DiagnosticsService
from services.extract_service import ExtractService
from services.indexing_service import IndexingService
from services.search_service import SearchService
from tests.conftest import create_docx


def _build_services(tmp_path: Path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    store = SQLiteStore(tmp_path / "db.sqlite3")
    ops = SafeFileOperator(TempManager())
    ext = ExtractService(ops, UserSettings().summary_rules_json)
    idx = IndexingService(store, ext, source, output, ops)
    return source, output, store, idx


def test_sqlite_worker_thread_like_flow(tmp_path: Path):
    source, _, store, idx = _build_services(tmp_path)
    create_docx(source / "a.docx")
    idx.full_rebuild()
    rows = store.search_people({"петренко"})
    assert rows


def test_remove_file_cleanup_removes_db_and_generated(tmp_path: Path):
    source, output, store, idx = _build_services(tmp_path)
    f = create_docx(source / "a.docx")
    idx.full_rebuild()
    assert any(output.iterdir())
    f.unlink()
    idx.full_rebuild()
    assert not store.list_documents()


def test_overwrite_extract_rebuild(tmp_path: Path):
    source, output, _store, idx = _build_services(tmp_path)
    source_file = create_docx(source / "a.docx")
    idx.full_rebuild()
    first = sorted(output.glob("*.docx"))[0]
    before = first.read_bytes()
    first.write_bytes(b"override")
    source_file.write_bytes(source_file.read_bytes() + b"x")
    idx.full_rebuild()
    after = first.read_bytes()
    assert after != b"override"
    assert after == before


def test_preview_flow_uses_paragraphs_json(tmp_path: Path):
    source, _output, store, idx = _build_services(tmp_path)
    create_docx(source / "a.docx")
    idx.full_rebuild()
    service = SearchService(store)
    person = service.search_people("петренко")[0]
    extracts = service.list_extracts(person["person_name_norm"])
    assert extracts and extracts[0]["paragraphs_json"]


def test_settings_apply_live_preview(qapp):
    from ui.dialogs.settings_dialog import SettingsDialog
    from ui.theme_manager import ThemeManager

    settings = UserSettings()
    dlg = SettingsDialog(settings)
    dlg.theme_combo.setCurrentText("dark")
    dlg.font_edit.setText("Arial")
    updated = dlg.build_settings(settings)
    ThemeManager(qapp).apply(updated)
    assert qapp.font().family() == "Arial"


def test_file_operations_add_rename_delete(tmp_path: Path):
    root = tmp_path / "fs"
    root.mkdir()
    p = root / "a.docx"
    p.write_bytes(b"x")
    renamed = root / "b.docx"
    p.rename(renamed)
    assert renamed.exists()
    renamed.unlink()
    assert not renamed.exists()


def test_diagnostics_broken_docx(tmp_path: Path):
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"broken")
    report = DiagnosticsService().diagnose_file(bad, "bad.docx")
    assert report.error_text
