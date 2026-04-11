from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from string import Formatter
from typing import Pattern

from domain.models import PersonExtract

logger = logging.getLogger(__name__)

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
        if not isinstance(self.pattern, str):
            raise ValueError(f"Invalid pattern in rule '{self.name}': pattern must be a string")
        if "?P[" in self.pattern:
            raise ValueError(
                f"Invalid pattern in rule '{self.name}':\n"
                f"Pattern: {self.pattern}\n"
                "Error: Можливо пошкоджено regex (очікується ?P<...>)\n"
                f"Position: {self.pattern.find('?P[')}"
            )
        try:
            return re.compile(self.pattern, _parse_flags(self.flags, self.name))
        except re.error as exc:
            logger.error("Failed to compile summary regex for rule '%s': %r", self.name, self.pattern)
            pos = exc.pos if exc.pos is not None else "n/a"
            raise ValueError(
                f"Invalid pattern in rule '{self.name}':\n"
                f"Pattern: {self.pattern}\n"
                f"Error: {exc.msg}\n"
                f"Position: {pos}"
            ) from exc


def _serialize_rules(rules: list[SummaryRule]) -> str:
    payload = [
        {
            "name": rule.name,
            "enabled": rule.enabled,
            "pattern": rule.pattern,
            "flags": rule.flags,
            "template": rule.template,
        }
        for rule in rules
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


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
    rules = _parse_rules_payload(data)
    _validate_roundtrip_integrity(rules)
    return rules


def _parse_rules_payload(data: object) -> list[SummaryRule]:
    if not isinstance(data, list):
        raise ValueError("Summary rules must be list")
    rules: list[SummaryRule] = []
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"Rule #{index + 1} must be an object")
        for field in ("name", "enabled", "pattern", "flags", "template"):
            if field not in row:
                raise ValueError(f"Missing field: {field}")
        if not isinstance(row["name"], str):
            raise ValueError(f"Rule #{index + 1}: name must be string")
        if not isinstance(row["enabled"], bool):
            raise ValueError(f"Rule #{index + 1}: enabled must be boolean")
        if not isinstance(row["pattern"], str):
            raise ValueError(f"Rule #{index + 1}: pattern must be string")
        if not isinstance(row["flags"], str):
            raise ValueError(f"Rule #{index + 1}: flags must be string")
        if not isinstance(row["template"], str):
            raise ValueError(f"Rule #{index + 1}: template must be string")
        rule = SummaryRule(
            name=row["name"],
            enabled=row["enabled"],
            pattern=row["pattern"],
            flags=row["flags"],
            template=row["template"],
        )
        if not rule.name.strip():
            raise ValueError(f"Rule #{index + 1} has empty name")
        if not rule.pattern:
            raise ValueError(f"Invalid pattern in rule '{rule.name}':\nPattern: {rule.pattern}\nError: pattern cannot be empty\nPosition: 0")
        if not rule.template.strip():
            raise ValueError(f"Template cannot be empty for rule: {rule.name}")
        rule.compile()
        rules.append(rule)
    return rules


def _validate_roundtrip_integrity(rules: list[SummaryRule]) -> None:
    roundtrip_json = _serialize_rules(rules)
    roundtrip_data = json.loads(roundtrip_json)
    roundtrip_rules = _parse_rules_payload(roundtrip_data)
    source = [(r.name, r.enabled, r.pattern, r.flags, r.template) for r in rules]
    loaded = [(r.name, r.enabled, r.pattern, r.flags, r.template) for r in roundtrip_rules]
    if source != loaded:
        raise ValueError("Summary rules roundtrip mismatch: rules changed after serialize/deserialize")


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
