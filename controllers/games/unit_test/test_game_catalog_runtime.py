# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for platform-specific game runtime configuration loading."""

import tempfile
import unittest
from pathlib import Path

from controllers.games.game_catalog import load_game_catalog


class GameCatalogRuntimeTest(unittest.TestCase):
    def test_termux_proot_runtime_settings_are_nested(self) -> None:
        config = """
[[games]]
name = "Nibbles"
command = ["gnome-nibbles"]
environment = { GENERIC = "yes" }
[games.termux_proot]
hardware_acceleration = false
environment = { GSK_RENDERER = "cairo" }
window_name = "Nibbles"
window_class = "org.gnome.Nibbles"
[games.install]
debian_package = "gnome-nibbles"
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "games.toml"
            path.write_text(config, encoding="utf-8")
            game = load_game_catalog(path)[0]

        self.assertEqual({"GENERIC": "yes"}, game.environment)
        self.assertFalse(game.termux_proot.hardware_acceleration)
        self.assertEqual({"GSK_RENDERER": "cairo"}, game.termux_proot.environment)
        self.assertEqual("Nibbles", game.termux_proot.window_name)
        self.assertEqual("org.gnome.Nibbles", game.termux_proot.window_class)


if __name__ == "__main__":
    unittest.main()
