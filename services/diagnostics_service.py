from __future__ import annotations

from pathlib import Path

from domain.models import DiagnosticsReport
from domain.name_normalization import detect_person_names, detect_uppercase_candidates
from infra.docx.docx_reader import read_docx


class DiagnosticsService:
    def diagnose_file(self, path: Path, source_rel: str) -> DiagnosticsReport:
        try:
            doc = read_docx(path)
            lines = [p.text for p in doc.paragraphs]
            names: set[str] = set()
            matched: list[str] = []
            for line in lines:
                found = detect_person_names(line)
                if found:
                    matched.append(line)
                    names.update(found)
            return DiagnosticsReport(
                source_rel=source_rel,
                total_paragraphs=len(doc.paragraphs),
                body_paragraphs=len(doc.paragraphs),
                unique_names=sorted(names),
                blocks_count=len(doc.body_elements),
                matched_examples=matched[:10],
                uppercase_hints=detect_uppercase_candidates(lines)[:10],
            )
        except Exception as exc:
            return DiagnosticsReport(source_rel, 0, 0, [], 0, [], [], str(exc))
