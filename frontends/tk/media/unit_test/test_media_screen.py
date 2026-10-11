# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Media hub regression checks without an X display."""

import unittest
from unittest.mock import Mock, patch

from frontends.tk.media.media_screen import MediaScreen


class MediaScreenTest(unittest.TestCase):
    def test_provider_glow_preserves_identity_and_fades_to_theme(self):
        screen = object.__new__(MediaScreen)
        canvas = Mock()
        canvas.cget.return_value = "#101010"
        canvas.winfo_rgb.side_effect = lambda color: tuple(
            int(color[i:i + 2], 16) * 257 for i in (1, 3, 5)
        )
        screen._paint_provider_glow(canvas, 320, 54, "#ed4768")
        canvas.delete.assert_called_once_with("glow")
        self.assertEqual(canvas.create_rectangle.call_count, 32)
        self.assertEqual(canvas.create_rectangle.call_args.kwargs["fill"], "#101010")
        canvas.tag_raise.assert_called_once_with("identity")

    def test_visualizer_uses_existing_action_without_online_gate(self):
        screen = object.__new__(MediaScreen)
        screen._theme_bundle = Mock()
        screen._online_allowed = lambda: False
        screen._show_visualizer = Mock()
        with patch("frontends.tk.media.media_screen.tk.Frame"), patch(
            "frontends.tk.media.media_screen.tk.Canvas"
        ), patch(
            "frontends.tk.media.media_screen.tk.Button"
        ) as button:
            screen._visualizer_card(Mock())
            button.call_args.kwargs["command"]()
        screen._show_visualizer.assert_called_once_with()

    def test_spectrum_replaces_previous_drawing_and_fits_allocation(self):
        screen = object.__new__(MediaScreen)
        canvas = Mock()
        canvas.winfo_rgb.return_value = (4096, 4096, 4096)
        screen._paint_visualizer(canvas, 240, 60)
        canvas.delete.assert_called_once_with("all")
        self.assertEqual(canvas.create_rectangle.call_count, 72)
        for call in canvas.create_rectangle.call_args_list:
            x1, y1, x2, y2 = call.args
            self.assertGreaterEqual(x1, 0)
            self.assertGreaterEqual(y1, 0)
            self.assertLessEqual(x2, 241)
            self.assertLessEqual(y2, 60)

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
