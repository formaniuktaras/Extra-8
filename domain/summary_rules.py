from __future__ import annotations

import json
import re
from dataclasses import dataclass
from string import Formatter
from typing import Pattern

from domain.models import PersonExtract


@dataclass(slots=True)
class SummaryRule:
    name: str
    enabled: bool
    pattern: str
    flags: str
    template: str

    def compile(self) -> Pattern[str]:
        fl = 0
        if "IGNORECASE" in self.flags.upper():
            fl |= re.IGNORECASE
        return re.compile(self.pattern, fl)


def parse_rules(raw_json: str) -> list[SummaryRule]:
    data = json.loads(raw_json)
    if not isinstance(data, list):
        raise ValueError("Summary rules must be list")
    rules: list[SummaryRule] = []
    for row in data:
        for field in ("name", "enabled", "pattern", "flags", "template"):
            if field not in row:
                raise ValueError(f"Missing field: {field}")
        rule = SummaryRule(**row)
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
