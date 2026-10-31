"""Shared FM identity mapping tests."""
from ui.radio.station_identity import station_label, preset_label


def test_known_call_sign_has_frequency() -> None:
    assert station_label("WRIF") == "WRIF · 101.1 FM"
    assert preset_label("101.1 FM", 101_100_000) == "WRIF · 101.1 FM"


def test_unknown_station_keeps_original_label() -> None:
    assert station_label("UNKNOWN") == "UNKNOWN"
    assert preset_label("88.1 FM", 88_100_000) == "88.1 FM"


def test_call_sign_lookup_is_case_insensitive() -> None:
    assert station_label("wcsx") == "WCSX · 94.7 FM"
