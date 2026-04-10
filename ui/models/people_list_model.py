from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class PeopleListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self._items: list[dict[str, str]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == Qt.DisplayRole:
            return item["person_name"]
        if role == Qt.UserRole:
            return item
        return None

    def set_items(self, items: list[dict[str, str]]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()
