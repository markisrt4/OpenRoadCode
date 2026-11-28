# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import Mock

from controllers.system import SystemLifecycleAction, SystemLifecycleController


class SystemLifecycleControllerTest(unittest.TestCase):
    def test_restart_is_deferred_until_execute(self) -> None:
        calls: list[tuple[str, list[str]]] = []
        controller = SystemLifecycleController(
            executable="/usr/bin/python3",
            execv=lambda executable, argv: calls.append((executable, argv)),
        )

        controller.request_restart_ui()

        self.assertEqual(controller.requested_action, SystemLifecycleAction.RESTART_UI)
        self.assertEqual(calls, [])
        self.assertTrue(controller.execute_requested_action())
        self.assertEqual(
            calls,
            [("/usr/bin/python3", ["/usr/bin/python3", "-m", "apps.orcUi"])],
        )
        self.assertEqual(controller.requested_action, SystemLifecycleAction.NONE)

    def test_poweroff_prefers_systemctl(self) -> None:
        run = Mock()
        controller = SystemLifecycleController(
            which=lambda command: f"/usr/bin/{command}",
            run=run,
        )

        controller.request_poweroff()

        self.assertTrue(controller.execute_requested_action())
        run.assert_called_once_with(["systemctl", "poweroff"], check=True, timeout=15)

    def test_poweroff_falls_back_to_loginctl(self) -> None:
        run = Mock()
        controller = SystemLifecycleController(
            which=lambda command: None if command == "systemctl" else "/usr/bin/loginctl",
            run=run,
        )

        controller.request_poweroff()

        self.assertTrue(controller.execute_requested_action())
        run.assert_called_once_with(["loginctl", "poweroff"], check=True, timeout=15)

    def test_rejected_poweroff_is_reported(self) -> None:
        command = ["systemctl", "poweroff"]
        controller = SystemLifecycleController(
            which=lambda _command: "/usr/bin/systemctl",
            run=Mock(side_effect=subprocess.CalledProcessError(1, command)),
        )
        controller.request_poweroff()

        with self.assertRaises(subprocess.CalledProcessError):
            controller.execute_requested_action()
        self.assertFalse(controller.execute_requested_action())

    def test_unavailable_poweroff_returns_false(self) -> None:
        controller = SystemLifecycleController(which=lambda _command: None)
        controller.request_poweroff()

        self.assertFalse(controller.execute_requested_action())
        self.assertEqual(controller.requested_action, SystemLifecycleAction.NONE)


if __name__ == "__main__":
    unittest.main()
