# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for display routing of auxiliary browser dashboards."""

import unittest
from unittest.mock import Mock

from apps.carUi.screens.aircraft_screen import AircraftScreen
from apps.carUi.screens.weather_screen import WEATHER_APP_KEY, WeatherScreen


class AuxiliaryDisplayTest(unittest.TestCase):
    def test_adsb_uses_auxiliary_display(self) -> None:
        launcher = Mock()
        screen = AircraftScreen.__new__(AircraftScreen)
        screen._adsb_launcher = launcher
        screen._auxiliary_display = ":0"
        screen.set_status = Mock()
        screen._return_overlay = Mock()

        screen.launch_adsb()

        launcher.launch.assert_called_once_with(
            remote_display=":0",
            set_status=screen.set_status,
        )
        screen._return_overlay.show.assert_called_once_with(
            x=12,
            y=12,
            display=":0",
        )

    def test_weather_dashboard_uses_managed_application(self) -> None:
        manager = Mock()
        screen = WeatherScreen.__new__(WeatherScreen)
        screen._app_runtime_manager = manager
        screen._auxiliary_display = ":4"
        screen.set_status = Mock()
        screen._return_overlay = Mock()

        screen.toggle_weather_dashboard()

        manager.launch.assert_called_once_with(
            WEATHER_APP_KEY,
            screen.set_status,
        )
        screen._return_overlay.show.assert_called_once_with(
            x=12,
            y=12,
            display=":4",
        )

    def test_adsb_return_closes_dashboard_and_goes_home(self) -> None:
        screen = AircraftScreen.__new__(AircraftScreen)
        screen._adsb_launcher = Mock()
        screen._auxiliary_display = ":0"
        screen._return_overlay = Mock()
        screen.set_status = Mock()
        screen._home_action = Mock()

        screen._return_from_adsb()

        screen._return_overlay.hide.assert_called_once_with()
        screen._adsb_launcher.stop.assert_called_once_with(
            ":0",
            screen.set_status,
        )
        screen._home_action.assert_called_once_with()

    def test_weather_return_closes_managed_application_and_goes_home(self) -> None:
        manager = Mock()
        screen = WeatherScreen.__new__(WeatherScreen)
        screen._app_runtime_manager = manager
        screen._auxiliary_display = ":4"
        screen._return_overlay = Mock()
        screen.set_status = Mock()
        screen._home_action = Mock()

        screen._return_from_dashboard()

        screen._return_overlay.hide.assert_called_once_with()
        manager.close.assert_called_once_with(
            WEATHER_APP_KEY,
            screen.set_status,
        )
        screen._home_action.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
