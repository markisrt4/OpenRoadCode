# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless tests for the Tk orcUi context-rail vehicle gauge binding."""

from unittest.mock import Mock

from apps.orcUi.frontend.tk.context_rail import ContextRail
from apps.orcUi.vehicle_presenter import VehiclePresentationState


def _rail_with_gauges() -> ContextRail:
    rail = ContextRail.__new__(ContextRail)
    rail._theme = Mock()
    rail._vehicle_state = VehiclePresentationState()
    rail._vehicle_gauges = {
        "rpm": Mock(),
        "fuel": Mock(),
    }
    rail._speed_value_label = Mock()
    rail._boost_value_label = Mock()
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
    rail._speed_value_label.configure.assert_called_once_with(text="47")
    rail._boost_value_label.configure.assert_called_once_with(text="11.7", fg=rail._theme.ui.accent_success)
    rail._vehicle_gauges["fuel"].set_value.assert_called_once_with(63.0)
    assert "coolant" not in rail._vehicle_gauges
    rail._gear_value_label.configure.assert_called_once_with(text="3")


def test_missing_vehicle_values_leave_gauges_unset() -> None:
    rail = _rail_with_gauges()

    rail._paint_vehicle_values()

    for gauge in rail._vehicle_gauges.values():
        gauge.set_value.assert_called_once_with(None)

    rail._speed_value_label.configure.assert_called_once_with(text="—")
    rail._boost_value_label.configure.assert_called_once_with(text="—", fg=rail._theme.ui.accent_success)
    rail._gear_value_label.configure.assert_called_once_with(text="—")


def test_home_boost_readout_retains_high_pressure_warning():
    rail = _rail_with_gauges()
    rail._vehicle_state = VehiclePresentationState(boost_psi=23.0)
    rail._paint_vehicle_values()
    rail._boost_value_label.configure.assert_called_once_with(text="23.0", fg=rail._theme.ui.accent_danger)
