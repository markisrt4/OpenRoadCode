# SPDX-License-Identifier: MIT
"""SDRForge user-systemd routing must remain strictly allowlisted."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from services.linux.systemd_service_manager import SystemdServiceManager


class SdrforgeSystemdTests(unittest.TestCase):
    def test_user_service_routes_through_fixed_helper(self) -> None:
        with patch("services.linux.systemd_service_manager.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "active\n", "")
            SystemdServiceManager._systemctl("is-active", "libsdrforge.service", check=False)
            command = run.call_args.args[0]
            self.assertEqual(
                command, ["sudo", "-n", "/usr/local/sbin/orc-sdrforge-user-service", "is-active"]
            )

    def test_system_service_keeps_restricted_sudo(self) -> None:
        with patch("services.linux.systemd_service_manager.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            SystemdServiceManager._systemctl("start", "valhalla.service")
            self.assertEqual(run.call_args.args[0][:3], ["sudo", "-n", "/usr/bin/systemctl"])

    def test_user_service_rejects_arbitrary_arguments(self) -> None:
        with self.assertRaises(ValueError):
            SystemdServiceManager._systemctl("show", "libsdrforge.service", "--all")
        with self.assertRaises(ValueError):
            SystemdServiceManager._systemctl("enable", "libsdrforge.service")

    def test_service_registered(self) -> None:
        self.assertEqual(
            SystemdServiceManager._unit("openroadcode-sdrforge"),
            "libsdrforge.service",
        )


if __name__ == "__main__":
    unittest.main()
