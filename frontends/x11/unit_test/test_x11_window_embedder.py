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
    def test_embed_reparents_maps_resizes_and_pins_found_window(
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
                    command, 0, stdout="111\n222\n", stderr=""
                )

            if command == ["xdotool", "getwindowgeometry", "--shell", "111"]:
                return subprocess.CompletedProcess(
                    command, 0, stdout="WIDTH=320\nHEIGHT=200\n", stderr=""
                )

            if command == ["xdotool", "getwindowgeometry", "--shell", "222"]:
                return subprocess.CompletedProcess(
                    command, 0, stdout="WIDTH=800\nHEIGHT=600\n", stderr=""
                )

            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        run.side_effect = fake_run
        embedder = X11WindowEmbedder(timeout_seconds=0.1)

        window_id = embedder.embed(1234, 5678, 800, 400)

        self.assertEqual(222, window_id)
        self.assertEqual(222, embedder.window_id)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(["xdotool", "search", "--pid", "1234"], commands[0])
        self.assertIn(["xdotool", "getwindowgeometry", "--shell", "111"], commands)
        self.assertIn(["xdotool", "getwindowgeometry", "--shell", "222"], commands)
        self.assertIn(["xdotool", "windowreparent", "222", "5678"], commands)
        self.assertIn(["xdotool", "windowmap", "222"], commands)
        self.assertIn(["xdotool", "windowsize", "222", "800", "400"], commands)
        self.assertIn(["xdotool", "windowmove", "222", "0", "0"], commands)

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    @patch("frontends.x11.x11_window_embedder.shutil.which", return_value="/usr/bin/xdotool")
    def test_hide_unmaps_matching_window_without_claiming_it(
        self, _which: Mock, run: Mock
    ) -> None:
        def fake_run(command, **_kwargs):
            if command[:3] == ["xdotool", "search", "--pid"]:
                return subprocess.CompletedProcess(command, 0, stdout="222\n", stderr="")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        run.side_effect = fake_run
        embedder = X11WindowEmbedder(timeout_seconds=0.1)

        window_id = embedder.hide(1234, window_name="SDR++")

        self.assertEqual(222, window_id)
        self.assertIsNone(embedder.window_id)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(["xdotool", "windowunmap", "222"], commands)

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
    def test_resize_moves_embedded_client_to_host_origin(self, run: Mock) -> None:
        embedder = X11WindowEmbedder()
        embedder._window_id = 99
        embedder._host_window_id = 123

        embedder.resize(640, 480)

        self.assertEqual(
            ["xdotool", "windowsize", "99", "640", "480"],
            run.call_args_list[0].args[0],
        )
        self.assertEqual(
            ["xdotool", "windowmove", "99", "0", "0"],
            run.call_args_list[1].args[0],
        )

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    @patch("frontends.x11.x11_window_embedder.shutil.which")
    def test_resize_relaxes_normal_hints_before_sizing(self, which: Mock, run: Mock) -> None:
        def fake_which(name: str):
            return "/usr/bin/xprop" if name == "xprop" else "/usr/bin/xdotool"

        which.side_effect = fake_which
        embedder = X11WindowEmbedder()
        embedder._window_id = 99
        embedder._host_window_id = 123
        embedder._relax_size_hints = True

        embedder.resize(640, 480)

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(
            ["/usr/bin/xprop", "-id", "99", "-remove", "WM_NORMAL_HINTS"],
            commands[0],
        )
        self.assertEqual(["xdotool", "windowsize", "99", "640", "480"], commands[1])
        self.assertEqual(["xdotool", "windowmove", "99", "0", "0"], commands[2])

    @patch("frontends.x11.x11_window_embedder.subprocess.run")
    def test_clear_forgets_embedded_window(self, run: Mock) -> None:
        embedder = X11WindowEmbedder()
        embedder._window_id = 99
        embedder._relax_size_hints = True

        embedder.clear()
        embedder.resize(640, 480)

        self.assertIsNone(embedder.window_id)
        self.assertFalse(embedder._relax_size_hints)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
