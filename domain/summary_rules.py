from __future__ import annotations

import json
import re
from dataclasses import dataclass
from string import Formatter
from typing import Pattern

from domain.models import PersonExtract

DEFAULT_SUMMARY_RULES: list[dict[str, object]] = [
    {
        "name": "Базовий наказ",
        "enabled": True,
        "pattern": r"(?P<surname>[А-ЯІЇЄҐ'’-]+)\s+(?P<first>[А-ЯІЇЄҐ][а-яіїєґ'’-]+)\s+(?P<patronymic>[А-ЯІЇЄҐ][а-яіїєґ'’-]+).*(?P<order_num>№\s*\d+)",
        "flags": "IGNORECASE",
        "template": "{surname} {first} {patronymic} ({order_num})",
    }
]

_SUPPORTED_FLAGS: dict[str, re.RegexFlag] = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "VERBOSE": re.VERBOSE,
}


def default_summary_rules_json() -> str:
    return json.dumps(DEFAULT_SUMMARY_RULES, ensure_ascii=False, indent=2)


@dataclass(slots=True)
class SummaryRule:
    name: str
    enabled: bool
    pattern: str
    flags: str
    template: str

    def compile(self) -> Pattern[str]:
        return re.compile(self.pattern, _parse_flags(self.flags, self.name))


def _parse_flags(flags: str, rule_name: str) -> int:
    if not isinstance(flags, str):
        raise ValueError(f"Invalid flags for rule '{rule_name}': expected string")
    normalized = flags.strip()
    if not normalized:
        return 0
    tokens = [part.strip().upper() for part in re.split(r"[|,\s]+", normalized) if part.strip()]
    acc = 0
    unknown = [token for token in tokens if token not in _SUPPORTED_FLAGS]
    if unknown:
        raise ValueError(f"Invalid flags for rule '{rule_name}': {', '.join(unknown)}")
    for token in tokens:
        acc |= _SUPPORTED_FLAGS[token]
    return acc


def parse_rules(raw_json: str) -> list[SummaryRule]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON for summary rules at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, list):
        raise ValueError("Summary rules must be list")
    rules: list[SummaryRule] = []
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"Rule #{index + 1} must be an object")
        for field in ("name", "enabled", "pattern", "flags", "template"):
            if field not in row:
                raise ValueError(f"Missing field: {field}")
        rule = SummaryRule(
            name=str(row["name"]),
            enabled=bool(row["enabled"]),
            pattern=str(row["pattern"]),
            flags=str(row["flags"]),
            template=str(row["template"]),
        )
        if not rule.name.strip():
            raise ValueError(f"Rule #{index + 1} has empty name")
        if not rule.pattern:
            raise ValueError(f"Invalid pattern for rule '{rule.name}': pattern cannot be empty")
        if not rule.template.strip():
            raise ValueError(f"Template cannot be empty for rule: {rule.name}")
        try:
            rule.compile()
        except re.error as exc:
            raise ValueError(f"Invalid pattern for rule '{rule.name}': {exc}") from exc
        rules.append(rule)
    return rules


def validate_rules_json(raw_json: str) -> None:
    rules = parse_rules(raw_json)
    formatter = Formatter()
    for rule in rules:
        for _, field_name, _, _ in formatter.parse(rule.template):
            if field_name is None:
                continue
            if not field_name.strip():
                raise ValueError(f"Invalid placeholder in rule '{rule.name}'")


def apply_summary_rules(rules: list[SummaryRule], text: str, extract: PersonExtract) -> str:
    derived = {
        "surname": extract.person_name.split()[0] if extract.person_name.split() else "",
        "surname_upper": extract.person_name.split()[0].upper() if extract.person_name.split() else "",
        "first": extract.person_name.split()[1] if len(extract.person_name.split()) > 1 else "",
        "patronymic": extract.person_name.split()[2] if len(extract.person_name.split()) > 2 else "",
        "unit": "",
        "rank": "",
        "position": "",
        "order_num": "",
        "order_date": "",
        "order_phrase": "",
        "death_date": "",
    }
    for rule in rules:
        if not rule.enabled:
            continue
        m = rule.compile().search(text)
        if not m:
            continue
        fields = {**derived, **m.groupdict()}
        return rule.template.format(**fields)
    return fallback_summary(extract)


def fallback_summary(extract: PersonExtract) -> str:
    return f"{extract.person_name}: витяг сформовано, абзаців {len(extract.block_indices)}"
