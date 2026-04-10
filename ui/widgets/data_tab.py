from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QLabel, QListWidget, QPushButton, QSplitter, QToolBar, QVBoxLayout, QWidget

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
    highlightToggled = Signal(bool)

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
        self.extracts_info_label = QLabel("Оберіть документ")
        self.highlight_checkbox = QCheckBox("Підсвічувати абзаци витягу")
        self.highlight_checkbox.setChecked(True)
        self.extracts_list = QListWidget()
        self._extract_items: list[dict] = []

        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setObjectName("data_right_splitter")
        extracts_box = QWidget()
        extracts_layout = QVBoxLayout(extracts_box)
        extracts_layout.setContentsMargins(0, 0, 0, 0)
        extracts_layout.addWidget(self.extracts_info_label)
        extracts_layout.addWidget(self.highlight_checkbox)
        extracts_layout.addWidget(self.extracts_list)
        self.right_splitter.addWidget(extracts_box)
        self.right_splitter.addWidget(self.full_preview)
        self.right_splitter.addWidget(self.extract_preview)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName("data_main_splitter")
        self.main_splitter.addWidget(self.tree)
        self.main_splitter.addWidget(self.right_splitter)

        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.main_splitter)

        self.btn_refresh.clicked.connect(self.refreshRequested)
        self.btn_open.clicked.connect(self.openRequested)
        self.btn_open_folder.clicked.connect(self.openFolderRequested)
        self.btn_diag.clicked.connect(self.diagnosticsRequested)
        self.btn_add.clicked.connect(self.addFilesRequested)
        self.btn_new_folder.clicked.connect(self.newFolderRequested)
        self.btn_rename.clicked.connect(self.renameRequested)
        self.btn_delete.clicked.connect(self.deleteRequested)
        self.extracts_list.currentRowChanged.connect(self.extractSelectionChanged)
        self.highlight_checkbox.toggled.connect(self.highlightToggled)

    def set_extract_items(self, extracts: list[dict]) -> None:
        self._extract_items = extracts
        self.extracts_list.clear()
        self.extracts_info_label.setText(f"Для цього документа знайдено {len(extracts)} витягів")
        for item in extracts:
            person = item.get("person_name") or "Без П.І.Б."
            summary = (item.get("summary_text") or "").strip()
            short_summary = (summary[:80] + "…") if len(summary) > 80 else summary
            line = person if not short_summary else f"{person} — {short_summary}"
            self.extracts_list.addItem(line)
            self.extracts_list.item(self.extracts_list.count() - 1).setToolTip(item.get("generated_rel", ""))
        if extracts:
            self.extracts_list.setCurrentRow(0)

    def current_extract(self, index: int) -> dict | None:
        if 0 <= index < len(self._extract_items):
            return self._extract_items[index]
        return None
