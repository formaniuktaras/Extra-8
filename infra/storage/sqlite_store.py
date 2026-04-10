from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from domain.models import PersonExtract, SourceDocument
from infra.storage.migrations import init_schema, migrate_if_needed


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        init_schema(self.conn)
        migrate_if_needed(self.conn)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        for _ in range(3):
            try:
                yield self.conn
                self.conn.commit()
                break
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc):
                    time.sleep(0.1)
                    continue
                raise

    def upsert_document(self, doc: SourceDocument) -> int:
        with self.tx() as conn:
            conn.execute(
                """
                INSERT INTO documents(source_key, source_rel, source_abs, mtime, size, hash)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(source_key) DO UPDATE SET
                source_rel=excluded.source_rel,
                source_abs=excluded.source_abs,
                mtime=excluded.mtime,
                size=excluded.size,
                hash=excluded.hash
                """,
                (doc.source_key, doc.source_rel, str(doc.source_abs), doc.mtime, doc.size, doc.sha1),
            )
            row = conn.execute("SELECT id FROM documents WHERE source_key=?", (doc.source_key,)).fetchone()
            return int(row["id"])

    def replace_extracts_for_document(self, document_id: int, extracts: list[PersonExtract]) -> None:
        with self.tx() as conn:
            conn.execute("DELETE FROM extracts WHERE document_id=?", (document_id,))
            for e in extracts:
                conn.execute(
                    """
                    INSERT INTO extracts(document_id, person_name, person_name_norm, generated_rel, paragraphs_json, summary_text)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (
                        document_id,
                        e.person_name,
                        e.person_name_norm,
                        e.generated_rel,
                        json.dumps(e.block_indices, ensure_ascii=False),
                        e.summary_text,
                    ),
                )

    def list_documents(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM documents ORDER BY source_rel"))

    def delete_document_by_source_key(self, source_key: str) -> None:
        with self.tx() as conn:
            conn.execute("DELETE FROM documents WHERE source_key=?", (source_key,))

    def search_people(self, filter_keys: set[str], limit: int = 200) -> list[sqlite3.Row]:
        if not filter_keys:
            q = "SELECT DISTINCT person_name, person_name_norm FROM extracts ORDER BY person_name LIMIT ?"
            return list(self.conn.execute(q, (limit,)))
        cond = " OR ".join(["person_name_norm LIKE ?" for _ in filter_keys])
        params = [f"%{k}%" for k in filter_keys] + [limit]
        q = f"SELECT DISTINCT person_name, person_name_norm FROM extracts WHERE {cond} ORDER BY person_name LIMIT ?"
        return list(self.conn.execute(q, params))

    def list_extracts_for_person(self, person_norm: str) -> list[sqlite3.Row]:
        q = """
            SELECT e.*, d.source_rel, d.source_abs
            FROM extracts e
            JOIN documents d ON d.id = e.document_id
            WHERE e.person_name_norm=?
            ORDER BY d.source_rel
        """
        return list(self.conn.execute(q, (person_norm,)))
