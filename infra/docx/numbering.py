from __future__ import annotations

from xml.etree import ElementTree as ET

from infra.docx.docx_reader import NS


def _get_numpr(p: ET.Element) -> tuple[str | None, int | None]:
    num_pr = p.find("w:pPr/w:numPr", NS)
    if num_pr is None:
        return None, None
    num_id = num_pr.find("w:numId", NS)
    ilvl = num_pr.find("w:ilvl", NS)
    num_val = num_id.attrib.get(f"{{{NS['w']}}}val") if num_id is not None else None
    ilvl_val = ilvl.attrib.get(f"{{{NS['w']}}}val") if ilvl is not None else None
    return num_val, int(ilvl_val) if ilvl_val is not None else None


def resolve_numbering_prefix(paragraph: ET.Element, counters: dict[tuple[str, int], int]) -> str:
    num_id, ilvl = _get_numpr(paragraph)
    if num_id is None or ilvl is None:
        return ""
    key = (num_id, ilvl)
    counters[key] = counters.get(key, 0) + 1
    parts = []
    for lvl in range(ilvl + 1):
        parts.append(str(counters.get((num_id, lvl), 1)))
    return ".".join(parts) + ". "


def merge_prefix_if_needed(prefix: str, text: str) -> str:
    if not prefix:
        return text
    if text.startswith(prefix.strip()):
        return text
    return prefix + text
