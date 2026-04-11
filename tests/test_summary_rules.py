import pytest

from core.config import AppConfig
from core.settings import SettingsManager, UserSettings
from domain.models import PersonExtract
from domain.summary_rules import (
    apply_summary_rules,
    default_summary_rules_json,
    fallback_summary,
    parse_rules,
    serialize_rules,
)
from services.extract_service import ExtractService


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


def test_default_summary_rules_compile_successfully():
    rules = parse_rules(default_summary_rules_json())
    assert rules
    for rule in rules:
        assert rule.compile()


def test_summary_rules_json_roundtrip_preserves_pattern(tmp_path):
    source_json = default_summary_rules_json()
    source_rules = parse_rules(source_json)

    manager = SettingsManager(tmp_path)
    manager.save(UserSettings(summary_rules_json=source_json))
    reloaded = manager.load().summary_rules_json
    reloaded_rules = parse_rules(reloaded)

    assert [(r.name, r.pattern, r.flags, r.template, r.enabled) for r in source_rules] == [
        (r.name, r.pattern, r.flags, r.template, r.enabled) for r in reloaded_rules
    ]


def test_named_group_pattern_compiles_correctly():
    payload = """
    [
      {"name":"named","enabled":true,"pattern":"(?P<order_num>№\\\\s*\\\\d+)","flags":"IGNORECASE","template":"{order_num}"}
    ]
    """
    rules = parse_rules(payload)
    assert rules[0].compile().search("Наказ № 777").group("order_num") == "№ 777"


def test_regex_named_groups_not_corrupted():
    payload = """
    [
      {"name":"named","enabled":true,"pattern":"(?P<order_num>№\\\\s*\\\\d+)","flags":"IGNORECASE","template":"{order_num}"}
    ]
    """
    rules = parse_rules(payload)
    assert rules[0].pattern == "(?P<order_num>№\\s*\\d+)"


def test_summary_rules_roundtrip_integrity():
    payload = """
    [
      {"name":"named","enabled":true,"pattern":"(?P<order_num>№\\\\s*\\\\d+)","flags":"IGNORECASE","template":"{order_num}"}
    ]
    """
    rules = parse_rules(payload)
    assert rules[0].compile().search("Наказ № 1")


def test_summary_rules_strict_pattern_roundtrip_parse_serialize_parse():
    original_json = """
    [
      {"name":"named","enabled":true,"pattern":"(?P<order_num>№\\\\s*\\\\d+)","flags":"IGNORECASE","template":"{order_num}"},
      {"name":"name","enabled":true,"pattern":"(?P<name>\\\\w+)","flags":"","template":"{name}"}
    ]
    """
    first_parse = parse_rules(original_json)
    serialized = serialize_rules(first_parse)
    second_parse = parse_rules(serialized)
    assert [rule.pattern for rule in first_parse] == [rule.pattern for rule in second_parse]


def test_invalid_regex_rule_is_rejected_without_overwriting_active_rules():
    service = ExtractService(default_summary_rules_json())
    before = service.rules_json

    with pytest.raises(ValueError):
        service.update_rules(
            '[{"name":"broken","enabled":true,"pattern":"(?P[bad","flags":"","template":"{surname}"}]'
        )

    assert service.rules_json == before
    assert service.summarize_record(
        {
            "person_name": "ПЕТРЕНКО Іван Іванович",
            "person_name_norm": "петренкоіваніванович",
            "paragraphs_json": "[1]",
            "paragraphs_text": '["Наказ № 55"]',
            "generated_rel": "a.docx",
        }
    )


def test_invalid_regex_does_not_override_existing_rules():
    service = ExtractService(default_summary_rules_json())
    before = service.rules_json

    with pytest.raises(ValueError):
        service.update_rules('[{"name":"broken","enabled":true,"pattern":"(?P[bad","flags":"","template":"x"}]')

    assert service.rules_json == before


def test_apply_updates_summary_rules_immediately():
    extract_service = ExtractService(default_summary_rules_json())
    extract_service.update_rules(
        UserSettings(
            summary_rules_json='[{"name":"R","enabled":true,"pattern":"(?P<order_num>№\\\\s*\\\\d+)","flags":"IGNORECASE","template":"{order_num}"}]'
        ).summary_rules_json
    )
    out = extract_service.summarize_record(
        {
            "person_name": "ПЕТРЕНКО Іван Іванович",
            "person_name_norm": "петренкоіваніванович",
            "paragraphs_json": "[1]",
            "paragraphs_text": '["Наказ № 55"]',
            "generated_rel": "a.docx",
        }
    )
    assert out == "№ 55"


def test_restore_defaults_restores_valid_rules(qapp):
    SettingsDialog = pytest.importorskip("ui.dialogs.settings_dialog", exc_type=ImportError).SettingsDialog
    dialog = SettingsDialog(UserSettings(summary_rules_json="[]"), AppConfig())
    dialog.rules_edit.setPlainText(
        '[{"name":"broken","enabled":true,"pattern":"(?P[bad","flags":"","template":"x"}]'
    )
    dialog.restore_default_summary_rules()
    ok, message = dialog.validate_user_settings()
    assert ok, message
    assert parse_rules(dialog.rules_edit.toPlainText())


