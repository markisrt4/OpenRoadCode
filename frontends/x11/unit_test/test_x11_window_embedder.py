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
    def test_embed_reparents_maps_and_resizes_found_window(
        self, _which: Mock, run: Mock
    ) -> None:
        def fake_run(command, **_kwargs):
            if (
                len(command) >= 4
                and command[0] == "xdotool"
                and command[1] == "search"
                and "--pid" in command
                and "1234" in command
            ):
                return subprocess.CompletedProcess(
                    command, 0, stdout="111\\n222\\n", stderr=""
                )

            if command == ["xdotool", "getwindowgeometry", "--shell", "111"]:
                return subprocess.CompletedProcess(
                    command, 0, stdout="WIDTH=320\\nHEIGHT=200\\n", stderr=""
                )

            if command == ["xdotool", "getwindowgeometry", "--shell", "222"]:
                return subprocess.CompletedProcess(
                    command, 0, stdout="WIDTH=800\\nHEIGHT=600\\n", stderr=""
                )

            if command == ["xwininfo", "-id", "222", "-tree"]:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout="Parent window id: 0x162e",
                    stderr="",
                )

            return subprocess.CompletedProcess(
                command, 0, stdout="", stderr=""
            )

        run.side_effect = fake_run
        embedder = X11WindowEmbedder(timeout_seconds=0.1)

        window_id = embedder.embed(1234, 5678, 800, 400)

        self.assertEqual(222, window_id)
        self.assertEqual(222, embedder.window_id)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(
            ["xdotool", "search", "--pid", "1234"],
            commands[0],
        )
        self.assertIn(["xdotool", "getwindowgeometry", "--shell", "111"], commands)
        self.assertIn(["xdotool", "getwindowgeometry", "--shell", "222"], commands)
        self.assertIn(["xdotool", "windowreparent", "222", "5678"], commands)
        self.assertIn(["xdotool", "windowmap", "222"], commands)
        self.assertIn(["xdotool", "windowsize", "222", "800", "400"], commands)
        self.assertIn(["xdotool", "windowmove", "222", "0", "0"], commands)

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    def test_best_window_id_falls_back_to_last_when_geometry_is_empty(self, run: Mock) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout=None, stderr=None)
        result = subprocess.CompletedProcess([], 0, stdout="111\n222\n", stderr="")

        self.assertEqual(222, X11WindowEmbedder._best_window_id(result))

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    def test_detach_reparents_unmaps_and_forgets_window(self, run: Mock) -> None:
        embedder = X11WindowEmbedder()
        embedder._window_id = 99

        embedder.detach(123)

        self.assertEqual(
            ["xdotool", "windowreparent", "99", "123"],
            run.call_args_list[0].args[0],
        )
        self.assertEqual(
            ["xdotool", "windowunmap", "99"],
            run.call_args_list[1].args[0],
        )
        self.assertIsNone(embedder.window_id)

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    def test_resize_clamps_dimensions_to_one(self, run: Mock) -> None:
        embedder = X11WindowEmbedder()
        embedder._window_id = 99

        embedder.resize(0, -5)

        self.assertEqual(
            ["xdotool", "windowsize", "99", "1", "1"],
            run.call_args_list[0].args[0],
        )
        self.assertEqual(1, run.call_count)

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
