# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for the restricted Linux systemd service manager."""

import subprocess
import unittest
from unittest.mock import patch

from services.linux.systemd_service_manager import SYSTEMCTL_BIN, SystemdServiceManager


class SystemdServiceManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = SystemdServiceManager()

    @patch("services.linux.systemd_service_manager.subprocess.run")
    def test_running_status_maps_systemd_active_to_running(self, run) -> None:
        run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="active\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="active\nrunning\nenabled\n", stderr=""),
        ]

        status = self.manager.status("openroadcode-navigation")

        self.assertEqual(status.name, "openroadcode-navigation")
        self.assertEqual(status.state, "running")
        self.assertEqual(status.detail, "active / running / enabled")
        self.assertEqual(
            run.call_args_list[0].args[0][:3],
            [SYSTEMCTL_BIN, "is-active", "openroadcode-navigation.service"],
        )

    @patch("services.linux.systemd_service_manager.subprocess.run")
    def test_adsb_api_name_maps_to_existing_readsb_unit(self, run) -> None:
        run.side_effect = [
            subprocess.CompletedProcess([], 3, stdout="inactive\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="inactive\ndead\nenabled\n", stderr=""),
        ]

        status = self.manager.status("openroadcode-adsb")

        self.assertEqual(status.state, "stopped")
        self.assertIn("readsb.service", run.call_args_list[0].args[0])

    @patch("services.linux.systemd_service_manager.subprocess.run")
    def test_mutating_action_uses_noninteractive_sudo(self, run) -> None:
        run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="active\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="active\nrunning\nenabled\n", stderr=""),
        ]

        self.manager.start("openroadcode-navigation")

        self.assertEqual(
            run.call_args_list[0].args[0],
            ["sudo", "-n", SYSTEMCTL_BIN, "start", "openroadcode-navigation.service"],
        )

    @patch("services.linux.systemd_service_manager.subprocess.run")
    def test_start_core_starts_services_in_dependency_order(self, run) -> None:
        def result(command, **kwargs):
            action_index = 3 if command[:2] == ["sudo", "-n"] else 1
            action = command[action_index]
            if action == "is-active":
                return subprocess.CompletedProcess(command, 0, stdout="active\n", stderr="")
            if action == "show":
                return subprocess.CompletedProcess(command, 0, stdout="active\nrunning\nenabled\n", stderr="")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        run.side_effect = result

        statuses = self.manager.start_core()

        starts = [
            entry.args[0]
            for entry in run.call_args_list
            if entry.args[0][:4] == ["sudo", "-n", SYSTEMCTL_BIN, "start"]
        ]
        self.assertEqual(
            starts,
            [
                ["sudo", "-n", SYSTEMCTL_BIN, "start", "openroadcode-message-broker.service"],
                ["sudo", "-n", SYSTEMCTL_BIN, "start", "openroadcode-navigation.service"],
                ["sudo", "-n", SYSTEMCTL_BIN, "start", "openroadcode-automotive.service"],
            ],
        )
        self.assertEqual([status.name for status in statuses], list(self.manager.CORE_STACK))

    def test_rejects_service_outside_whitelist(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported OpenRoadCode service"):
            self.manager.start("ssh")


if __name__ == "__main__":
    unittest.main()
