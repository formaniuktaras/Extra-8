from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from domain.models import PersonExtract
from domain.name_normalization import detect_person_names, normalize_person_key
from domain.summary_rules import apply_summary_rules, parse_rules
from infra.docx.docx_writer import build_extract_package
from infra.filesystem.file_ops import SafeFileOperator


class ExtractSelectionStrategy(Protocol):
    def select(self, matched_indices: set[int], paragraph_count: int) -> list[int]: ...


@dataclass(slots=True)
class ContextWindowSelectionStrategy:
    include_previous: int = 1
    include_next: int = 1

    def select(self, matched_indices: set[int], paragraph_count: int) -> list[int]:
        selected: set[int] = set()
        for idx in matched_indices:
            selected.add(idx)
            for step in range(1, self.include_previous + 1):
                if idx - step >= 0:
                    selected.add(idx - step)
            for step in range(1, self.include_next + 1):
                if idx + step < paragraph_count:
                    selected.add(idx + step)
        return sorted(selected)


class ExtractService:
    def __init__(
        self,
        file_ops: SafeFileOperator,
        rules_json: str,
        selection_strategy: ExtractSelectionStrategy | None = None,
    ) -> None:
        self.file_ops = file_ops
        self.rules = parse_rules(rules_json)
        self.selection_strategy = selection_strategy or ContextWindowSelectionStrategy()

    def build_extracts_for_doc(self, doc, output_root: Path, source_rel: str) -> list[PersonExtract]:
        people_blocks: dict[str, set[int]] = {}
        for i, p in enumerate(doc.paragraphs):
            for person in detect_person_names(p.text):
                people_blocks.setdefault(person, set()).add(i)
        extracts: list[PersonExtract] = []
        for person_name, paragraph_positions in people_blocks.items():
            safe_name = normalize_person_key(person_name).replace(" ", "_")
            rel = Path(source_rel).with_suffix("").as_posix().replace("/", "_") + f"__{safe_name}.docx"
            out_path = output_root / rel
            selected_paragraph_positions = self.selection_strategy.select(paragraph_positions, len(doc.paragraphs))
            selected_blocks = sorted({doc.paragraphs[i].block_index for i in selected_paragraph_positions})
            payload = build_extract_package(doc, selected_blocks)
            self.file_ops.atomic_write_bytes(out_path, payload)
            paragraph_texts = [doc.paragraphs[i].text for i in selected_paragraph_positions]
            ext = PersonExtract(
                person_name=person_name,
                person_name_norm=normalize_person_key(person_name),
                block_indices=selected_blocks,
                generated_rel=rel,
                paragraphs_text=paragraph_texts,
            )
            ext.summary_text = apply_summary_rules(self.rules, "\n".join(ext.paragraphs_text), ext)
            extracts.append(ext)
        return extracts
