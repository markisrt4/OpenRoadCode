# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concurrency tests for safe OpenCV camera shutdown."""

from __future__ import annotations

import threading

from hardware_io.camera.v4l2_camera import V4L2Camera


class _BlockingCapture:
    def __init__(self) -> None:
        self.read_started = threading.Event()
        self.finish_read = threading.Event()
        self.released = threading.Event()

    def isOpened(self) -> bool:
        return not self.released.is_set()

    def read(self):
        self.read_started.set()
        self.finish_read.wait()
        assert not self.released.is_set()
        return True, object()

    def release(self) -> None:
        self.released.set()


def test_close_does_not_release_capture_during_native_read() -> None:
    camera = V4L2Camera()
    capture = _BlockingCapture()
    camera._capture = capture

    reader = threading.Thread(target=camera.read)
    reader.start()
    assert capture.read_started.wait(1.0)

    closed = threading.Event()
    closer = threading.Thread(target=lambda: (camera.close(), closed.set()))
    closer.start()
    assert not closed.wait(0.05)
    assert not capture.released.is_set()

    capture.finish_read.set()
    reader.join(1.0)
    closer.join(1.0)
    assert closed.is_set()
    assert capture.released.is_set()
