# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Bridge decoder framing, timeouts, cancellation and release ownership."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
import threading

import numpy as np
import pytest

from hardware_io.camera.android_bridge_camera import AndroidBridgeCamera
from hardware_io.camera.software_camera_controls import SoftwareCameraControls
from hardware_io.camera.camera_controls_if import CameraProfile


def decoder(monkeypatch):
    capture = Mock()
    capture.isOpened.return_value = True
    image = np.zeros((2, 3, 3), dtype=np.uint8)
    capture.read.return_value = (True, image)
    cv2 = SimpleNamespace(
        __version__='4.10.0',
        CAP_FFMPEG=1900, CAP_PROP_OPEN_TIMEOUT_MSEC=53, CAP_PROP_READ_TIMEOUT_MSEC=54,
        videoio_registry=SimpleNamespace(hasBackend=lambda backend: True),
        VideoCapture=Mock(return_value=capture), error=RuntimeError,
    )
    monkeypatch.setitem(__import__('sys').modules, 'cv2', cv2)
    monkeypatch.setattr('hardware_io.camera.android_bridge_camera.urlopen',
                        lambda *args, **kwargs: BytesIO(
                            b'{"state":"streaming","codec":"h264","container":"mpegts"}'))
    return cv2, capture, image


def test_decoded_frames_have_monotonic_receipt_times_and_session_sequence(monkeypatch):
    cv2, capture, image = decoder(monkeypatch)
    camera = AndroidBridgeCamera()
    camera.open()
    cv2.VideoCapture.assert_called_once_with('http://127.0.0.1:8767/video', 1900,
                                            [53, 1500, 54, 500])
    first, second = camera.read(), camera.read()
    assert first.image is image and second.image is image
    assert (first.sequence, second.sequence) == (0, 1)
    assert second.timestamp_s >= first.timestamp_s
    camera.close()
    camera.close()
    capture.release.assert_called_once()
    assert not camera.is_open
    camera.open()
    assert camera.read().sequence == 0
    camera.close()


def test_bridge_must_be_streaming_before_decoder_is_started(monkeypatch):
    cv2, _, _ = decoder(monkeypatch)
    monkeypatch.setattr('hardware_io.camera.android_bridge_camera.urlopen',
                        lambda *args, **kwargs: BytesIO(b'{"state":"stopped"}'))
    with pytest.raises(RuntimeError, match='start Camera'):
        AndroidBridgeCamera().open()
    cv2.VideoCapture.assert_not_called()


def test_wrong_service_or_transport_is_rejected(monkeypatch):
    cv2, _, _ = decoder(monkeypatch)
    monkeypatch.setattr('hardware_io.camera.android_bridge_camera.urlopen',
                        lambda *args, **kwargs: BytesIO(
                            b'{"state":"streaming","codec":"mjpeg","container":"jpeg"}'))
    with pytest.raises(RuntimeError, match='H.264'):
        AndroidBridgeCamera().open()
    cv2.VideoCapture.assert_not_called()


def test_missing_ffmpeg_backend_has_an_actionable_error(monkeypatch):
    cv2, _, _ = decoder(monkeypatch)
    cv2.videoio_registry.hasBackend = lambda backend: False
    with pytest.raises(RuntimeError, match='FFmpeg backend'):
        AndroidBridgeCamera().open()
    cv2.VideoCapture.assert_not_called()


def test_failed_open_releases_native_capture_and_failed_read_never_returns_old_image(monkeypatch):
    _, capture, _ = decoder(monkeypatch)
    camera = AndroidBridgeCamera()
    capture.isOpened.return_value = False
    with pytest.raises(RuntimeError, match='Cannot decode'):
        camera.open()
    capture.release.assert_called_once()
    capture.isOpened.return_value = True
    camera.open()
    capture.read.return_value = (False, None)
    with pytest.raises(RuntimeError, match='reopen Vision'):
        camera.read()
    camera.close()


def test_close_during_read_discards_completion_and_never_releases_concurrently(monkeypatch):
    _, capture, image = decoder(monkeypatch)
    camera = AndroidBridgeCamera()
    camera.open()
    started, finish = threading.Event(), threading.Event()
    def read():
        started.set()
        assert finish.wait(1)
        capture.release.assert_not_called()
        return True, image
    capture.read.side_effect = read
    errors = []
    def reader():
        try:
            camera.read()
        except RuntimeError as error:
            errors.append(str(error))
    reading = threading.Thread(target=reader)
    reading.start()
    assert started.wait(1)
    closing = threading.Thread(target=camera.close)
    closing.start()
    assert camera._closing.wait(1)
    finish.set()
    reading.join(1)
    closing.join(1)
    assert not reading.is_alive() and not closing.is_alive()
    assert errors == ['Bridge camera read was cancelled']
    capture.release.assert_called_once()


def test_close_during_open_cancels_and_releases_the_unowned_decoder(monkeypatch):
    cv2, capture, _ = decoder(monkeypatch)
    camera = AndroidBridgeCamera()
    entered, finish = threading.Event(), threading.Event()
    def opening(*args):
        entered.set()
        assert finish.wait(1)
        return capture
    cv2.VideoCapture.side_effect = opening
    errors = []
    def opener():
        try:
            camera.open()
        except RuntimeError as error:
            errors.append(str(error))
    opening_thread = threading.Thread(target=opener)
    opening_thread.start()
    assert entered.wait(1)
    closing = threading.Thread(target=camera.close)
    closing.start()
    assert camera._closing.wait(1)
    finish.set()
    opening_thread.join(1)
    closing.join(1)
    assert errors and not camera.is_open
    capture.release.assert_called_once()


def test_software_profiles_do_not_issue_android_exposure_commands():
    controls = SoftwareCameraControls()
    controls.apply(CameraProfile.LOW_LIGHT)
    assert controls.current_profile == CameraProfile.LOW_LIGHT
    controls.invalidate()
    assert controls.current_profile is None
    controls.restore_day_defaults()
    assert controls.current_profile == CameraProfile.DAY


def test_read_only_diagnostic_never_takes_the_video_client_slot(monkeypatch):
    cv2, _, _ = decoder(monkeypatch)
    monkeypatch.setattr(__import__('sys'), 'argv', ['bridge-check', '--check-only'])
    from hardware_io.camera.component_test.android_bridge_camera_cli import main
    assert main() == 0
    cv2.VideoCapture.assert_not_called()
