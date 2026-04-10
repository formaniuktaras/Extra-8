from __future__ import annotations

from pathlib import Path

from domain.models import DiagnosticsReport
from domain.name_normalization import detect_person_names, detect_uppercase_candidates
from infra.docx.docx_reader import read_docx


class DiagnosticsService:
    def diagnose_file(self, path: Path, source_rel: str) -> DiagnosticsReport:
        stat = path.stat() if path.exists() else None
        try:
            doc = read_docx(path)
            lines = [p.text for p in doc.paragraphs]
            names: set[str] = set()
            matched: list[str] = []
            matched_indices: list[int] = []
            for line in lines:
                found = detect_person_names(line)
                if found:
                    matched.append(line)
                    names.update(found)
            for idx, paragraph in enumerate(doc.paragraphs):
                if detect_person_names(paragraph.text):
                    matched_indices.append(idx)
            return DiagnosticsReport(
                source_rel=source_rel,
                source_abs=str(path.resolve()),
                file_size=stat.st_size if stat else 0,
                mtime=stat.st_mtime if stat else 0.0,
                has_styles_xml=doc.styles_tree is not None,
                has_numbering_xml=doc.numbering_tree is not None,
                total_paragraphs=len(doc.paragraphs),
                body_paragraphs=len(doc.paragraphs),
                unique_names=sorted(names),
                blocks_count=len(doc.body_elements),
                paragraph_indices=list(range(len(doc.paragraphs))),
                matched_indices=matched_indices,
                matched_examples=matched[:10],
                uppercase_hints=detect_uppercase_candidates(lines)[:10],
            )
        except Exception as exc:
            return DiagnosticsReport(
                source_rel=source_rel,
                source_abs=str(path.resolve()),
                file_size=stat.st_size if stat else 0,
                mtime=stat.st_mtime if stat else 0.0,
                has_styles_xml=False,
                has_numbering_xml=False,
                total_paragraphs=0,
                body_paragraphs=0,
                unique_names=[],
                blocks_count=0,
                paragraph_indices=[],
                matched_indices=[],
                matched_examples=[],
                uppercase_hints=[],
                error_text=str(exc),
            )
