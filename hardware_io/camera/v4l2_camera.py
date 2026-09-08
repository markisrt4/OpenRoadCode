# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Linux V4L2 camera source implemented with OpenCV."""

from __future__ import annotations

import time
from typing import Any

from hardware_io.camera.camera_if import CameraFrame, CameraIf


class V4L2Camera(CameraIf):
    """Capture frames from a Linux V4L2 camera device.

    OpenCV is imported lazily so simply importing OpenRoadCode does not make
    camera support a mandatory dependency on systems that do not use it.
    """

    def __init__(
        self,
        device: str = "/dev/video0",
        *,
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
        pixel_format: str = "MJPG",
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        if fps <= 0:
            raise ValueError("fps must be positive")
        if len(pixel_format) != 4:
            raise ValueError("pixel_format must be a four-character code")

        self._device = device
        self._width = width
        self._height = height
        self._fps = float(fps)
        self._pixel_format = pixel_format
        self._capture: Any | None = None
        self._cv2: Any | None = None
        self._sequence = 0

    @property
    def is_open(self) -> bool:
        return self._capture is not None and bool(self._capture.isOpened())

    @property
    def device(self) -> str:
        return self._device

    def open(self) -> None:
        if self.is_open:
            return

        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "OpenCV is required for V4L2Camera; install python3-opencv "
                "or the project's camera development dependency"
            ) from exc

        capture = cv2.VideoCapture(self._device, cv2.CAP_V4L2)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Unable to open camera device {self._device}")

        fourcc = cv2.VideoWriter_fourcc(*self._pixel_format)
        capture.set(cv2.CAP_PROP_FOURCC, fourcc)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        capture.set(cv2.CAP_PROP_FPS, self._fps)

        self._cv2 = cv2
        self._capture = capture
        self._sequence = 0

    def read(self) -> CameraFrame:
        if not self.is_open:
            raise RuntimeError("Camera is not open")

        ok, image = self._capture.read()
        if not ok or image is None:
            raise RuntimeError(f"Failed to capture frame from {self._device}")

        frame = CameraFrame(
            image=image,
            timestamp_s=time.monotonic(),
            sequence=self._sequence,
        )
        self._sequence += 1
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self._cv2 = None
