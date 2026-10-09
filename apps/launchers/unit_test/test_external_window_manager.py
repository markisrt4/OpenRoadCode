# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for external X11 window presentation behavior."""

import unittest
from unittest.mock import Mock, patch

from apps.launchers.external_window_manager import ExternalWindowManager


class ExternalWindowManagerTest(unittest.TestCase):
    def test_rejects_nonpositive_timeout(self) -> None:
        with self.assertRaises(ValueError):
            ExternalWindowManager(window_timeout_seconds=0.0)

    @patch("apps.launchers.external_window_manager.shutil.which", return_value="/usr/bin/tool")
    def test_activate_raises_matching_window(self, _which: Mock) -> None:
        manager = ExternalWindowManager()
        with (
            patch.object(manager, "wait_for_window_id", return_value="0x123"),
            patch.object(manager, "_run") as run,
        ):
            window_id = manager.activate(display=":0", window_class="OpenRoadCodeWeather")

        self.assertEqual(window_id, "0x123")
        self.assertEqual(run.call_args.args[0], ["wmctrl", "-ia", "0x123"])

    @patch("apps.launchers.external_window_manager.shutil.which", return_value="/usr/bin/tool")
    def test_close_requests_normal_window_close(self, _which: Mock) -> None:
        manager = ExternalWindowManager()
        with patch.object(manager, "_run") as run:
            closed = manager.close(display=":2", window_id="0x456")

        self.assertTrue(closed)
        self.assertEqual(run.call_args.args[0], ["wmctrl", "-ic", "0x456"])

    @patch("apps.launchers.external_window_manager.shutil.which", return_value="/usr/bin/tool")
    @patch("apps.launchers.external_window_manager.time.sleep")
    def test_fit_removes_window_states_and_applies_geometry(self, _sleep: Mock, _which: Mock) -> None:
        manager = ExternalWindowManager()
        with (
            patch.object(manager, "wait_for_window_id", return_value="0x789"),
            patch.object(manager, "_run") as run,
        ):
            window_id = manager.fit(
                display=":0",
                window_class="OpenRoadCodeADSB",
                position=(10, 20),
                size=(800, 480),
            )

        self.assertEqual(window_id, "0x789")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[-1], ["wmctrl", "-ir", "0x789", "-e", "0,10,20,800,480"])
        self.assertTrue(any("remove,fullscreen" in command for command in commands))
        self.assertTrue(any(command[0] == "xprop" for command in commands))

    @patch("apps.launchers.external_window_manager.shutil.which", return_value="/usr/bin/tool")
    def test_wait_for_window_id_falls_back_to_root_client_list(self, _which: Mock) -> None:
        manager = ExternalWindowManager()
        responses = [
            Mock(stdout="0x00100001 0 xfce4-terminal.Xfce4-terminal host Terminal\n"),
            Mock(stdout="_NET_CLIENT_LIST(WINDOW): window id # 0x100001, 0x200004\n"),
            Mock(stdout='WM_CLASS(STRING) = "xfce4-terminal", "Xfce4-terminal"\n'),
            Mock(stdout='WM_CLASS(STRING) = "earth.google.com__web_search", "openroadcode-google-earth"\n'),
        ]

        with patch("apps.launchers.external_window_manager.subprocess.run", side_effect=responses):
            window_id = manager.wait_for_window_id(
                display=":1",
                window_class="openroadcode-google-earth",
            )

        self.assertEqual(window_id, "0x200004")


if __name__ == "__main__":
    unittest.main()
