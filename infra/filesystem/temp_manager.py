from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


class TempManager:
    def __init__(self, prefix: str = "docx_extract_") -> None:
        self.root = Path(tempfile.mkdtemp(prefix=prefix))

    def alloc(self, suffix: str = ".tmp") -> Path:
        fd, p = tempfile.mkstemp(dir=self.root, suffix=suffix)
        Path(p).unlink(missing_ok=True)
        return Path(p)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
