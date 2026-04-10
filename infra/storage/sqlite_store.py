from __future__ import annotations

import json
import random
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from domain.models import PersonExtract, SourceDocument
from infra.storage.migrations import migrate_if_needed


@dataclass(slots=True)
class SQLiteRetryPolicy:
    retries: int = 5
    base_delay: float = 0.05
    max_delay: float = 0.5


class SQLiteConnectionFactory:
    def __init__(self, db_path: Path, retry_policy: SQLiteRetryPolicy | None = None) -> None:
        self.db_path = db_path
        self.retry_policy = retry_policy or SQLiteRetryPolicy()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            migrate_if_needed(conn)

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=2.0)
        self._configure_connection(conn)
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        for attempt in range(self.retry_policy.retries + 1):
            with self.connection() as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    yield conn
                    conn.commit()
                    return
                except sqlite3.OperationalError as exc:
                    conn.rollback()
                    if "locked" not in str(exc).lower() or attempt >= self.retry_policy.retries:
                        raise
                    sleep_for = min(
                        self.retry_policy.max_delay,
                        self.retry_policy.base_delay * (2**attempt) + random.uniform(0.0, 0.02),
                    )
                    time.sleep(sleep_for)
                except Exception:
                    conn.rollback()
                    raise


class SQLiteStore:
    def __init__(self, db_path: Path, connection_factory: SQLiteConnectionFactory | None = None) -> None:
        self.db_path = db_path
        self.connection_factory = connection_factory or SQLiteConnectionFactory(db_path)

    def upsert_document(self, doc: SourceDocument) -> int:
        with self.connection_factory.transaction() as conn:
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
            if row is None:
                raise RuntimeError("Failed to upsert document")
            return int(row["id"])

    def replace_extracts_for_document(self, document_id: int, extracts: list[PersonExtract]) -> None:
        with self.connection_factory.transaction() as conn:
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
        with self.connection_factory.connection() as conn:
            return list(conn.execute("SELECT * FROM documents ORDER BY source_rel"))

    def delete_document_by_source_key(self, source_key: str) -> None:
        with self.connection_factory.transaction() as conn:
            conn.execute("DELETE FROM documents WHERE source_key=?", (source_key,))

    def list_generated_rels_for_source_key(self, source_key: str) -> list[str]:
        with self.connection_factory.connection() as conn:
            rows = conn.execute(
                """
                SELECT e.generated_rel
                FROM extracts e
                JOIN documents d ON d.id = e.document_id
                WHERE d.source_key=?
                """,
                (source_key,),
            ).fetchall()
        return [str(r["generated_rel"]) for r in rows]

    def search_people(self, filter_keys: set[str], limit: int = 200) -> list[sqlite3.Row]:
        with self.connection_factory.connection() as conn:
            if not filter_keys:
                q = "SELECT DISTINCT person_name, person_name_norm FROM extracts ORDER BY person_name LIMIT ?"
                return list(conn.execute(q, (limit,)))
            cond = " OR ".join(["person_name_norm LIKE ?" for _ in filter_keys])
            starts_cond = " OR ".join(["person_name_norm LIKE ?" for _ in filter_keys])
            params = [f"%{k}%" for k in filter_keys] + [f"{k}%" for k in filter_keys] + [limit]
            q = (
                f"SELECT DISTINCT person_name, person_name_norm FROM extracts WHERE {cond} "
                f"ORDER BY CASE WHEN {starts_cond} THEN 0 ELSE 1 END, person_name LIMIT ?"
            )
            return list(conn.execute(q, params))

    def list_extracts_for_person(self, person_norm: str) -> list[sqlite3.Row]:
        q = """
            SELECT e.*, d.source_rel, d.source_abs
            FROM extracts e
            JOIN documents d ON d.id = e.document_id
            WHERE e.person_name_norm=?
            ORDER BY d.source_rel
        """
        with self.connection_factory.connection() as conn:
            return list(conn.execute(q, (person_norm,)))

    def get_extract_by_generated_rel(self, generated_rel: str) -> sqlite3.Row | None:
        with self.connection_factory.connection() as conn:
            return conn.execute(
                """
                SELECT e.*, d.source_rel, d.source_abs
                FROM extracts e
                JOIN documents d ON d.id = e.document_id
                WHERE e.generated_rel=?
                """,
                (generated_rel,),
            ).fetchone()
