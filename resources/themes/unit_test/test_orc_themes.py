# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract tests for packaged OpenRoadCode theme resources."""

from pathlib import Path

import pytest

from ui.theme import load_theme_bundle

_THEME_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "filename",
    ("orc-dark.css", "orc-light.css"),
)
def test_packaged_theme_contains_required_automotive_rules(
    filename: str,
) -> None:
    bundle = load_theme_bundle(_THEME_ROOT / filename)
    sheet = bundle.style_sheet

    assert sheet.declarations(".automotive-gauge")
    assert sheet.declarations(".automotive-shifter")
    assert sheet.declarations(".automotive-offroad")


@pytest.mark.parametrize(
    "filename",
    ("orc-dark.css", "orc-light.css"),
)
def test_packaged_theme_contains_complete_offroad_palette(
    filename: str,
) -> None:
    bundle = load_theme_bundle(_THEME_ROOT / filename)
    values = bundle.style_sheet.declarations(".automotive-offroad")

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


def test_light_theme_keeps_instruments_dark_but_offroad_light() -> None:
    bundle = load_theme_bundle(_THEME_ROOT / "orc-light.css")
    sheet = bundle.style_sheet

    gauge = sheet.declarations(".automotive-gauge")
    shifter = sheet.declarations(".automotive-shifter")
    offroad = sheet.declarations(".automotive-offroad")

    assert gauge["background"] == "#000000"
    assert gauge["color"] == "#ffffff"

    assert shifter["background"] == "#000000"
    assert shifter["color"] == "#ffffff"

    assert offroad["background"] == bundle.ui.background
    assert offroad["--panel"] == bundle.ui.surface
    assert offroad["color"] == bundle.ui.text
