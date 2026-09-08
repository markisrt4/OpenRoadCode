# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless tests for the home context-rail vehicle gauge binding."""

from unittest.mock import Mock

from apps.orcUi.context_rail import ContextRail
from apps.orcUi.vehicle_presenter import VehiclePresentationState


def _rail_with_gauges() -> ContextRail:
    rail = ContextRail.__new__(ContextRail)
    rail._vehicle_state = VehiclePresentationState()
    rail._vehicle_gauges = {
        "rpm": Mock(),
        "speed": Mock(),
        "boost": Mock(),
        "fuel": Mock(),
        "coolant": Mock(),
    }
    rail._gear_value_label = Mock()
    return rail


def test_vehicle_values_feed_compact_home_gauges() -> None:
    rail = _rail_with_gauges()
    rail._vehicle_state = VehiclePresentationState(
        speed_mph=47.0,
        engine_speed_rpm=3250.0,
        boost_psi=11.7,
        fuel_percent=63.0,
        gear="3",
        coolant_temperature_f=194.0,
    )

    rail._paint_vehicle_values()

    rail._vehicle_gauges["rpm"].set_value.assert_called_once_with(3.25)
    rail._vehicle_gauges["speed"].set_value.assert_called_once_with(47.0)
    rail._vehicle_gauges["boost"].set_value.assert_called_once_with(11.7)
    rail._vehicle_gauges["fuel"].set_value.assert_called_once_with(63.0)
    rail._vehicle_gauges["coolant"].set_value.assert_called_once_with(194.0)
    rail._gear_value_label.configure.assert_called_once_with(text="3")


def test_missing_vehicle_values_leave_gauges_unset() -> None:
    rail = _rail_with_gauges()

    rail._paint_vehicle_values()

    for gauge in rail._vehicle_gauges.values():
        gauge.set_value.assert_called_once_with(None)

    rail._gear_value_label.configure.assert_called_once_with(text="—")
