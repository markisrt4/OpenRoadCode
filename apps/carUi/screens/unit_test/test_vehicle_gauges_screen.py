# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the Car UI vehicle-gauge destination lifecycle."""

import unittest
from unittest.mock import Mock, patch

from apps.carUi.screens.vehicle_gauges_screen import VehicleGaugesScreen


class FakeHost:
    def __init__(self) -> None:
        self.screen_parent = Mock()
        self.callback = None
        self.cancelled = None
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

    def schedule_ui_callback(self, _delay_ms: int, callback):
        self.callback = callback
        return "vehicle-poll"

    def cancel_ui_callback(self, callback_id: object) -> None:
        self.cancelled = callback_id


class VehicleGaugesScreenTest(unittest.TestCase):
    @patch("apps.carUi.screens.vehicle_gauges_screen.VehicleGaugePanel")
    def test_source_is_polled_only_while_screen_is_visible(
        self,
        panel_type,
    ) -> None:
        host = FakeHost()
        source = Mock()
        state = source.read_state.return_value
        panel = panel_type.return_value
        screen = VehicleGaugesScreen(
            host,  # type: ignore[arg-type]
            source=source,
            create_menu_tile=Mock(),
            back_action=Mock(),
        )

        screen.show()

        source.connect.assert_called_once()
        panel.update_state.assert_called_with(state, connected=True)
        self.assertEqual(host.callback, screen._poll)

        screen.hide()

        self.assertEqual(host.cancelled, "vehicle-poll")
        source.disconnect.assert_called_once()

    @patch("apps.carUi.screens.vehicle_gauges_screen.VehicleGaugePanel")
    def test_unconfigured_source_still_displays_panel(self, panel_type) -> None:
        host = FakeHost()
        screen = VehicleGaugesScreen(
            host,  # type: ignore[arg-type]
            source=None,
            create_menu_tile=Mock(),
            back_action=Mock(),
        )

        screen.show()

        panel_type.return_value.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )
        self.assertEqual(host.status, "Vehicle telemetry is not configured")


if __name__ == "__main__":
    unittest.main()
