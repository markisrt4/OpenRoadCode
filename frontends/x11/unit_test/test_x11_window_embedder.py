# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the shared X11 window embedding frontend."""

import subprocess
import unittest
from unittest.mock import Mock, patch

from frontends.x11.x11_window_embedder import X11WindowEmbedder


class X11WindowEmbedderTest(unittest.TestCase):
    @patch("frontends.x11.x11_window_embedder.shutil.which")
    def test_supported_requires_xdotool(self, which: Mock) -> None:
        which.return_value = "/usr/bin/xdotool"
        self.assertTrue(X11WindowEmbedder.supported())
        which.assert_called_once_with("xdotool")

    @patch("frontends.x11.x11_window_embedder.shutil.which", return_value=None)
    def test_embed_fails_when_xdotool_is_missing(self, _which: Mock) -> None:
        embedder = X11WindowEmbedder(timeout_seconds=0.01)
        with self.assertRaisesRegex(RuntimeError, "xdotool is required"):
            embedder.embed(1234, 5678, 800, 400)

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    @patch("frontends.x11.x11_window_embedder.shutil.which", return_value="/usr/bin/xdotool")
    def test_embed_reparents_and_resizes_found_window(
        self, _which: Mock, run: Mock
    ) -> None:
        run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="111\n222\n", stderr=""),
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 0),
        ]
        embedder = X11WindowEmbedder(timeout_seconds=0.1)

        window_id = embedder.embed(1234, 5678, 800, 400)

        self.assertEqual(222, window_id)
        self.assertEqual(222, embedder.window_id)
        self.assertEqual(
            ["xdotool", "search", "--onlyvisible", "--pid", "1234"],
            run.call_args_list[0].args[0],
        )
        self.assertEqual(
            ["xdotool", "windowreparent", "222", "5678"],
            run.call_args_list[1].args[0],
        )
        self.assertEqual(
            ["xdotool", "windowsize", "222", "800", "400"],
            run.call_args_list[2].args[0],
        )
        self.assertEqual(
            ["xdotool", "windowmove", "222", "0", "0"],
            run.call_args_list[3].args[0],
        )

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    def test_resize_clamps_dimensions_to_one(self, run: Mock) -> None:
        embedder = X11WindowEmbedder()
        embedder._window_id = 99

        embedder.resize(0, -5)

        self.assertEqual(
            ["xdotool", "windowsize", "99", "1", "1"],
            run.call_args_list[0].args[0],
        )
        self.assertEqual(
            ["xdotool", "windowmove", "99", "0", "0"],
            run.call_args_list[1].args[0],
        )

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    def test_clear_forgets_embedded_window(self, run: Mock) -> None:
        embedder = X11WindowEmbedder()
        embedder._window_id = 99

        embedder.clear()
        embedder.resize(640, 480)

        self.assertIsNone(embedder.window_id)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
