# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Behavior tests for contract-bound vision lifecycle ownership."""

from __future__ import annotations

import threading
import time

import numpy as np

from controllers.computer_vision.camera_frame_processor import CameraFrameProcessor, CameraMode
from controllers.computer_vision.object_detector_if import Detection, DetectionFrame
from controllers.computer_vision.object_tracker_if import ObjectTrack, TrackFrame
from controllers.computer_vision.vision_controller import VisionController
from hardware_io.camera.camera_controls_if import CameraProfile
from hardware_io.camera.camera_if import CameraFrame
from ui.vision.vision_ui_state import VisionCameraMode, VisionLifecycle


class _Dispatcher:
    def __init__(self) -> None:
        self.callbacks = []

    def schedule_ui_callback(self, delay_ms, callback):
        assert delay_ms == 0
        self.callbacks.append(callback)
        return callback

    def run_all(self) -> None:
        while self.callbacks:
            self.callbacks.pop(0)()


class _Ui:
    def __init__(self) -> None:
        self.handler = None
        self.states = []

    def set_vision_request_handler(self, handler) -> None:
        self.handler = handler

    def set_vision_state(self, state) -> None:
        self.states.append(state)


class _Controls:
    def __init__(self) -> None:
        self.current_profile = None
        self.applied = []
        self.invalidations = 0
        self.restores = 0

    def apply(self, profile) -> None:
        self.current_profile = CameraProfile(profile)
        self.applied.append(self.current_profile)

    def invalidate(self) -> None:
        self.current_profile = None
        self.invalidations += 1

    def restore_day_defaults(self) -> None:
        self.restores += 1
        self.apply(CameraProfile.DAY)


class _Camera:
    def __init__(self, frame=None, *, open_error=None) -> None:
        self.is_open = False
        self.frame = frame
        self.open_error = open_error
        self.open_attempted = threading.Event()
        self.opened = threading.Event()
        self.read_once = threading.Event()
        self.closed = threading.Event()

    def open(self) -> None:
        self.open_attempted.set()
        if self.open_error is not None:
            raise self.open_error
        self.is_open = True
        self.opened.set()

    def read(self):
        if self.frame is not None and not self.read_once.is_set():
            self.read_once.set()
            return self.frame
        self.closed.wait(2.0)
        if not self.is_open:
            raise RuntimeError("camera closed")
        raise RuntimeError("timed out")

    def close(self) -> None:
        self.is_open = False
        self.closed.set()


class _Worker:
    def __init__(self) -> None:
        self.processed_frames = 0
        self.latest_result = None
        self.latest_tracks = None
        self.starts = 0
        self.stops = 0

    def start(self) -> None:
        self.starts += 1

    def submit(self, frame) -> None:
        self.processed_frames += 1
        self.latest_result = DetectionFrame(
            frame.timestamp_s,
            frame.sequence,
            12.0,
            (Detection("car", 0.8, 0.1, 0.2, 0.3, 0.4),),
        )
        self.latest_tracks = TrackFrame(
            frame.timestamp_s,
            frame.sequence,
            (ObjectTrack(7, "car", 0.8, 0.1, 0.2, 0.3, 0.4, 1.5),),
        )

    def stop(self) -> None:
        self.stops += 1


def _controller(camera, worker=None):
    dispatcher, ui, controls = _Dispatcher(), _Ui(), _Controls()
    controller = VisionController(
        dispatcher,
        ui,
        camera,
        controls,
        CameraFrameProcessor(CameraMode.DAY),
        worker or _Worker(),
        source_label="test-camera",
    )
    return controller, dispatcher, ui, controls


def _wait(event: threading.Event) -> None:
    assert event.wait(1.0)


def test_hide_invalidates_queued_active_state_and_releases_camera() -> None:
    """Deliver only inactive state when hide overtakes queued startup state."""
    camera = _Camera()
    controller, dispatcher, ui, controls = _controller(camera)
    controller.request_activate()
    _wait(camera.opened)

    controller.request_deactivate()
    dispatcher.run_all()

    assert ui.states[-1].lifecycle is VisionLifecycle.INACTIVE
    assert all(state.lifecycle is not VisionLifecycle.RUNNING for state in ui.states[1:])
    assert not camera.is_open
    assert controls.restores >= 1


def test_frame_is_published_as_immutable_rgb_state_with_tracks() -> None:
    """Translate backend pixels and tracks into one frontend snapshot."""
    bgr = np.asarray([[[1, 2, 3], [4, 5, 6]]], dtype=np.uint8)
    camera = _Camera(CameraFrame(bgr, 4.0, 9))
    controller, dispatcher, ui, _controls = _controller(camera)
    controller.request_activate()
    _wait(camera.read_once)
    time.sleep(0.01)
    dispatcher.run_all()

    state = ui.states[-1]
    assert state.lifecycle is VisionLifecycle.RUNNING
    assert state.image is not None
    assert state.image.data == bytes((3, 2, 1, 6, 5, 4))
    assert state.objects[0].track_id == 7
    assert state.inference_latency_s == 0.012
    controller.request_deactivate()


def test_target_state_requests_are_idempotent_and_do_not_touch_inactive_hardware() -> None:
    """Retain requested values without operating a closed camera device."""
    controller, dispatcher, ui, controls = _controller(_Camera())
    controller.request_camera_mode(VisionCameraMode.LOW_LIGHT)
    controller.request_camera_mode(VisionCameraMode.LOW_LIGHT)
    controller.request_ai_enabled(False)
    controller.request_ai_enabled(False)
    dispatcher.run_all()

    assert controls.applied == []
    assert ui.states[-1].requested_mode is VisionCameraMode.LOW_LIGHT
    assert not ui.states[-1].ai_enabled


def test_startup_failure_is_presented_without_leaking_resources() -> None:
    """Publish an error state and stop runtime resources after open failure."""
    camera = _Camera(open_error=RuntimeError("not present"))
    worker = _Worker()
    controller, dispatcher, ui, _controls = _controller(camera, worker)
    controller.request_activate()
    _wait(camera.open_attempted)
    time.sleep(0.01)
    dispatcher.run_all()

    assert ui.states[-1].lifecycle is VisionLifecycle.ERROR
    assert "not present" in ui.states[-1].status_message
    assert worker.stops == 1


def test_close_disconnects_requests_and_rejects_later_activation() -> None:
    """Permanently detach the UI and ignore activation after composition closes."""
    camera = _Camera()
    controller, dispatcher, ui, _controls = _controller(camera)
    controller.close()
    controller.request_activate()
    dispatcher.run_all()

    assert ui.handler is None
    assert not camera.opened.is_set()
