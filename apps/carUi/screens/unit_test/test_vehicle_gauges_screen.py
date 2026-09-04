# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the Car UI vehicle-gauge bus consumer."""

import unittest
from unittest.mock import Mock, patch

from apps.carUi.screens.vehicle_gauges_screen import VehicleGaugesScreen
from messaging.contracts.automotive import VehicleStateData, VehicleStateMessage
from messaging.contracts.common import Timestamp


class FakeHost:
    def __init__(self) -> None:
        self.screen_parent = Mock()
        self.status = None

    def activate_screen(self, _screen) -> None:
        pass

    def clear_screen_content(self) -> None:
        pass

    def set_screen_title(self, _title: str) -> None:
        pass

    def set_screen_back_action(self, _action) -> None:
        pass

    def set_screen_status(self, message: str) -> None:
        self.status = message


def _message() -> VehicleStateMessage:
    return VehicleStateMessage(
        version=1,
        timestamp=Timestamp(seconds=1, nanoseconds=0),
        source="test-obd",
        data=VehicleStateData(
            engine_speed_rad_s=100.0,
            vehicle_speed_m_s=20.0,
            transmission_gear=3,
            throttle_position=0.4,
            accelerator_pedal_position=0.3,
            engine_load=0.5,
            intake_manifold_pressure_pa=120000.0,
            barometric_pressure_pa=101000.0,
            boost_pressure_pa=19000.0,
            mass_air_flow_kg_s=0.02,
            coolant_temperature_k=360.0,
            intake_air_temperature_k=300.0,
            fuel_level=0.75,
            control_voltage_v=13.8,
        ),
    )


class VehicleGaugesScreenTest(unittest.TestCase):
    @patch("apps.carUi.screens.vehicle_gauges_screen.VehicleGaugePanel")
    def test_message_updates_si_gauge_interface(self, panel_type) -> None:
        host = FakeHost()
        panel = panel_type.return_value
        screen = VehicleGaugesScreen(
            host,  # type: ignore[arg-type]
            create_menu_tile=Mock(),
            back_action=Mock(),
        )
        message = _message()

        screen.show()
        screen.set_vehicle_message(message)

        panel.set_engine_speed.assert_called_with(100.0)
        panel.set_vehicle_speed.assert_called_with(20.0)
        panel.set_boost_pressure.assert_called_with(19000.0)
        panel.set_coolant_temperature.assert_called_with(360.0)
        panel.set_control_voltage.assert_called_with(13.8)
        self.assertEqual(host.status, "Vehicle telemetry: test-obd · 1 messages")

    @patch("apps.carUi.screens.vehicle_gauges_screen.VehicleGaugePanel")
    def test_latest_message_is_rendered_when_screen_is_shown(self, panel_type) -> None:
        host = FakeHost()
        panel = panel_type.return_value
        screen = VehicleGaugesScreen(
            host,  # type: ignore[arg-type]
            create_menu_tile=Mock(),
            back_action=Mock(),
        )

        screen.set_vehicle_message(_message())
        screen.show()

        panel.set_vehicle_speed.assert_called_with(20.0)
        self.assertEqual(host.status, "Vehicle telemetry: test-obd · 1 messages")

    @patch("apps.carUi.screens.vehicle_gauges_screen.VehicleGaugePanel")
    def test_empty_screen_waits_for_bus_telemetry(self, panel_type) -> None:
        host = FakeHost()
        screen = VehicleGaugesScreen(
            host,  # type: ignore[arg-type]
            create_menu_tile=Mock(),
            back_action=Mock(),
        )

        screen.show()

        panel_type.return_value.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )
        self.assertEqual(host.status, "Waiting for vehicle telemetry")


if __name__ == "__main__":
    unittest.main()
