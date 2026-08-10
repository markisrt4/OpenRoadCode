"""Tests for the Car UI off-road dashboard destination lifecycle."""

import unittest
from unittest.mock import Mock, patch

from apps.carUi.screens.offroad_dashboard_screen import OffroadDashboardScreen


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
    @patch("apps.carUi.screens.offroad_dashboard_screen.NavigationStatePresenter")
    @patch("apps.carUi.screens.offroad_dashboard_screen.OffroadDashboardPanel")
    def test_show_polls_and_hide_releases_controller(
        self,
        panel_type,
        presenter_type,
    ) -> None:
        host = FakeHost()
        controller = Mock()
        controller.is_started = True
        controller.calibration = None
        controller.read_state.return_value = Mock()
        panel = panel_type.return_value
        presenter = presenter_type.return_value
        screen = OffroadDashboardScreen(
            host,  # type: ignore[arg-type]
            controller=controller,
            create_menu_tile=Mock(),
            back_action=Mock(),
        )

        screen.show()

        controller.start.assert_called_once()
        presenter.present.assert_called_once_with(controller.read_state.return_value)
        self.assertEqual(host.callback, screen._poll)

        screen.hide()

        self.assertEqual(host.cancelled, "poll-job")
        controller.stop.assert_called_once()
        panel.pack.assert_called_once_with(fill="both", expand=True)

    @patch("apps.carUi.screens.offroad_dashboard_screen.OffroadDashboardPanel")
    def test_sensor_failure_uses_concise_user_message(self, panel_type) -> None:
        host = FakeHost()
        controller = Mock()
        controller.start.side_effect = RuntimeError(
            "MPU-6050 support requires a long implementation detail"
        )
        panel = panel_type.return_value
        screen = OffroadDashboardScreen(
            host,  # type: ignore[arg-type]
            controller=controller,
            create_menu_tile=Mock(),
            back_action=Mock(),
        )

        with self.assertLogs(
            "apps.carUi.screens.offroad_dashboard_screen",
            level="WARNING",
        ):
            screen.show()

        message = panel.set_status.call_args.args[0]
        self.assertEqual(message.summary, "Motion sensor unavailable")
        self.assertEqual(message.severity.name, "ERROR")
        self.assertIsNone(message.detail)
        self.assertEqual(host.status, "Motion sensor unavailable")


if __name__ == "__main__":
    unittest.main()
