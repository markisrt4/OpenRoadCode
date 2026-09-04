# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for theme selection and listener notification."""

import pytest

from controllers.theme import ThemeController
from ui.theme import StyleSheet, ThemeBundle, ThemeMode, UiTheme


def _bundle(background: str) -> ThemeBundle:
    theme = UiTheme(
        background=background,
        surface="#111111",
        surface_alt="#222222",
        border="#333333",
        text="#eeeeee",
        text_muted="#aaaaaa",
        accent_primary="#123456",
        accent_success="#234567",
        accent_warning="#345678",
        accent_danger="#456789",
        control_background="#222222",
        control_active="#123456",
        control_text="#eeeeee",
    )
    return ThemeBundle(ui=theme, style_sheet=StyleSheet({}))


def _controller() -> ThemeController:
    return ThemeController(
        {
            ThemeMode.DARK: _bundle("#000000"),
            ThemeMode.LIGHT: _bundle("#ffffff"),
        }
    )


def test_controller_starts_with_requested_theme() -> None:
    controller = ThemeController(
        {
            ThemeMode.DARK: _bundle("#000000"),
            ThemeMode.LIGHT: _bundle("#ffffff"),
        },
        initial_mode=ThemeMode.LIGHT,
    )

    assert controller.mode is ThemeMode.LIGHT
    assert controller.theme.background == "#ffffff"


def test_toggle_switches_between_dark_and_light() -> None:
    controller = _controller()

    assert controller.toggle() is ThemeMode.LIGHT
    assert controller.theme.background == "#ffffff"
    assert controller.toggle() is ThemeMode.DARK
    assert controller.theme.background == "#000000"


def test_subscriber_receives_initial_and_changed_theme() -> None:
    controller = _controller()
    notifications: list[tuple[ThemeMode, str]] = []

    def listener(mode: ThemeMode, bundle: ThemeBundle) -> None:
        notifications.append((mode, bundle.ui.background))

    controller.subscribe(listener)
    controller.set_mode(ThemeMode.LIGHT)

    assert notifications == [
        (ThemeMode.DARK, "#000000"),
        (ThemeMode.LIGHT, "#ffffff"),
    ]


def test_setting_current_mode_does_not_notify_again() -> None:
    controller = _controller()
    notifications: list[ThemeMode] = []

    controller.subscribe(lambda mode, bundle: notifications.append(mode))
    controller.set_mode(ThemeMode.DARK)

    assert notifications == [ThemeMode.DARK]


def test_missing_initial_theme_is_rejected() -> None:
    with pytest.raises(ValueError, match="No theme configured for mode light"):
        ThemeController(
            {ThemeMode.DARK: _bundle("#000000")},
            initial_mode=ThemeMode.LIGHT,
        )
