from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Generic, TypeVar

T = TypeVar("T")


class PreviewCache(Generic[T]):
    def __init__(self, max_entries: int = 64) -> None:
        self.max_entries = max_entries
        self._items: OrderedDict[tuple[str, int], T] = OrderedDict()

    def _resolve_key(self, path: Path) -> tuple[str, int] | None:
        try:
            stat = path.resolve().stat()
        except OSError:
            return None
        return (str(path.resolve()), stat.st_mtime_ns)

    def get(self, path: Path) -> T | None:
        key = self._resolve_key(path)
        if key is None:
            return None
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
        return value

    def put(self, path: Path, value: T) -> None:
        key = self._resolve_key(path)
        if key is None:
            return
        self.invalidate(path)
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)

    def invalidate(self, path: Path) -> None:
        abs_path = str(path.resolve())
        stale_keys = [key for key in self._items.keys() if key[0] == abs_path]
        for key in stale_keys:
            self._items.pop(key, None)

    def clear(self) -> None:
        self._items.clear()
