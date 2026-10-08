# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for service-manager runtime selection."""

import unittest
from unittest.mock import patch

from services.common.service_manager_runtime import (
    create_service_manager,
    detect_service_manager_runtime,
)
from services.linux.systemd_service_manager import SystemdServiceManager
from services.termux.service_manager import RunitServiceManager


class ServiceManagerRuntimeTest(unittest.TestCase):
    def test_termux_version_selects_termux(self) -> None:
        self.assertEqual(
            detect_service_manager_runtime(
                {"TERMUX_VERSION": "0.118"}, platform="linux"
            ),
            "termux",
        )

    def test_termux_prefix_selects_termux(self) -> None:
        self.assertEqual(
            detect_service_manager_runtime(
                {"PREFIX": "/data/data/com.termux/files/usr"},
                platform="linux",
            ),
            "termux",
        )

    def test_normal_linux_selects_linux(self) -> None:
        self.assertEqual(
            detect_service_manager_runtime({}, platform="linux"),
            "linux",
        )

    def test_unsupported_platform_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unsupported OpenRoadCode"):
            detect_service_manager_runtime({}, platform="darwin")

    @patch("services.termux.service_manager.RunitServiceManager")
    def test_factory_constructs_runit_manager_on_termux(self, manager) -> None:
        created = create_service_manager(
            {"TERMUX_VERSION": "0.118"}, platform="linux"
        )
        self.assertIs(created, manager.return_value)

    @patch("services.linux.systemd_service_manager.SystemdServiceManager")
    def test_factory_constructs_systemd_manager_on_linux(self, manager) -> None:
        created = create_service_manager({}, platform="linux")
        self.assertIs(created, manager.return_value)

    def test_concrete_manager_types_remain_platform_specific(self) -> None:
        self.assertIsNot(RunitServiceManager, SystemdServiceManager)


if __name__ == "__main__":
    unittest.main()
