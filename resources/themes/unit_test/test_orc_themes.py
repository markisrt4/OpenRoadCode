# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract tests for packaged OpenRoadCode theme resources."""

from pathlib import Path

import pytest

from ui.theme import load_theme_bundle

_THEME_ROOT = Path(__file__).resolve().parents[1]
_THEME_FILES = ("orc-dark.css", "orc-light.css")


@pytest.mark.parametrize("filename", _THEME_FILES)
def test_packaged_theme_loads_semantic_ui_contract(filename: str) -> None:
    bundle = load_theme_bundle(_THEME_ROOT / filename)

    assert bundle.ui.background
    assert bundle.ui.surface
    assert bundle.ui.text
    assert bundle.ui.control_background
    assert bundle.ui.control_active
    assert bundle.ui.control_text


@pytest.mark.parametrize("filename", _THEME_FILES)
def test_packaged_theme_contains_required_automotive_rules(filename: str) -> None:
    sheet = load_theme_bundle(_THEME_ROOT / filename).style_sheet

    assert sheet.declarations(".automotive-gauge")
    assert sheet.declarations(".automotive-shifter")
    assert sheet.declarations(".automotive-offroad")


@pytest.mark.parametrize("filename", _THEME_FILES)
def test_packaged_theme_contains_complete_offroad_palette(filename: str) -> None:
    values = load_theme_bundle(_THEME_ROOT / filename).style_sheet.declarations(
        ".automotive-offroad"
    )

    required = {
        "background",
        "color",
        "--panel",
        "--border",
        "--muted",
        "--heading",
        "--success",
        "--warning",
        "--danger",
        "--sky",
        "--ground",
        "--control-background",
        "--control-active",
        "--control-text",
    }

    assert required <= values.keys()


@pytest.mark.parametrize("filename", _THEME_FILES)
def test_automotive_gauge_defines_linear_card_palette(filename: str) -> None:
    values = load_theme_bundle(_THEME_ROOT / filename).style_sheet.declarations(
        ".automotive-gauge"
    )

    required = {
        "--linear-card-background",
        "--linear-card-inner",
        "--linear-card-border",
        "--linear-card-highlight",
        "--linear-card-text",
        "--linear-card-muted",
    }

    assert required <= values.keys()


def test_light_theme_keeps_instruments_dark_but_offroad_light() -> None:
    bundle = load_theme_bundle(_THEME_ROOT / "orc-light.css")
    sheet = bundle.style_sheet

    gauge = sheet.declarations(".automotive-gauge")
    shifter = sheet.declarations(".automotive-shifter")
    offroad = sheet.declarations(".automotive-offroad")

    assert gauge["background"] == bundle.ui.background
    assert gauge["color"] == "#ffffff"
    assert gauge["--gauge-face"] == "#080a0c"
    assert gauge["--gauge-tick"] == "#f2f4f5"

    assert shifter["background"] == "#000000"
    assert shifter["color"] == "#ffffff"
    assert shifter["--panel"] == "#111315"
    assert shifter["--gear-active"] == "#ff3143"

    assert offroad["background"] == bundle.ui.background
    assert offroad["--panel"] == bundle.ui.surface
    assert offroad["color"] == bundle.ui.text