def test_restore_defaults_produces_valid_rules(qapp):
    SettingsDialog = pytest.importorskip("ui.dialogs.settings_dialog", exc_type=ImportError).SettingsDialog
    dialog = SettingsDialog(UserSettings(summary_rules_json='[{"name":"broken","enabled":true,"pattern":"(?P[bad","flags":"","template":"x"}]'), AppConfig())
    dialog.restore_default_summary_rules()
    parsed = parse_rules(dialog.rules_edit.toPlainText())
    assert parsed


def test_pattern_with_named_groups_compiles():
    rules = parse_rules(
        '[{"name":"named","enabled":true,"pattern":"(?P<name>\\\\w+)","flags":"","template":"{name}"}]'
    )
    assert rules[0].compile().search("hello").group("name") == "hello"


def test_json_error_and_regex_error_are_reported_separately(qapp):
    SettingsDialog = pytest.importorskip("ui.dialogs.settings_dialog", exc_type=ImportError).SettingsDialog
    dialog = SettingsDialog(UserSettings(), AppConfig())

    dialog.rules_edit.setPlainText("{broken")
    ok_json, message_json = dialog.validate_user_settings()

    dialog.rules_edit.setPlainText(
        '[{"name":"broken","enabled":true,"pattern":"(?P[bad","flags":"","template":"x"}]'
    )
    ok_regex, message_regex = dialog.validate_user_settings()

    assert not ok_json
    assert "Invalid JSON" in (message_json or "")
    assert not ok_regex
    assert "Invalid pattern in rule 'broken'" in (message_regex or "")
    assert "Pattern: (?P[bad" in (message_regex or "")


def test_named_group_pattern_survives_settings_roundtrip(qapp, tmp_path):
    SettingsDialog = pytest.importorskip("ui.dialogs.settings_dialog", exc_type=ImportError).SettingsDialog
    source_json = default_summary_rules_json()
    dialog = SettingsDialog(UserSettings(summary_rules_json=source_json), AppConfig())

    text_from_dialog = dialog.rules_edit.toPlainText()
    assert text_from_dialog == source_json

    built_settings = dialog.build_settings(UserSettings())
    assert built_settings.summary_rules_json == source_json

    manager = SettingsManager(tmp_path)
    manager.save(built_settings)
    loaded_settings = manager.load()
    assert loaded_settings.summary_rules_json == source_json

    parsed = parse_rules(loaded_settings.summary_rules_json)
    assert parsed[0].pattern == (
        r"(?P<surname>[А-ЯІЇЄҐ'’-]+)\s+(?P<first>[А-ЯІЇЄҐ][а-яіїєґ'’-]+)\s+"
        r"(?P<patronymic>[А-ЯІЇЄҐ][а-яіїєґ'’-]+).*(?P<order_num>№\s*\d+)"
    )


def test_default_summary_rules_keep_named_groups():
    default_json = default_summary_rules_json()
    assert "(?P<surname>" in default_json
    assert "(?P<first>" in default_json
    assert "(?P<patronymic>" in default_json
    assert "(?P<order_num>" in default_json


def test_no_angle_bracket_stripping_in_summary_pattern(qapp):
    SettingsDialog = pytest.importorskip("ui.dialogs.settings_dialog", exc_type=ImportError).SettingsDialog
    payload = (
        '[{"name":"named","enabled":true,'
        '"pattern":"(?P<surname>\\\\w+)\\\\s+(?P<first>\\\\w+)\\\\s+(?P<patronymic>\\\\w+).*(?P<order_num>№\\\\s*\\\\d+)",'
        '"flags":"","template":"{surname} {order_num}"}]'
    )
    dialog = SettingsDialog(UserSettings(summary_rules_json=payload), AppConfig())
    rebuilt = dialog.build_settings(UserSettings()).summary_rules_json
    parsed = parse_rules(rebuilt)
    assert parsed[0].pattern == r"(?P<surname>\w+)\s+(?P<first>\w+)\s+(?P<patronymic>\w+).*(?P<order_num>№\s*\d+)"


def test_invalid_pattern_guard_not_triggered_for_valid_named_groups():
    payload = (
        '[{"name":"named","enabled":true,'
        '"pattern":"(?P<surname>\\\\w+)\\\\s+(?P<first>\\\\w+)\\\\s+(?P<patronymic>\\\\w+).*(?P<order_num>№\\\\s*\\\\d+)",'
        '"flags":"IGNORECASE","template":"{surname} {order_num}"}]'
    )
    rules = parse_rules(payload)
    compiled = rules[0].compile()
    match = compiled.search("PETRENKO Ivan Ivanovych ... № 77")
    assert match is not None
    assert match.group("order_num") == "№ 77"
