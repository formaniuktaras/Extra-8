from __future__ import annotations

from types import SimpleNamespace

import pytest

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTextEdit
    from ui.controllers.app_controller import AppController
    from ui.widgets.data_tab import DataTab
except Exception:  # pragma: no cover
    pytestmark = pytest.mark.skip(reason="PySide6 недоступний у тестовому середовищі")
    Qt = object  # type: ignore[assignment]
    QTextEdit = object  # type: ignore[assignment]
    AppController = object  # type: ignore[assignment]
    DataTab = object  # type: ignore[assignment]


class _FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message: str):
        self.messages.append(message)


class _FakeIndex:
    def __init__(self, payload):
        self.payload = payload

    def data(self, role=None):
        if role == 256:
            return self.payload
        return None


class _FakeWin:
    def __init__(self):
        self.search_tab = SimpleNamespace(extract_preview=QTextEdit(), summary_preview=QTextEdit())
        self._status = _FakeStatusBar()

    def statusBar(self):
        return self._status


def test_data_tab_multi_extract_labels(qapp):
    tab = DataTab()
    tab.set_extract_items(
        [
            {
                "person_name": "Іван Петренко",
                "summary_text": "Дуже довгий опис " * 8,
                "generated_rel": "folder/file.docx",
            }
        ]
    )

    text = tab.extracts_list.item(0).text()
    assert "Іван Петренко" in text
    assert "Дуже довгий опис" in text
    assert tab.extracts_list.item(0).toolTip() == "folder/file.docx"


def test_search_tab_preview_uses_preview_service(qapp):
    controller = AppController.__new__(AppController)
    controller.win = _FakeWin()

    class _PreviewStub:
        def __init__(self):
            self.called_with = None
            self.last_extract_mode = "generated"

        def get_extract_preview(self, record):
            self.called_with = record
            return "preview from service"

    controller.preview_service = _PreviewStub()
    payload = {"summary_text": "sum"}

    controller.extract_selected(_FakeIndex(payload))

    assert controller.preview_service.called_with is payload
    assert controller.win.search_tab.extract_preview.toPlainText() == "preview from service"
    assert controller.win.search_tab.summary_preview.toPlainText() == "sum"
