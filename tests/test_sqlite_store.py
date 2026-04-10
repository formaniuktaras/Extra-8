from pathlib import Path

from domain.models import PersonExtract, SourceDocument
from infra.storage.sqlite_store import SQLiteStore


def test_sqlite_schema_initialization(tmp_path: Path):
    store = SQLiteStore(tmp_path / "i.sqlite3")
    rows = store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r[0] for r in rows}
    assert {"meta", "documents", "extracts"}.issubset(names)


def test_sqlite_migration(tmp_path: Path):
    store = SQLiteStore(tmp_path / "i.sqlite3")
    v = store.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
    assert int(v) >= 1


def test_insert_load_list_extracts(tmp_path: Path):
    store = SQLiteStore(tmp_path / "i.sqlite3")
    doc = SourceDocument("a", "a.docx", tmp_path / "a.docx", 1.0, 10)
    did = store.upsert_document(doc)
    store.replace_extracts_for_document(did, [PersonExtract("ПЕТРЕНКО Іван Іванович", "петренк іван іванович", [0], "x.docx")])
    assert store.search_people({"петренк"})
