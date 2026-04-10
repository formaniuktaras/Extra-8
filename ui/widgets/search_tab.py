from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.extracts_list import ExtractsListView
from ui.widgets.people_list import PeopleListView
from ui.widgets.preview_panel import PreviewPanel
from ui.widgets.summary_panel import SummaryPanel


class SearchTab(QWidget):
    queryChanged = Signal(str)
    rebuildRequested = Signal()
    quickCheckRequested = Signal()
    openSourceRequested = Signal()
    openFolderRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.search_edit = QLineEdit()
        self.results_label = QLabel("0 результатів")
        self.rebuild_btn = QPushButton("Перебудувати індекс")
        self.quick_btn = QPushButton("Швидка перевірка")
        self.open_source_btn = QPushButton("Відкрити DOCX")
        self.open_folder_btn = QPushButton("Відкрити теку")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        self.people_list = PeopleListView()
        self.extracts_list = ExtractsListView()
        self.extract_preview = PreviewPanel("Попередній перегляд витягу")
        self.summary_preview = SummaryPanel("Короткий опис")

        top = QHBoxLayout()
        top.addWidget(QLabel("Пошук П.І.Б."))
        top.addWidget(self.search_edit)
        top.addWidget(self.results_label)
        top.addWidget(self.rebuild_btn)
        top.addWidget(self.quick_btn)
        top.addWidget(self.open_source_btn)
        top.addWidget(self.open_folder_btn)
        top.addWidget(self.theme_combo)

        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setObjectName("search_right_splitter")
        self.right_splitter.addWidget(self.extracts_list)
        self.right_splitter.addWidget(self.extract_preview)
        self.right_splitter.addWidget(self.summary_preview)

        self.center_splitter = QSplitter(Qt.Horizontal)
        self.center_splitter.setObjectName("search_center_splitter")
        self.center_splitter.addWidget(self.people_list)
        self.center_splitter.addWidget(self.right_splitter)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.center_splitter)

        self.search_edit.textChanged.connect(self.queryChanged)
        self.rebuild_btn.clicked.connect(self.rebuildRequested)
        self.quick_btn.clicked.connect(self.quickCheckRequested)
        self.open_source_btn.clicked.connect(self.openSourceRequested)
        self.open_folder_btn.clicked.connect(self.openFolderRequested)

    def set_people_count(self, count: int) -> None:
        self.results_label.setText("Нічого не знайдено" if count == 0 else f"{count} результатів")
