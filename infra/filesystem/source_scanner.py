from __future__ import annotations

from pathlib import Path

IGNORED_PREFIXES = ("~$",)
IGNORED_SUFFIXES = (".tmp", ".bak")


def scan_docx_files(source_root: Path) -> list[Path]:
    if not source_root.exists():
        return []
    files: list[Path] = []
    for path in source_root.rglob("*.docx"):
        name = path.name.lower()
        if any(path.name.startswith(p) for p in IGNORED_PREFIXES):
            continue
        if any(name.endswith(s) for s in IGNORED_SUFFIXES):
            continue
        files.append(path)
    return sorted(files)
