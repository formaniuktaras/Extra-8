from __future__ import annotations

from domain.name_normalization import build_filter_keys
from infra.storage.sqlite_store import SQLiteStore


class SearchService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def search_people(self, query: str) -> list[dict[str, str]]:
        keys = build_filter_keys(query)
        rows = self.store.search_people(keys)
        return [{"person_name": r["person_name"], "person_name_norm": r["person_name_norm"]} for r in rows]

    def list_extracts(self, person_norm: str) -> list[dict[str, str]]:
        rows = self.store.list_extracts_for_person(person_norm)
        return [dict(r) for r in rows]
