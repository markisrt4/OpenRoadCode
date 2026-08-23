# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Car UI lighting runtime composition."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from apps.carUi.runtime.lighting_runtime_factory import create_lighting_controller
from controllers.lighting.parsers.leddmx_config_parser import LedDmxBluetoothConfig


class LightingRuntimeFactoryTest(unittest.TestCase):
    @patch("apps.carUi.runtime.lighting_runtime_factory.LedDmxController")
    @patch("apps.carUi.runtime.lighting_runtime_factory.BleakGattTransport")
    @patch("apps.carUi.runtime.lighting_runtime_factory.load_leddmx_config")
    def test_leddmx_uses_discovery_when_address_is_not_configured(
        self,
        load_config,
        transport_type,
        controller_type,
    ) -> None:
        load_config.return_value = self._config()
        transport = Mock()
        transport_type.return_value = transport

        controller = create_lighting_controller(project_root=Path("/project"))

        self.assertIs(controller, controller_type.return_value)
        transport_type.assert_called_once_with(
            address=None,
            characteristic_uuid="0000ffe1-0000-1000-8000-00805f9b34fb",
            excluded_service_uuids=(),
            excluded_name_fragments=(),
            write_with_response=False,
            command_delay_seconds=0.05,
            reconnect_delay_seconds=0.25,
            scan_timeout_seconds=15.0,
            connect_timeout_seconds=8.0,
        )
        controller_type.assert_called_once_with(transport=transport)

    @staticmethod
    def _config() -> LedDmxBluetoothConfig:
        return LedDmxBluetoothConfig(
            service_uuid="0000ffe0-0000-1000-8000-00805f9b34fb",
            characteristic_uuid="0000ffe1-0000-1000-8000-00805f9b34fb",
            excluded_service_uuids=(),
            excluded_name_fragments=(),
            write_with_response=False,
            command_delay_seconds=0.05,
            reconnect_delay_seconds=0.25,
            scan_timeout_seconds=15.0,
            candidate_connect_timeout_seconds=8.0,
        )


if __name__ == "__main__":
    unittest.main()
