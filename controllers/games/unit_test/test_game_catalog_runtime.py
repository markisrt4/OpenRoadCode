# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for platform-specific game runtime configuration loading."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers.games.game_catalog import load_game_catalog
from controllers.games.debian_command_runner import DebianCommandRunner
from controllers.games.debian_game_installer import DebianGameInstaller


class GameCatalogRuntimeTest(unittest.TestCase):
    def test_gnome_catalog_games_launch_through_proot_opengl_bridge(self) -> None:
        catalog_path = Path(__file__).resolve().parents[3] / "config" / "games.toml"
        with patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}, clear=True):
            games = {game.name: game for game in load_game_catalog(catalog_path)}
        runner = DebianCommandRunner.__new__(DebianCommandRunner)
        runner._mode = "proot"
        with patch("controllers.games.debian_game_installer.DebianCommandRunner", return_value=runner):
            installer = DebianGameInstaller()
        for name in ("GNOME 2048", "GNOME Nibbles", "GNOME Sudoku"):
            with self.subTest(game=name):
                game = games[name]
                self.assertTrue(game.enabled)
                with patch.object(runner, "_ensure_virgl_server", return_value=True) as bridge:
                    command = installer.launch_command(game)
                bridge.assert_called_once_with()
                self.assertIn("--shared-tmp", command)
                self.assertIn("GALLIUM_DRIVER=virpipe", command)
                self.assertIn("GSK_RENDERER=gl", command)
                self.assertNotIn("GSK_RENDERER=cairo", command)
                self.assertNotIn("GALLIUM_DRIVER=llvmpipe", command)
                self.assertIsNotNone(installer.window_selectors(game)[0])

    def test_termux_proot_runtime_settings_are_nested(self) -> None:
        config = """
[[games]]
name = "Nibbles"
command = ["gnome-nibbles"]
environment = { GENERIC = "yes" }
[games.termux_proot]
rendering = "software"
environment = { GSK_RENDERER = "cairo" }
window_name = "Nibbles"
window_class = "org.gnome.Nibbles"
relax_size_hints = true
[games.install]
debian_package = "gnome-nibbles"
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "games.toml"
            path.write_text(config, encoding="utf-8")
            game = load_game_catalog(path)[0]

        self.assertEqual({"GENERIC": "yes"}, game.environment)
        self.assertEqual("software", game.termux_proot.rendering)
        self.assertEqual({"GSK_RENDERER": "cairo"}, game.termux_proot.environment)
        self.assertEqual("Nibbles", game.termux_proot.window_name)
        self.assertEqual("org.gnome.Nibbles", game.termux_proot.window_class)
        self.assertTrue(game.termux_proot.relax_size_hints)

    def test_termux_only_disable_marks_game_disabled_on_termux(self) -> None:
        config = """
[[games]]
name = "Nibbles"
command = ["gnome-nibbles"]
[games.termux_proot]
enabled = false
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "games.toml"
            path.write_text(config, encoding="utf-8")
            with patch.dict(
                os.environ,
                {"PREFIX": "/data/data/com.termux/files/usr"},
                clear=True,
            ):
                game = load_game_catalog(path)[0]

        self.assertFalse(game.enabled)
        self.assertFalse(game.termux_proot.enabled)

    def test_termux_only_disable_does_not_disable_native_debian(self) -> None:
        config = """
[[games]]
name = "Nibbles"
command = ["gnome-nibbles"]
[games.termux_proot]
enabled = false
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "games.toml"
            path.write_text(config, encoding="utf-8")
            with patch.dict(os.environ, {"PREFIX": "/usr"}, clear=True):
                game = load_game_catalog(path)[0]

        self.assertTrue(game.enabled)
        self.assertFalse(game.termux_proot.enabled)

    def test_invalid_termux_rendering_policy_is_rejected(self) -> None:
        config = """
[[games]]
name = "Bad"
command = ["bad"]
[games.termux_proot]
rendering = "galaxy-magic"
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "games.toml"
            path.write_text(config, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported Termux/proot rendering policy"):
                load_game_catalog(path)


if __name__ == "__main__":
    unittest.main()
