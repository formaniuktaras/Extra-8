from __future__ import annotations

from pathlib import Path

from domain.models import PersonExtract
from domain.name_normalization import detect_person_names, normalize_person_key
from domain.summary_rules import apply_summary_rules, parse_rules
from infra.docx.docx_writer import write_extract_docx
from infra.filesystem.file_ops import SafeFileOperator


class ExtractService:
    def __init__(self, file_ops: SafeFileOperator, rules_json: str) -> None:
        self.file_ops = file_ops
        self.rules = parse_rules(rules_json)

    def build_extracts_for_doc(self, doc, output_root: Path, source_rel: str) -> list[PersonExtract]:
        people_blocks: dict[str, list[int]] = {}
        for p in doc.paragraphs:
            for person in detect_person_names(p.text):
                people_blocks.setdefault(person, []).append(p.block_index)
        extracts: list[PersonExtract] = []
        for person_name, indices in people_blocks.items():
            safe_name = normalize_person_key(person_name).replace(" ", "_")
            rel = Path(source_rel).with_suffix("").as_posix().replace("/", "_") + f"__{safe_name}.docx"
            out_path = output_root / rel
            payload = write_extract_docx(doc, sorted(set(indices)), out_path)
            self.file_ops.atomic_replace_bytes(out_path, payload)
            ext = PersonExtract(
                person_name=person_name,
                person_name_norm=normalize_person_key(person_name),
                block_indices=sorted(set(indices)),
                generated_rel=rel,
                paragraphs_text=[doc.paragraphs[i].text for i in range(len(doc.paragraphs)) if doc.paragraphs[i].block_index in indices],
            )
            ext.summary_text = apply_summary_rules(self.rules, "\n".join(ext.paragraphs_text), ext)
            extracts.append(ext)
        return extracts
