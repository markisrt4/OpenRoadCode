# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component tests for vehicle-gauge stylesheet resolution."""

from pathlib import Path

import pytest

from frontends.tk.automotive.vehicle_gauge_theme import vehicle_gauge_theme_from_style_sheet
from frontends.tk.automotive.vehicle_gauge_widgets import LinearGauge
from ui.theme import load_theme_bundle


_THEME_ROOT = Path(__file__).resolve().parents[4] / "resources" / "themes"


@pytest.mark.parametrize("filename", ("orc-dark.css", "orc-light.css"))
def test_vehicle_gauge_theme_resolves_packaged_css(filename: str) -> None:
    bundle = load_theme_bundle(_THEME_ROOT / filename)
    values = bundle.style_sheet.declarations(".automotive-gauge")
    theme = vehicle_gauge_theme_from_style_sheet(bundle.style_sheet)

    assert theme.background_color == values["background"]
    assert theme.face_color == values["--gauge-face"]
    assert theme.bezel_mid == values["--gauge-bezel"]
    assert theme.foreground_color == values["--gauge-tick"]
    assert theme.needle_body == values["--gauge-needle"]
    assert theme.linear_card_background == values["--linear-card-background"]
    assert theme.linear_card_inner == values["--linear-card-inner"]
    assert theme.linear_card_border == values["--linear-card-border"]
    assert theme.linear_card_highlight == values["--linear-card-highlight"]
    assert theme.linear_card_text == values["--linear-card-text"]
    assert theme.linear_card_muted == values["--linear-card-muted"]


def _linear_gauge(theme):
    gauge = LinearGauge.__new__(LinearGauge)
    gauge._style = theme
    gauge._connected = True
    gauge._value = 50.0
    gauge._danger_low = None
    gauge._danger_high = None
    gauge._caution_low = None
    gauge._caution_high = None
    return gauge


def test_light_linear_gauge_uses_card_text_for_normal_value() -> None:
    bundle = load_theme_bundle(_THEME_ROOT / "orc-light.css")
    theme = vehicle_gauge_theme_from_style_sheet(bundle.style_sheet)
    gauge = _linear_gauge(theme)

    assert gauge._display_value_color() == theme.linear_card_text
    assert gauge._display_value_color() == bundle.ui.text


def test_linear_gauge_uses_muted_card_text_when_disconnected() -> None:
    bundle = load_theme_bundle(_THEME_ROOT / "orc-light.css")
    theme = vehicle_gauge_theme_from_style_sheet(bundle.style_sheet)
    gauge = _linear_gauge(theme)
    gauge._connected = False

    assert gauge._display_value_color() == theme.linear_card_muted


def test_linear_gauge_preserves_warning_colors() -> None:
    bundle = load_theme_bundle(_THEME_ROOT / "orc-light.css")
    theme = vehicle_gauge_theme_from_style_sheet(bundle.style_sheet)
    gauge = _linear_gauge(theme)

    gauge._caution_high = 40.0
    assert gauge._display_value_color() == theme.caution_value

    gauge._danger_high = 45.0
    assert gauge._display_value_color() == theme.danger_value
