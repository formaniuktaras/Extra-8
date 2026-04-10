from pathlib import Path
from threading import Thread

from domain.models import PersonExtract, SourceDocument
from infra.storage.sqlite_store import SQLiteStore


def test_sqlite_schema_initialization(tmp_path: Path):
    store = SQLiteStore(tmp_path / "i.sqlite3")
    with store.connection_factory.connection() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r[0] for r in rows}
    assert {"meta", "documents", "extracts"}.issubset(names)


def test_sqlite_migration(tmp_path: Path):
    store = SQLiteStore(tmp_path / "i.sqlite3")
    with store.connection_factory.connection() as conn:
        v = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
    assert int(v) >= 1


def test_insert_load_list_extracts(tmp_path: Path):
    store = SQLiteStore(tmp_path / "i.sqlite3")
    doc = SourceDocument("a", "a.docx", tmp_path / "a.docx", 1.0, 10)
    did = store.upsert_document(doc)
    store.replace_extracts_for_document(did, [PersonExtract("ПЕТРЕНКО Іван Іванович", "петренк іван іванович", [0], "x.docx")])
    assert store.search_people({"петренк"})


def test_store_can_be_used_from_multiple_threads(tmp_path: Path):
    store = SQLiteStore(tmp_path / "i.sqlite3")

    def worker(i: int) -> None:
        doc = SourceDocument(f"k{i}", f"{i}.docx", tmp_path / f"{i}.docx", float(i), i)
        did = store.upsert_document(doc)
        store.replace_extracts_for_document(did, [PersonExtract(f"Person {i}", f"person {i}", [0], f"{i}.docx")])

    threads = [Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(store.list_documents()) == 8
