# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Camera, perception and sensor diagnostics without optional hardware packages."""

import json
import logging
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from common.logging.structured import JsonFormatter, operation, validate_event
from controllers.computer_vision.model_readiness import YoloModelReadiness
from controllers.computer_vision.object_detector_if import DetectionFrame
from controllers.computer_vision.perception_worker import PerceptionWorker
from controllers.environmental.ambient_light_controller import AmbientLightController
from controllers.environmental.barometric_controller import BarometricController
from controllers.environmental.barometric_source_if import BarometricSample
from hardware_io.camera.camera_if import CameraFrame
from hardware_io.camera.v4l2_camera import V4L2Camera
from hardware_io.camera.v4l2_camera_controls import V4L2CameraProfileController
from hardware_io.camera.camera_controls_if import CameraProfile

PRIVATE = "private-image /private/device https://private.test/?token=private 42.8028 -83.0127"


def records(caplog, prefix):
    result = [json.loads(JsonFormatter().format(r)) for r in caplog.records
              if r.name.startswith(prefix)]
    allowed = {"timestamp", "level", "component", "event", "message", "pid",
               "operation_id", "stage", "state", "reason", "exception_type",
               "result_count", "category", "delivered", "watcher_count"}
    for record in result:
        validate_event(record)
        assert set(record) <= allowed
    text = json.dumps(result)
    for private in ("private", "42.8028", "-83.0127", "latitude", "longitude",
                    "image", "model_name", "database_path", "device_address"):
        assert private not in text
    return result


def wait_until(predicate):
    deadline = time.monotonic() + 2
    while not predicate() and time.monotonic() < deadline:
        time.sleep(0.005)
    assert predicate()


def test_camera_open_capture_recovery_and_close_are_private(caplog):
    caplog.set_level(logging.DEBUG)
    cv2 = Mock()
    capture = cv2.VideoCapture.return_value
    capture.isOpened.return_value = False
    camera = V4L2Camera(PRIVATE)
    with patch.dict(sys.modules, cv2=cv2), operation("camera-session"):
        for _ in range(2):
            with pytest.raises(RuntimeError):
                camera.open()
        capture.isOpened.return_value = True
        camera.open()
        capture.read.side_effect = [(False, None), (False, None), (True, PRIVATE)]
        for _ in range(2):
            with pytest.raises(RuntimeError):
                camera.read()
        assert camera.read().image == PRIVATE
        camera.close()
    emitted = records(caplog, "vision.camera")
    failures = [r for r in emitted if r["event"] == "camera.failed"]
    recoveries = [r for r in emitted if r["event"] == "camera.recovered"]
    assert [r["stage"] for r in failures] == ["open", "capture"]
    assert [r["stage"] for r in recoveries] == ["open", "capture"]
    assert all(r["operation_id"] == "camera-session" for r in emitted)
    assert [r["state"] for r in emitted if r["event"] == "camera.state_changed"] == ["open", "closed"]


def test_camera_profile_failure_and_recovery_do_not_log_control_output(caplog):
    caplog.set_level(logging.DEBUG)
    controls = V4L2CameraProfileController(PRIVATE)
    with patch("hardware_io.camera.v4l2_camera_controls.subprocess.run") as run:
        run.return_value = SimpleNamespace(returncode=1, stderr=PRIVATE, stdout=PRIVATE)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                controls.apply(CameraProfile.DAY)
        run.return_value = SimpleNamespace(returncode=0)
        controls.apply(CameraProfile.DAY)
        controls.apply(CameraProfile.DAY)
    emitted = records(caplog, "vision.camera.controls")
    assert len([r for r in emitted if r["event"] == "camera.failed"]) == 1
    assert len([r for r in emitted if r["event"] == "camera.recovered"]) == 1
    assert len([r for r in emitted if r["event"] == "camera.state_changed"]) == 1


def test_model_loading_is_correlated_and_cached_without_logging_paths(caplog):
    caplog.set_level(logging.DEBUG)
    yolo = Mock(side_effect=[OSError(PRIVATE), OSError(PRIVATE), object()])
    readiness = YoloModelReadiness(PRIVATE)
    with patch.dict(sys.modules, ultralytics=SimpleNamespace(YOLO=yolo)):
        for _ in range(2):
            with pytest.raises(OSError):
                readiness.prepare()
        with operation("model-request"):
            model = readiness.prepare()
        assert readiness.prepare() is model
    emitted = records(caplog, "vision.model")
    assert yolo.call_count == 3
    assert len([r for r in emitted if r["event"] == "vision.failed"]) == 1
    recovery = next(r for r in emitted if r["event"] == "vision.recovered")
    assert recovery["operation_id"] == "model-request"


