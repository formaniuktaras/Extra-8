from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileSystemModel


class SourceTreeModel(QFileSystemModel):
    def __init__(self, root: Path) -> None:
        super().__init__()
        self.setRootPath(str(root))
