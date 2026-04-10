from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PreviewParagraph:
    index: int
    text: str
    is_selected: bool = False


@dataclass(slots=True)
class StructuredPreview:
    paragraphs: list[PreviewParagraph]
    plain_text: str