@pytest.mark.parametrize("stage", ["inference", "tracking"])
def test_perception_survives_failure_and_recovers_on_next_frame(caplog, stage):
    caplog.set_level(logging.DEBUG)
    detector, tracker = Mock(), Mock()
    result = DetectionFrame(1, 1, 1, ())
    detector.detect.return_value = result
    tracker.update.return_value = None
    failing = detector.detect if stage == "inference" else tracker.update
    failing.side_effect = [RuntimeError(PRIVATE), RuntimeError(PRIVATE),
                           result if stage == "inference" else None]
    worker = PerceptionWorker(detector, tracker)
    with operation("vision-session"):
        worker.start()
    try:
        for index in range(3):
            worker.submit(CameraFrame(PRIVATE, 1, index))
            wait_until(lambda: failing.call_count >= index + 1)
            # Wait until the failed frame is consumed before submitting another.
            if index < 2:
                wait_until(lambda: any(r.event == "vision.failed" for r in caplog.records))
        wait_until(lambda: worker.processed_frames == 1)
        assert worker.is_running and worker.latest_result is result
    finally:
        worker.stop()
    emitted = records(caplog, "vision.perception")
    assert len([r for r in emitted if r["event"] == "vision.failed"]) == 1
    recovery = next(r for r in emitted if r["event"] == "vision.recovered")
    assert recovery["stage"] == stage
    assert all(r["operation_id"] == "vision-session" for r in emitted)


def test_stopping_worker_discards_inflight_result(caplog):
    caplog.set_level(logging.DEBUG)
    entered, release = threading.Event(), threading.Event()
    def detect(frame):
        entered.set()
        assert release.wait(2)
        return DetectionFrame(1, 1, 1, ())
    worker = PerceptionWorker(Mock(detect=detect))
    worker.start()
    worker.submit(CameraFrame(PRIVATE, 1, 1))
    assert entered.wait(1)
    stopper = threading.Thread(target=worker.stop)
    stopper.start()
    wait_until(lambda: not worker.is_running)
    release.set()
    stopper.join(2)
    assert not stopper.is_alive() and worker.latest_result is None
    emitted = records(caplog, "vision.perception")
    assert any(r["event"] == "vision.result_discarded" for r in emitted)


def test_worker_start_failure_does_not_claim_running(caplog):
    caplog.set_level(logging.DEBUG)
    worker = PerceptionWorker(Mock())
    with patch("controllers.computer_vision.perception_worker.threading.Thread.start",
               side_effect=OSError(PRIVATE)):
        with pytest.raises(OSError):
            worker.start()
    assert not worker.is_running
    assert any(r["stage"] == "start" for r in records(caplog, "vision.perception"))


@pytest.mark.parametrize("kind", ["ambient", "barometric"])
def test_sensor_failures_recover_and_successful_polling_stays_debug(caplog, kind):
    caplog.set_level(logging.DEBUG)
    source = Mock()
    if kind == "ambient":
        controller = AmbientLightController(source)
        source.get_illuminance_lux.side_effect = [OSError(PRIVATE), OSError(PRIVATE), 123.0, 123.0]
    else:
        controller = BarometricController(source)
        source.read_barometric.side_effect = [OSError(PRIVATE), OSError(PRIVATE),
                                             BarometricSample(101325), BarometricSample(101325)]
    controller.start()
    for _ in range(2):
        with pytest.raises(OSError):
            controller.read_state()
    with operation("sensor-read"):
        controller.read_state()
    controller.read_state()
    controller.stop()
    emitted = records(caplog, "environmental.")
    assert len([r for r in emitted if r["event"] == "sensor.failed"]) == 1
    recovery = next(r for r in emitted if r["event"] == "sensor.recovered")
    assert recovery["operation_id"] == "sensor-read"
    assert [r["state"] for r in emitted if r["event"] == "sensor.state_changed"] == ["started", "stopped"]
    assert not any("illuminance_lux" in r or "pressure_pa" in r for r in emitted)


def test_invalid_sensor_sample_is_logged_without_the_value(caplog):
    caplog.set_level(logging.DEBUG)
    source = Mock()
    source.get_illuminance_lux.return_value = float("nan")
    controller = AmbientLightController(source)
    with pytest.raises(RuntimeError):
        controller.read_state()
    failure = next(r for r in records(caplog, "environmental.") if r["event"] == "sensor.failed")
    assert failure["exception_type"] == "RuntimeError"
