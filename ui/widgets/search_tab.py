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

    def __init__(self) -> None:
        super().__init__()
        self.search_edit = QLineEdit()
        self.rebuild_btn = QPushButton("Перебудувати індекс")
        self.quick_btn = QPushButton("Швидка перевірка")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        self.people_list = PeopleListView()
        self.extracts_list = ExtractsListView()
        self.extract_preview = PreviewPanel("Попередній перегляд витягу")
        self.summary_preview = SummaryPanel("Короткий опис")

        top = QHBoxLayout()
        top.addWidget(QLabel("Пошук П.І.Б."))
        top.addWidget(self.search_edit)
        top.addWidget(self.rebuild_btn)
        top.addWidget(self.quick_btn)
        top.addWidget(self.theme_combo)

        right = QSplitter(Qt.Vertical)
        right.addWidget(self.extracts_list)
        right.addWidget(self.extract_preview)
        right.addWidget(self.summary_preview)

        center = QSplitter(Qt.Horizontal)
        center.addWidget(self.people_list)
        center.addWidget(right)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(center)

        self.search_edit.textChanged.connect(self.queryChanged)
        self.rebuild_btn.clicked.connect(self.rebuildRequested)
        self.quick_btn.clicked.connect(self.quickCheckRequested)
