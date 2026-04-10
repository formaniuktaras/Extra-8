from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QPushButton, QSplitter, QToolBar, QVBoxLayout, QWidget

from ui.widgets.preview_panel import PreviewPanel
from ui.widgets.source_tree_panel import SourceTreePanel


class DataTab(QWidget):
    refreshRequested = Signal()
    openRequested = Signal()
    diagnosticsRequested = Signal()
    addFilesRequested = Signal()
    newFolderRequested = Signal()
    renameRequested = Signal()
    deleteRequested = Signal()
    openFolderRequested = Signal()
    extractSelectionChanged = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.toolbar = QToolBar()
        self.btn_refresh = QPushButton("Оновити")
        self.btn_open = QPushButton("Відкрити")
        self.btn_open_folder = QPushButton("Відкрити теку")
        self.btn_diag = QPushButton("Діагностика файлу")
        self.btn_add = QPushButton("Додати файли…")
        self.btn_new_folder = QPushButton("Нова папка")
        self.btn_rename = QPushButton("Перейменувати")
        self.btn_delete = QPushButton("Видалити")
        for btn in [
            self.btn_refresh,
            self.btn_open,
            self.btn_open_folder,
            self.btn_diag,
            self.btn_add,
            self.btn_new_folder,
            self.btn_rename,
            self.btn_delete,
        ]:
            self.toolbar.addWidget(btn)

        self.tree = SourceTreePanel()
        self.full_preview = PreviewPanel("Документ цілком")
        self.extract_preview = PreviewPanel("Вміст витягу")
        self.extracts_list = QListWidget()
        self._extract_items: list[dict] = []

        right = QSplitter(Qt.Vertical)
        right.addWidget(self.extracts_list)
        right.addWidget(self.full_preview)
        right.addWidget(self.extract_preview)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(right)

        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(splitter)

        self.btn_refresh.clicked.connect(self.refreshRequested)
        self.btn_open.clicked.connect(self.openRequested)
        self.btn_open_folder.clicked.connect(self.openFolderRequested)
        self.btn_diag.clicked.connect(self.diagnosticsRequested)
        self.btn_add.clicked.connect(self.addFilesRequested)
        self.btn_new_folder.clicked.connect(self.newFolderRequested)
        self.btn_rename.clicked.connect(self.renameRequested)
        self.btn_delete.clicked.connect(self.deleteRequested)
        self.extracts_list.currentRowChanged.connect(self.extractSelectionChanged)

    def set_extract_items(self, extracts: list[dict]) -> None:
        self._extract_items = extracts
        self.extracts_list.clear()
        for item in extracts:
            self.extracts_list.addItem(item.get("generated_rel", "extract"))
        if extracts:
            self.extracts_list.setCurrentRow(0)

    def current_extract(self, index: int) -> dict | None:
        if 0 <= index < len(self._extract_items):
            return self._extract_items[index]
        return None
