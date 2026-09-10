# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for runtime adapters injected into the ORC Tk shell."""

import unittest
from unittest.mock import Mock, patch

from apps.orcUi.core_runtime import MapRuntime, StateIngressRuntime


class MapRuntimeTest(unittest.TestCase):
    @patch.dict("apps.orcUi.core_runtime.os.environ", {"DISPLAY": ":9"})
    def test_launch_supplies_display_and_parent_window(self) -> None:
        renderer = Mock()
        runtime = MapRuntime(renderer)

        runtime.launch(1234)

        renderer.launch.assert_called_once_with(display=":9", parent_window_id=1234)

    def test_stop_delegates_to_renderer(self) -> None:
        renderer = Mock()
        runtime = MapRuntime(renderer)

        runtime.stop()

        renderer.stop.assert_called_once_with()


class StateIngressRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schedule_ui = Mock()
        self.vehicle_sink = Mock()
        self.position_sink = Mock()
        self.attitude_sink = Mock()
        self.guidance_sink = Mock()
        self.dispatcher = Mock()
        self.runtime = StateIngressRuntime(
            schedule_ui=self.schedule_ui,
            apply_vehicle_state=self.vehicle_sink,
            apply_position_state=self.position_sink,
            apply_attitude_state=self.attitude_sink,
            apply_route_guidance_state=self.guidance_sink,
            dispatcher=self.dispatcher,
        )

    def test_start_schedules_ui_drain_before_dispatcher(self) -> None:
        self.runtime.start()

        self.schedule_ui.assert_called_once_with(0, self.runtime._drain_ui_queue)
        self.dispatcher.start.assert_called_once_with()

    def test_lifecycle_delegates_to_dispatcher(self) -> None:
        self.runtime.start()
        self.runtime.close()

        self.dispatcher.start.assert_called_once_with()
        self.dispatcher.close.assert_called_once_with()

    def test_close_drops_late_ui_delivery(self) -> None:
        self.runtime.close()

        self.runtime._schedule_state(self.vehicle_sink)
        self.runtime._drain_ui_queue()

        self.vehicle_sink.assert_not_called()

    def test_worker_state_enqueue_does_not_call_tk_scheduler(self) -> None:
        self.runtime._schedule_state(self.vehicle_sink)

        self.schedule_ui.assert_not_called()
        self.vehicle_sink.assert_not_called()

    def test_ui_drain_applies_queued_state_and_reschedules(self) -> None:
        self.runtime._schedule_state(self.vehicle_sink)

        self.runtime._drain_ui_queue()

        self.vehicle_sink.assert_called_once_with()
        self.schedule_ui.assert_called_once_with(
            self.runtime._UI_DRAIN_INTERVAL_MS,
            self.runtime._drain_ui_queue,
        )

    @patch("apps.orcUi.core_runtime.VehiclePresenter.present")
    def test_vehicle_message_is_presented_before_ui_drain(self, present: Mock) -> None:
        message = Mock()
        state = present.return_value

        self.runtime._on_vehicle_message(message)

        present.assert_called_once_with(message.data)
        self.schedule_ui.assert_not_called()
        self.vehicle_sink.assert_not_called()
        self.runtime._drain_ui_queue()
        self.vehicle_sink.assert_called_once_with(state)

    @patch("apps.orcUi.core_runtime.NavigationPresenter.present_position")
    def test_position_message_is_presented_before_ui_drain(self, present: Mock) -> None:
        message = Mock()
        state = present.return_value

        self.runtime._on_position_message(message)

        self.schedule_ui.assert_not_called()
        self.runtime._drain_ui_queue()
        self.position_sink.assert_called_once_with(state)

    def test_route_guidance_message_is_forwarded_on_ui_drain(self) -> None:
        message = Mock()
        self.runtime._on_route_guidance_message(message)
        self.schedule_ui.assert_not_called()
        self.runtime._drain_ui_queue()
        self.guidance_sink.assert_called_once_with(message)

    @patch("apps.orcUi.core_runtime.NavigationPresenter.present_attitude")
    def test_attitude_message_is_presented_before_ui_drain(self, present: Mock) -> None:
        message = Mock()
        state = present.return_value

        self.runtime._on_attitude_message(message)

        self.schedule_ui.assert_not_called()
        self.runtime._drain_ui_queue()
        self.attitude_sink.assert_called_once_with(state)


if __name__ == "__main__":
    unittest.main()