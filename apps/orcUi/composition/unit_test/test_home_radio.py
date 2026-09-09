# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Regression coverage for feature-owned Home radio presentation."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from apps.orcUi.composition.radio import configure_radio
from apps.orcUi.home_shell import ComposedHomeShell
from ui.theme import ThemeMode


class HomeRadioCompositionTest(unittest.TestCase):
    @patch("apps.orcUi.composition.radio.StreamingRadioNowPlaying")
    @patch("apps.orcUi.composition.radio.RadioScreen")
    @patch("apps.orcUi.composition.radio.StreamingRadioFavorites")
    @patch("apps.orcUi.composition.radio.RadioBrowserDirectory")
    def test_home_factory_uses_runtime_and_retained_screen(self, directory_type, favorites_type, screen_type, now_playing_type):
        app = Mock()
        app.theme_mode = ThemeMode.DARK
        runtime = Mock()
        composition = configure_radio(app, runtime)
        self.assertIs(composition.screen, screen_type.return_value)
        self.assertIs(composition.directory, directory_type.return_value)
        self.assertIs(composition.favorites, favorites_type.return_value)
        app.register_screen.assert_called_once_with("RADIO", composition.screen)
        factory = app.set_home_radio_factory.call_args.args[0]
        parent = Mock()
        widget = factory(parent)
        self.assertIs(widget, now_playing_type.return_value)
        kwargs = now_playing_type.call_args.kwargs
        self.assertIs(kwargs["controller"], runtime.streaming_radio)
        kwargs["on_open_rf"]()
        app.navigate_to.assert_called_with("RADIO")
        composition.screen.open_rf.assert_called_once_with()
        kwargs["on_open_streaming"]()
        composition.screen.open_streaming.assert_called_once_with()
        self.assertEqual(app.navigate_to.call_count, 2)

    def test_home_slot_rebuilds_only_when_home_is_active(self):
        app = ComposedHomeShell.__new__(ComposedHomeShell)
        app._active_nav = "RADIO"
        app._show_home = Mock()
        factory = Mock()
        app.set_home_radio_factory(factory)
        self.assertIs(app._home_radio_factory, factory)
        app._show_home.assert_not_called()
        app._active_nav = "HOME"
        app.set_home_radio_factory(factory)
        app._show_home.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
