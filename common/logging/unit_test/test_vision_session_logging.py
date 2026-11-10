# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Session correlation and cleanup independently of capture/inference packages."""

import logging
import threading
from unittest.mock import Mock, patch

import pytest

from common.logging.structured import operation
from common.logging.unit_test.test_device_logging import PRIVATE, records, wait_until
from controllers.computer_vision.camera_frame_processor import CameraMode
from controllers.computer_vision.vision_controller import VisionController
from ui.vision.vision_ui_state import VisionLifecycle


def session():
    dispatcher, ui, camera, controls, processor, worker = (Mock() for _ in range(6))
    processor.mode = processor.last_effective_mode = CameraMode.AUTO
    processor.last_luminance = 100
    worker.processed_frames = 0
    controller = VisionController(dispatcher, ui, camera, controls, processor, worker,
                                  source_label=PRIVATE)
    return controller, dispatcher, ui, camera, controls, worker


def test_camera_session_failure_recovery_and_shutdown_share_session_id(caplog):
    caplog.set_level(logging.DEBUG)
    controller, _, _, camera, _, _ = session()
    camera.open.side_effect = OSError(PRIVATE)
    for _ in range(2):
        controller.request_activate()
        wait_until(lambda: controller._thread is None)
    release = threading.Event()
    camera.open.side_effect = None
    camera.read.side_effect = lambda: release.wait(2)
    camera.close.side_effect = release.set
    with operation("vision-request"):
        controller.request_activate()
    wait_until(lambda: camera.read.call_count == 1)
    controller.request_deactivate()
    controller.close()
    emitted = records(caplog, "vision.session")
    failures = [r for r in emitted if r["event"] == "vision.failed"]
    assert len(failures) == 1 and failures[0]["stage"] == "capture_session"
    recovered = next(r for r in emitted if r["event"] == "vision.recovered")
    assert recovered["operation_id"] == "vision-request"
    states = [r for r in emitted if r["event"] == "vision.state_changed"
              and r["operation_id"] == "vision-request"]
    assert {r["state"] for r in states} >= {"running", "inactive", "closed"}


def test_stale_delivery_logs_original_operation_without_updating_ui(caplog):
    caplog.set_level(logging.DEBUG)
    controller, dispatcher, ui, _, _, _ = session()
    with operation("old-session"):
        controller._publish(0, controller._state(VisionLifecycle.RUNNING))
    callback = dispatcher.schedule_ui_callback.call_args.args[1]
    controller._generation += 1  # A newer session supersedes the queued delivery.
    ui.set_vision_state.reset_mock()
    callback()
    ui.set_vision_state.assert_not_called()
    discarded = next(r for r in records(caplog, "vision.session")
                     if r["event"] == "vision.result_discarded")
    assert discarded["operation_id"] == "old-session"


def test_cleanup_failures_are_private_and_do_not_skip_camera_release(caplog):
    caplog.set_level(logging.DEBUG)
    controller, _, _, camera, controls, worker = session()
    camera.open.side_effect = RuntimeError(PRIVATE)
    controls.restore_day_defaults.side_effect = OSError(PRIVATE)
    worker.stop.side_effect = OSError(PRIVATE)
    controller.request_activate()
    wait_until(lambda: controller._thread is None)
    camera.close.assert_called_once()
    emitted = records(caplog, "vision.session")
    assert {r["stage"] for r in emitted if r["event"] == "vision.failed"} == {
        "capture_session", "restore_profile", "worker_stop"}


def test_thread_start_failure_does_not_leave_active_camera_session(caplog):
    caplog.set_level(logging.DEBUG)
    controller, _, _, camera, _, _ = session()
    with patch("controllers.computer_vision.vision_controller.threading.Thread.start",
               side_effect=OSError(PRIVATE)):
        with pytest.raises(OSError):
            controller.request_activate()
    assert not controller._active and controller._thread is None
    camera.open.assert_not_called()
    assert any(r["stage"] == "activate" and r["event"] == "vision.failed"
               for r in records(caplog, "vision.session"))
