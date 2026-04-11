from types import SimpleNamespace

from core.settings import UserSettings
from services.extract_service import ExtractService


def _doc(paragraphs: list[str]):
    return SimpleNamespace(
        paragraphs=[SimpleNamespace(text=text, block_index=i) for i, text in enumerate(paragraphs)]
    )


def test_extract_service_returns_text_only_extracts(tmp_path):
    service = ExtractService(UserSettings().summary_rules_json)
    doc = _doc([
        "РОЗДІЛ:",
        "ПЕТРЕНКО Іван Іванович",
        "Детальний опис",
    ])

    extracts = service.build_extracts_for_doc(doc, tmp_path, "a.docx")

    assert extracts
    item = extracts[0]
    assert item.generated_rel is None
    assert item.block_indices
    assert item.paragraphs_text
    assert item.summary_text
    assert not list(tmp_path.rglob("*.docx"))
