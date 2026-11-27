# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import sys
from unittest.mock import Mock, call

import pytest

from hardware_io.camera.v4l2_camera import V4L2Camera


@pytest.mark.parametrize("index_opens", [True, False])
def test_retries_numbered_device_by_index(monkeypatch, index_opens):
    cv2 = Mock()
    named_capture = Mock()
    named_capture.isOpened.return_value = False
    indexed_capture = Mock()
    indexed_capture.isOpened.return_value = index_opens
    cv2.VideoCapture.side_effect = [named_capture, indexed_capture]
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    camera = V4L2Camera("/dev/video2")
    if index_opens:
        camera.open()
        assert camera.is_open
        indexed_capture.set.assert_called()
        camera.close()
    else:
        with pytest.raises(RuntimeError, match="/dev/video2"):
            camera.open()
        assert not camera.is_open
        indexed_capture.set.assert_not_called()

    assert cv2.VideoCapture.call_args_list == [
        call("/dev/video2", cv2.CAP_V4L2),
        call(2, cv2.CAP_V4L2),
    ]
    named_capture.release.assert_called_once()
    indexed_capture.release.assert_called_once()


@pytest.mark.parametrize("device", ["/dev/video0", "/dev/v4l/by-id/camera"])
def test_successful_named_open_uses_the_requested_path(monkeypatch, device):
    cv2 = Mock()
    cv2.VideoCapture.return_value.isOpened.return_value = True
    monkeypatch.setitem(sys.modules, "cv2", cv2)

    camera = V4L2Camera(device)
    camera.open()
    cv2.VideoCapture.assert_called_once_with(device, cv2.CAP_V4L2)
    camera.close()
