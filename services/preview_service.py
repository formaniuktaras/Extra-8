from __future__ import annotations

import json
from pathlib import Path

from infra.docx.docx_reader import read_docx
from services.preview_cache import PreviewCache
from services.preview_types import PreviewParagraph, StructuredPreview

EXTRACT_UNAVAILABLE_TEXT = "Не вдалося завантажити вміст витягу"
EXTRACT_MISSING_TEXT = "Витяг відсутній"
SOURCE_READ_ERROR_TEXT = "Не вдалося прочитати DOCX"


class PreviewService:
    def __init__(self, output_root: Path, cache_size: int = 64) -> None:
        self.output_root = output_root
        self._text_cache: PreviewCache[str] = PreviewCache(max_entries=cache_size)
        self._source_paragraphs_cache: PreviewCache[list[tuple[int, str]]] = PreviewCache(max_entries=cache_size)
        self._last_extract_mode = "paragraphs_json"

    @property
    def last_extract_mode(self) -> str:
        return self._last_extract_mode

    def get_source_preview(self, source_path: Path) -> str:
        cached = self._text_cache.get(source_path)
        if cached is not None:
            return cached
        source_paragraphs = self._load_source_paragraphs(source_path)
        if source_paragraphs is None:
            return SOURCE_READ_ERROR_TEXT
        preview = "\n".join(text for _, text in source_paragraphs if text)
        self._text_cache.put(source_path, preview)
        return preview

    def get_extract_preview(self, record: dict) -> str:
        json_text = record.get("paragraphs_json") or "[]"
        try:
            blocks = json.loads(json_text)
        except Exception:
            blocks = []
        if isinstance(blocks, list) and blocks and all(isinstance(index, int) for index in blocks):
            source_abs = record.get("source_abs")
            if source_abs:
                source_paragraphs = self._load_source_paragraphs(Path(source_abs))
                if source_paragraphs:
                    mapped = {idx: text for idx, text in source_paragraphs}
                    lines = [mapped.get(index, "").strip() for index in blocks]
                    lines = [line for line in lines if line]
                    if lines:
                        self._last_extract_mode = "paragraphs_json"
                        return "\n".join(lines)

        paragraphs_text_raw = record.get("paragraphs_text") or []
        if isinstance(paragraphs_text_raw, str):
            try:
                paragraphs_text = json.loads(paragraphs_text_raw)
            except Exception:
                paragraphs_text = [paragraphs_text_raw]
        else:
            paragraphs_text = paragraphs_text_raw
        if paragraphs_text:
            lines = [str(line).strip() for line in paragraphs_text if str(line).strip()]
            if lines:
                self._last_extract_mode = "paragraphs_text"
                return "\n".join(lines)

        self._last_extract_mode = "empty"
        return EXTRACT_MISSING_TEXT

    def build_highlighted_source_preview(self, source_path: Path, selected_indices: list[int]) -> StructuredPreview:
        selected = set(selected_indices)
        source_paragraphs = self._load_source_paragraphs(source_path)
        if source_paragraphs is None:
            return StructuredPreview(paragraphs=[], plain_text=SOURCE_READ_ERROR_TEXT)
        paragraphs = [
            PreviewParagraph(index=index, text=text, is_selected=(index in selected)) for index, text in source_paragraphs
        ]
        plain_text = "\n".join(p.text for p in paragraphs if p.text)
        return StructuredPreview(paragraphs=paragraphs, plain_text=plain_text)

    def _load_source_paragraphs(self, source_path: Path) -> list[tuple[int, str]] | None:
        cached = self._source_paragraphs_cache.get(source_path)
        if cached is not None:
            return cached
        try:
            doc = read_docx(source_path)
        except Exception:
            return None
        paragraphs = [(p.block_index, p.text) for p in doc.paragraphs]
        self._source_paragraphs_cache.put(source_path, paragraphs)
        return paragraphs
