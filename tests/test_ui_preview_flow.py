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


class _FakeCurrentIndex:
    def __init__(self, payload):
        self.payload = payload

    def isValid(self):
        return self.payload is not None

    def data(self, role=None):
        if role == 256:
            return self.payload
        return None


class _FakeWin:
    def __init__(self, payload=None):
        self.search_tab = SimpleNamespace(
            extract_preview=QTextEdit(),
            summary_preview=QTextEdit(),
            extracts_list=SimpleNamespace(currentIndex=lambda: _FakeCurrentIndex(payload)),
        )
        self._status = _FakeStatusBar()

    def statusBar(self):
        return self._status


def test_data_tab_highlight_works_without_extract_preview_panel(qapp):
    tab = DataTab()
    assert not hasattr(tab, "extract_preview")
    tab.set_extract_items(
        [
            {
                "person_name": "Іван Петренко",
                "summary_text": "Дуже довгий опис " * 8,
                "source_rel": "folder/file.docx",
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

        def get_extract_preview(self, record):
            self.called_with = record
            return "preview from service"

    controller.preview_service = _PreviewStub()
    payload = {"summary_text": "sum"}

    controller.extract_selected(_FakeIndex(payload))

    assert controller.preview_service.called_with is payload
    assert controller.win.search_tab.extract_preview.toPlainText() == "preview from service"
    assert controller.win.search_tab.summary_preview.toPlainText() == "sum"


def test_open_original_action_still_works(qapp, monkeypatch, tmp_path):
    source = tmp_path / "a.docx"
    source.write_bytes(b"x")
    payload = {"source_abs": str(source)}

    controller = AppController.__new__(AppController)
    controller.win = _FakeWin(payload=payload)
    opened = []
    monkeypatch.setattr(controller, "_open_path", lambda path: opened.append(path))

    controller.open_source_docx_from_search()

    assert opened == [source]
