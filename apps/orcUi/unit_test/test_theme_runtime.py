# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for ORC-specific theme runtime wiring."""

from apps.orcUi.orc_theme import ThemeMode as OrcThemeMode
from apps.orcUi.theme_runtime import create_theme_controller
from ui.theme import ThemeMode


def test_orc_legacy_helpers_use_shared_theme_mode_contract() -> None:
    assert OrcThemeMode is ThemeMode


def test_create_theme_controller_loads_packaged_orc_themes() -> None:
    controller = create_theme_controller()

    assert controller.mode is ThemeMode.DARK
    assert controller.theme.background == "#05090d"

    controller.toggle()

    assert controller.mode is ThemeMode.LIGHT
    assert controller.theme.background == "#e8edf0"


def test_packaged_light_theme_keeps_automotive_instruments_dark() -> None:
    controller = create_theme_controller(ThemeMode.LIGHT)
    sheet = controller.bundle.style_sheet

    gauge = sheet.declarations(".automotive-gauge")
    shifter = sheet.declarations(".automotive-shifter")

    assert gauge["background"] == "#000000"
    assert gauge["color"] == "#ffffff"
    assert gauge["--gauge-face"] == "#080a0c"
    assert gauge["--gauge-tick"] == "#f2f4f5"

    assert shifter["background"] == "#000000"
    assert shifter["color"] == "#ffffff"
    assert shifter["--panel"] == "#111315"
    assert shifter["--gear-active"] == "#ff3143"
