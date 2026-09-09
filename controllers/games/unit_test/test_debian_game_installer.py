# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Debian game launch behavior across native and Termux/proot hosts."""

import unittest
from unittest.mock import Mock, patch

from controllers.games.debian_game_installer import DebianGameInstaller
from controllers.games.game_types import GameDefinition, TermuxProotRuntimeConfig


class DebianGameInstallerRuntimeTest(unittest.TestCase):
    def _game(self) -> GameDefinition:
        return GameDefinition(
            name="Nibbles",
            command=("gnome-nibbles",),
            environment={"GENERIC_SETTING": "1"},
            termux_proot=TermuxProotRuntimeConfig(
                environment={"GSK_RENDERER": "cairo"},
                rendering="software",
                window_name="Nibbles",
                window_class="org.gnome.Nibbles",
                relax_size_hints=True,
            ),
            debian_package="gnome-nibbles",
        )

    @patch("controllers.games.debian_game_installer.DebianCommandRunner")
    def test_proot_applies_only_proot_runtime_compatibility(self, runner_type: Mock) -> None:
        runner = runner_type.return_value
        runner.is_proot = True
        runner.graphical_command.return_value = ["wrapped"]
        installer = DebianGameInstaller()

        command = installer.launch_command(self._game())

        self.assertEqual(["wrapped"], command)
        args = runner.graphical_command.call_args.args[0]
        self.assertIn("GENERIC_SETTING=1", args)
        self.assertIn("GSK_RENDERER=cairo", args)
        self.assertEqual("software", runner.graphical_command.call_args.kwargs["rendering"])
        self.assertEqual(
            ("Nibbles", "org.gnome.Nibbles"),
            installer.window_selectors(self._game()),
        )
        self.assertTrue(installer.relax_window_size_hints(self._game()))

    @patch("controllers.games.debian_game_installer.DebianCommandRunner")
    def test_native_debian_ignores_termux_proot_runtime_compatibility(self, runner_type: Mock) -> None:
        runner = runner_type.return_value
        runner.is_proot = False
        runner.graphical_command.return_value = ["native"]
        installer = DebianGameInstaller()

        command = installer.launch_command(self._game())

        self.assertEqual(["native"], command)
        args = runner.graphical_command.call_args.args[0]
        self.assertIn("GENERIC_SETTING=1", args)
        self.assertNotIn("GSK_RENDERER=cairo", args)
        self.assertEqual("auto", runner.graphical_command.call_args.kwargs["rendering"])
        self.assertEqual((None, None), installer.window_selectors(self._game()))
        self.assertFalse(installer.relax_window_size_hints(self._game()))


if __name__ == "__main__":
    unittest.main()
