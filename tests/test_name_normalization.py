from domain.name_normalization import (
    build_filter_keys,
    detect_person_names,
    detect_uppercase_candidates,
    normalize_person_key,
)


def test_normalize_person_key():
    assert normalize_person_key("ПЕТРЕНКО Іван Іванович") == "петренко іван іванович"


def test_build_filter_keys():
    keys = build_filter_keys("Петренко Іван Іванович")
    assert "петренко іван іванович" in keys
    assert "петренко" in keys


def test_search_normalization_apostrophes_confusables():
    assert normalize_person_key("ПEТРЕНКО Іван Іванович") == normalize_person_key("ПЕТРЕНКО Іван Іванович")
    assert normalize_person_key("О’Браєн Іван Іванович") == normalize_person_key("О'Браєн Іван Іванович")


def test_name_regex_detection():
    names = detect_person_names("Наказ: ПЕТРЕНКО Іван Іванович")
    assert names


def test_uppercase_candidate_detection():
    lines = ["КОМАНДУВАННЯ СУХОПУТНИХ ВІЙСЬК", "звичайний рядок"]
    hints = detect_uppercase_candidates(lines)
    assert hints and "КОМАНДУВАННЯ" in hints[0]
