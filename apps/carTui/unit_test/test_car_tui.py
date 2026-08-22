# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for static Car TUI home routing."""

import unittest
from argparse import Namespace
from unittest.mock import Mock, patch

from apps.carTui.car_tui import CarTui
from apps.carTui.main import build_dependencies, main
from apps.carTui.vehicle_bus_state import VehicleBusState
from controllers.navigation import SimulatedNavigationController
from messaging.message_dispatcher import MessageDispatcher


class FakeWindow:
    def __init__(self, keys: list[int]) -> None:
        self._keys = iter(keys)

    def getmaxyx(self):
        return (24, 100)

    def erase(self) -> None:
        pass

    def addnstr(self, *_args) -> None:
        pass

    def refresh(self) -> None:
        pass

    def nodelay(self, _enabled: bool) -> None:
        pass

    def keypad(self, _enabled: bool) -> None:
        pass

    def getch(self) -> int:
        return next(self._keys)


class CarTuiTest(unittest.TestCase):
    @patch("apps.carTui.car_tui._configure_curses")
    def test_number_key_opens_static_route(self, _configure) -> None:
        dependencies = Mock()
        app = CarTui(dependencies)
        navigation = Mock()
        navigation.run.return_value = False
        app._routes["navigation"] = navigation
        window = FakeWindow([ord("1")])

        app.run(window)

        navigation.run.assert_called_once_with(window)

    @patch("apps.carTui.car_tui._configure_curses")
    def test_q_exits_from_home(self, _configure) -> None:
        app = CarTui(Mock())
        app.run(FakeWindow([ord("q")]))

    def test_demo_uses_simulated_navigation_and_bus_vehicle_state(self) -> None:
        dependencies = build_dependencies(Namespace(simulate=True))
        try:
            self.assertIsInstance(
                dependencies.navigation_controller,
                SimulatedNavigationController,
            )
            self.assertIsInstance(dependencies.vehicle_state, VehicleBusState)
            self.assertIsInstance(
                dependencies.vehicle_dispatcher,
                MessageDispatcher,
            )
        finally:
            dependencies.close()

    @patch("apps.carTui.main.curses.wrapper")
    @patch("apps.carTui.main.parse_args")
    @patch("apps.carTui.main.build_dependencies")
    def test_demo_enables_simulated_gps_display(
        self, build_dependencies_mock, parse_args_mock, wrapper_mock
    ) -> None:
        parse_args_mock.return_value = Namespace(simulate=True, gps=False)
        dependencies = build_dependencies_mock.return_value

        self.assertEqual(main(), 0)

        app_run = wrapper_mock.call_args.args[0]
        self.assertTrue(app_run.__self__._routes["navigation"]._gps_enabled)
        dependencies.close.assert_called_once_with()
