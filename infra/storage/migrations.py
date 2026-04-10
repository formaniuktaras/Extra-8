from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_key TEXT UNIQUE NOT NULL,
            source_rel TEXT NOT NULL,
            source_abs TEXT,
            mtime REAL NOT NULL,
            size INTEGER NOT NULL,
            hash TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS extracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            person_name TEXT NOT NULL,
            person_name_norm TEXT NOT NULL,
            generated_rel TEXT NOT NULL,
            paragraphs_json TEXT NOT NULL,
            summary_text TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_extracts_person_norm ON extracts(person_name_norm);")
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))
    conn.commit()


def migrate_if_needed(conn: sqlite3.Connection) -> None:
    cur = conn.execute("SELECT value FROM meta WHERE key='schema_version'")
    row = cur.fetchone()
    if not row:
        init_schema(conn)
        return
    version = int(row[0])
    if version < SCHEMA_VERSION:
        init_schema(conn)
