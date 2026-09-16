# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for display routing of managed auxiliary browser dashboards."""

import unittest
from unittest.mock import Mock

from apps.carUi.screens.aircraft_screen import ADSB_APP_KEY, AircraftScreen


class AuxiliaryDisplayTest(unittest.TestCase):
    def test_adsb_uses_managed_application(self) -> None:
        manager = Mock()
        screen = AircraftScreen.__new__(AircraftScreen)
        screen._app_runtime_manager = manager
        screen._auxiliary_display = ":0"
        screen.set_status = Mock()
        screen._return_overlay = Mock()

        screen.launch_adsb()

        manager.launch.assert_called_once_with(
            ADSB_APP_KEY,
            screen.set_status,
        )
        screen._return_overlay.show.assert_called_once_with(
            x=12,
            y=12,
            display=":0",
        )

    def test_adsb_return_closes_managed_application_and_goes_home(self) -> None:
        manager = Mock()
        screen = AircraftScreen.__new__(AircraftScreen)
        screen._app_runtime_manager = manager
        screen._auxiliary_display = ":0"
        screen._return_overlay = Mock()
        screen.set_status = Mock()
        screen._home_action = Mock()

        screen._return_from_adsb()

        screen._return_overlay.hide.assert_called_once_with()
        manager.close.assert_called_once_with(
            ADSB_APP_KEY,
            screen.set_status,
        )
        screen._home_action.assert_called_once_with()



if __name__ == "__main__":
    unittest.main()
