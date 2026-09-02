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


def test_packaged_light_theme_contains_automotive_shifter_style() -> None:
    controller = create_theme_controller(ThemeMode.LIGHT)
    shifter = controller.bundle.style_sheet.declarations(".automotive-shifter")

    assert shifter["background"] == "#e8edf0"
    assert shifter["--panel"] == "#f6f8f9"
    assert shifter["--gear-active"] == "#d51f2b"
