# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Media hub regression checks without an X display."""

import unittest
from unittest.mock import Mock, patch

from frontends.tk.media.media_screen import MediaScreen


class MediaScreenTest(unittest.TestCase):
    def test_visualizer_uses_existing_action_without_online_gate(self):
        screen = object.__new__(MediaScreen)
        screen._theme_bundle = Mock()
        screen._online_allowed = lambda: False
        screen._show_visualizer = Mock()
        with patch("frontends.tk.media.media_screen.tk.Frame"), patch(
            "frontends.tk.media.media_screen.tk.Button"
        ) as button:
            screen._visualizer_card(Mock())
            button.call_args.kwargs["command"]()
        screen._show_visualizer.assert_called_once_with()

    def test_spotify_secondary_actions_use_body_and_share_row(self):
        screen = object.__new__(MediaScreen)
        screen._theme_bundle = Mock()
        body = Mock()
        body.winfo_manager.return_value = "pack"
        body.children = {}
        accent = Mock()
        accent.winfo_manager.return_value = "place"
        card = Mock()
        card.winfo_children.return_value = [accent, body]
        row = Mock()

        def create(parent, **kwargs):
            self.assertIs(parent, body)
            parent.children[kwargs["name"]] = row
            return row

        with patch("frontends.tk.media.media_screen.tk.Frame", side_effect=create) as frame:
            self.assertIs(screen._spotify_settings_row(card), row)
            self.assertIs(screen._spotify_settings_row(card), row)
            frame.assert_called_once()
        row.pack.assert_called_once()

    def test_offline_provider_shortcut_does_not_launch(self):
        screen = object.__new__(MediaScreen)
        screen._online_allowed = lambda: False
        screen._host = Mock()
        launch = Mock()
        screen._online_action(launch)()
        launch.assert_not_called()
        screen._host.set_screen_status.assert_called_once_with(
            "Offline mode: online media unavailable"
        )

    def test_online_provider_shortcut_preserves_action(self):
        screen = object.__new__(MediaScreen)
        screen._online_allowed = lambda: True
        screen._host = Mock()
        launch = Mock()
        screen._online_action(launch)()
        launch.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
