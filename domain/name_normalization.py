from __future__ import annotations

import re
from typing import Iterable

APOSTROPHES = "'’`ʼ"
CONFUSABLES = str.maketrans({
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "I": "І", "K": "К", "M": "М", "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У",
    "a": "а", "c": "с", "e": "е", "i": "і", "o": "о", "p": "р", "x": "х", "y": "у",
})

NAME_RE = re.compile(
    r"\b([А-ЯІЇЄҐ][А-ЯІЇЄҐ'’\-]{1,}|[А-ЯІЇЄҐ][а-яіїєґ'’\-]+)\s+([А-ЯІЇЄҐ][а-яіїєґ'’\-]+)\s+([А-ЯІЇЄҐ][а-яіїєґ'’\-]+)\b"
)


def normalize_text(text: str) -> str:
    text = text.translate(CONFUSABLES)
    for ap in APOSTROPHES:
        text = text.replace(ap, "'")
    text = re.sub(r"\s+", " ", text.strip())
    return text


def normalize_person_key(name: str) -> str:
    raw = normalize_text(name).lower()
    raw = re.sub(r"[^а-яіїєґ'\- ]+", "", raw)
    parts = [stem_like_token(p) for p in raw.split() if p]
    return " ".join(parts)


def stem_like_token(token: str) -> str:
    suffixes = ("ові", "еві", "ому", "а", "у", "ом", "ою", "і", "е", "я", "ю")
    for s in suffixes:
        if len(token) > 4 and token.endswith(s):
            return token[: -len(s)]
    return token


def build_filter_keys(query: str) -> set[str]:
    norm = normalize_person_key(query)
    toks = norm.split()
    keys = {norm}
    if toks:
        keys.add(" ".join(toks[:2]))
        keys.add(toks[0])
    return {k for k in keys if k}


def detect_person_names(text: str) -> list[str]:
    clean = normalize_text(text)
    return [" ".join(m.groups()) for m in NAME_RE.finditer(clean)]


def detect_uppercase_candidates(lines: Iterable[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        n = normalize_text(line)
        if len(n) > 8 and re.search(r"\b[А-ЯІЇЄҐ]{3,}\b", n):
            result.append(n)
    return result
