from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.bootstrap import bootstrap
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    deps = bootstrap()
    win = MainWindow(
        indexing_service=deps["indexing_service"],
        search_service=deps["search_service"],
        diagnostics_service=deps["diagnostics_service"],
        settings_service=deps["settings_service"],
        source_root=deps["source_root"],
    )
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
