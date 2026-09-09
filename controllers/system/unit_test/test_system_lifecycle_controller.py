# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

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
        commands: list[list[str]] = []
        controller = SystemLifecycleController(
            which=lambda command: f"/usr/bin/{command}",
            popen=lambda command: commands.append(command),
        )

        controller.request_poweroff()

        self.assertTrue(controller.execute_requested_action())
        self.assertEqual(commands, [["systemctl", "poweroff"]])

    def test_poweroff_falls_back_to_loginctl(self) -> None:
        commands: list[list[str]] = []
        controller = SystemLifecycleController(
            which=lambda command: None if command == "systemctl" else "/usr/bin/loginctl",
            popen=lambda command: commands.append(command),
        )

        controller.request_poweroff()

        self.assertTrue(controller.execute_requested_action())
        self.assertEqual(commands, [["loginctl", "poweroff"]])

    def test_unavailable_poweroff_returns_false(self) -> None:
        controller = SystemLifecycleController(which=lambda _command: None)
        controller.request_poweroff()

        self.assertFalse(controller.execute_requested_action())
        self.assertEqual(controller.requested_action, SystemLifecycleAction.NONE)


if __name__ == "__main__":
    unittest.main()
