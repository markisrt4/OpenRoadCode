# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the Car UI off-road dashboard bus-driven lifecycle."""

import math
import unittest
from unittest.mock import Mock, patch

from apps.carUi.screens.offroad_dashboard_screen import OffroadDashboardScreen
from ui.navigation import PositionFix


class FakeHost:
    def __init__(self) -> None:
        self.screen_parent = Mock()
        self.activated = None
        self.callback = None
        self.cancelled = None
        self.status = None

    def activate_screen(self, screen) -> None:
        self.activated = screen

    def clear_screen_content(self) -> None:
        pass

    def set_screen_title(self, _title: str) -> None:
        pass

    def set_screen_back_action(self, _action) -> None:
        pass

    def set_screen_status(self, message: str) -> None:
        self.status = message

    def schedule_ui_callback(self, _delay_ms: int, callback):
        self.callback = callback
        return "poll-job"

    def cancel_ui_callback(self, callback_id: object) -> None:
        self.cancelled = callback_id


class OffroadDashboardScreenTest(unittest.TestCase):
    @patch("apps.carUi.screens.offroad_dashboard_screen.OffroadDashboardPanel")
    def test_show_builds_bus_driven_panel(self, panel_type) -> None:
        host = FakeHost()
        panel = panel_type.return_value
        screen = OffroadDashboardScreen(
            host,  # type: ignore[arg-type]
            create_menu_tile=Mock(),
            back_action=Mock(),
        )

        screen.show()

        panel.pack.assert_called_once_with(fill="both", expand=True)
        panel.set_status.assert_called_with("Waiting for navigation telemetry")
        self.assertEqual(host.status, "Waiting for navigation telemetry")

        screen.hide()
        self.assertIsNone(screen._panel)

    def test_current_position_is_presented_on_configured_map(self) -> None:
        host = FakeHost()
        presentation = Mock()
        screen = OffroadDashboardScreen(
            host,  # type: ignore[arg-type]
            create_menu_tile=Mock(),
            back_action=Mock(),
            map_presentation=presentation,
        )
        screen._latest_position = PositionFix(
            latitude_rad=math.radians(42.8028),
            longitude_rad=math.radians(-83.0127),
            altitude_m=210.0,
            pfom_m=3.0,
        )

        screen.show_current_location_on_map()

        presentation.focus_location.assert_called_once_with(
            42.8028,
            -83.0127,
            altitude_m=210.0,
        )
        self.assertEqual(host.status, "Opening current location")

    @patch("apps.carUi.screens.offroad_dashboard_screen.OffroadDashboardPanel")
    def test_navigation_error_uses_concise_user_message(self, panel_type) -> None:
        host = FakeHost()
        panel = panel_type.return_value
        screen = OffroadDashboardScreen(
            host,  # type: ignore[arg-type]
            create_menu_tile=Mock(),
            back_action=Mock(),
        )
        screen.show()

        screen.set_navigation_error(
            "openroad.navigation.imu",
            RuntimeError("MPU-6050 support requires a long implementation detail"),
        )

        message = panel.set_status.call_args.args[0]
        self.assertEqual(
            message.summary,
            "Navigation error [openroad.navigation.imu]: RuntimeError",
        )
        self.assertEqual(message.severity.name, "ERROR")
        self.assertIsNone(message.detail)
        self.assertEqual(
            host.status,
            "Navigation error [openroad.navigation.imu]: RuntimeError",
        )


if __name__ == "__main__":
    unittest.main()
