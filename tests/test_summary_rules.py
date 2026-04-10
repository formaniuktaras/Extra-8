import pytest

from domain.models import PersonExtract
from domain.summary_rules import apply_summary_rules, fallback_summary, parse_rules


RAW = """
[
  {"name":"R1","enabled":true,"pattern":"(?P<order_num>№\\\\s*\\\\d+)","flags":"IGNORECASE","template":"{surname} {order_num}"}
]
"""


def test_summary_rules_parser():
    rules = parse_rules(RAW)
    assert len(rules) == 1


def test_summary_rule_application():
    extract = PersonExtract("ПЕТРЕНКО Іван Іванович", "", [1], "a.docx")
    text = "Наказ № 123"
    out = apply_summary_rules(parse_rules(RAW), text, extract)
    assert "№ 123" in out


def test_fallback_summary_generation():
    extract = PersonExtract("ПЕТРЕНКО Іван Іванович", "", [1, 2], "a.docx")
    out = fallback_summary(extract)
    assert "абзаців 2" in out


def test_summary_parser_validation_error():
    with pytest.raises(ValueError):
        parse_rules("{}")
