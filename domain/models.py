from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ParagraphDescriptor:
    text: str
    block_index: int
    has_numbering: bool = False
    numbering_prefix: str = ""


@dataclass(slots=True)
class SourceDocument:
    source_key: str
    source_rel: str
    source_abs: Path
    mtime: float
    size: int
    sha1: str | None = None


@dataclass(slots=True)
class PersonExtract:
    person_name: str
    person_name_norm: str
    block_indices: list[int]
    generated_rel: str
    summary_text: str = ""
    paragraphs_text: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DiagnosticsReport:
    source_rel: str
    source_abs: str
    file_size: int
    mtime: float
    has_styles_xml: bool
    has_numbering_xml: bool
    total_paragraphs: int
    body_paragraphs: int
    unique_names: list[str]
    blocks_count: int
    paragraph_indices: list[int]
    matched_indices: list[int]
    matched_examples: list[str]
    uppercase_hints: list[str]
    error_text: str | None = None
