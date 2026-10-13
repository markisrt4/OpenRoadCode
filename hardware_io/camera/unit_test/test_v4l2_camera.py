# SPDX-License-Identifier: MIT
"""Verify OpenCV/V4L2 device selection without camera hardware."""

import sys
from unittest.mock import Mock, patch

from hardware_io.camera.v4l2_camera import V4L2Camera


def test_linux_video_device_path_uses_opencv_numeric_v4l2_index():
    cv2 = Mock()
    cv2.CAP_V4L2 = 200
    cv2.CAP_PROP_FOURCC = 6
    cv2.CAP_PROP_FRAME_WIDTH = 3
    cv2.CAP_PROP_FRAME_HEIGHT = 4
    cv2.CAP_PROP_FPS = 5
    cv2.VideoWriter_fourcc.return_value = 1234
    cv2.VideoCapture.return_value.isOpened.return_value = True
    camera = V4L2Camera("/dev/video12")

    with patch.dict(sys.modules, {"cv2": cv2}):
        camera.open()

    cv2.VideoCapture.assert_called_once_with(12, cv2.CAP_V4L2)


def test_non_device_name_remains_available_for_custom_opencv_sources():
    cv2 = Mock()
    cv2.CAP_V4L2 = 200
    cv2.CAP_PROP_FOURCC = 6
    cv2.CAP_PROP_FRAME_WIDTH = 3
    cv2.CAP_PROP_FRAME_HEIGHT = 4
    cv2.CAP_PROP_FPS = 5
    cv2.VideoWriter_fourcc.return_value = 1234
    cv2.VideoCapture.return_value.isOpened.return_value = True
    camera = V4L2Camera("camera-alias")

    with patch.dict(sys.modules, {"cv2": cv2}):
        camera.open()

    cv2.VideoCapture.assert_called_once_with("camera-alias", cv2.CAP_V4L2)
