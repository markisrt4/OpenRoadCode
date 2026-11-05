# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import time
from threading import Event

from controllers.navigation.waze_gesture_controller import WazeGestureController
from ui.navigation.waze_gesture_if import WazeGesture


class Adapter:
    available = True

    def __init__(self):
        self.started, self.finish = Event(), Event()
        self.calls = []

    def perform(self, gesture, cancelled):
        self.calls.append(gesture)
        self.cancelled = cancelled
        self.started.set()
        self.finish.wait(timeout=2)


def settled(controller):
    deadline = time.monotonic() + 1
    while controller.state.busy and time.monotonic() < deadline:
        time.sleep(.005)
    assert not controller.state.busy


def test_gestures_are_async_serialized_and_hidden_views_reject_requests():
    adapter = Adapter()
    controller = WazeGestureController(adapter)
    controller.request_gesture(WazeGesture.PAN_UP)
    assert not adapter.calls
    controller.set_visible(True)
    controller.request_gesture(WazeGesture.PAN_LEFT)
    assert adapter.started.wait(1)
    assert controller.state.busy
    controller.request_gesture(WazeGesture.PAN_RIGHT)
    assert adapter.calls == [WazeGesture.PAN_LEFT]
    controller.set_visible(False)
    assert adapter.cancelled()
    adapter.finish.set()
    settled(controller)
    assert controller.state.status == ''
    assert not controller.state.available


def test_stale_completion_cannot_update_a_reopened_view_and_close_revokes_input():
    adapter = Adapter()
    controller = WazeGestureController(adapter)
    controller.set_visible(True)
    controller.request_gesture(WazeGesture.ZOOM_IN)
    assert adapter.started.wait(1)
    controller.set_visible(False)
    controller.set_visible(True)
    assert adapter.cancelled()
    adapter.finish.set()
    settled(controller)
    assert controller.state.status == ''
    controller.close()
    controller.set_visible(True)
    controller.request_gesture(WazeGesture.ZOOM_OUT)
    assert not controller.state.available
    assert adapter.calls == [WazeGesture.ZOOM_IN]


def test_adapter_failure_is_reported_and_does_not_leave_controls_busy():
    class Failing:
        available = True

        def perform(self, gesture, cancelled):
            raise RuntimeError('missing viewer')

    controller = WazeGestureController(Failing())
    controller.set_visible(True)
    controller.request_gesture(WazeGesture.ZOOM_OUT)
    settled(controller)
    assert 'unavailable' in controller.state.status
