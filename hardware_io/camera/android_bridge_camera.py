# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Decode the Android bridge's H.264/MPEG-TS stream behind CameraIf."""

import json
from threading import Event, RLock
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from hardware_io.camera.camera_if import CameraFrame, CameraIf


class AndroidBridgeCamera(CameraIf):
    """Use the existing OpenCV FFmpeg backend, with bounded open/read operations.

    Frames are BGR arrays, matching V4L2Camera. Timestamps mark decoder delivery
    on the local monotonic clock, not Android sensor exposure or MPEG-TS PTS.
    Closing can wait for at most the configured in-flight OpenCV operation; it
    never releases a native capture concurrently with read().
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8767", *,
                 open_timeout_ms: int = 1500, read_timeout_ms: int = 500) -> None:
        parsed = urlsplit(base_url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.username or parsed.password):
            raise ValueError("Bridge camera URL must be an HTTP(S) service base URL")
        # Validate a supplied port before it is handed to the native decoder.
        parsed.port
        if not 0 < open_timeout_ms <= 1500 or not 0 < read_timeout_ms <= 500:
            raise ValueError("Camera timeouts must be bounded: open <=1500 ms, read <=500 ms")
        self._base_url = base_url.rstrip("/")
        self._open_timeout_ms = open_timeout_ms
        self._read_timeout_ms = read_timeout_ms
        self._lock = RLock()
        self._closing = Event()
        self._capture: Any | None = None
        self._sequence = 0

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._capture is not None and bool(self._capture.isOpened())

    def open(self) -> None:
        with self._lock:
            if self.is_open:
                return
            self._closing.clear()
            self.check_status()
            if self._closing.is_set():
                raise RuntimeError("Bridge camera startup was cancelled")
            try:
                import cv2
            except ModuleNotFoundError as exc:
                raise RuntimeError("OpenCV with FFmpeg support is required for the Android camera") from exc
            except (ImportError, OSError) as exc:
                raise RuntimeError(
                    "OpenCV is installed but its native libraries cannot load. "
                    "On Termux, update and reinstall matching OpenCV/libprotobuf packages."
                ) from exc
            registry = getattr(cv2, "videoio_registry", None)
            if (registry is None or not hasattr(registry, "hasBackend")
                    or not registry.hasBackend(cv2.CAP_FFMPEG)
                    or not hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC")
                    or not hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC")):
                raise RuntimeError("This OpenCV build needs an FFmpeg backend with stream timeout support")
            try:
                capture = cv2.VideoCapture(self._base_url + "/video", cv2.CAP_FFMPEG, [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self._open_timeout_ms,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC, self._read_timeout_ms,
                ])
            except (cv2.error, TypeError) as exc:
                raise RuntimeError("OpenCV could not create the bounded Android video decoder") from exc
            if self._closing.is_set() or not capture.isOpened():
                capture.release()
                raise RuntimeError("Cannot decode Android video; check the bridge camera and FFmpeg support")
            self._capture = capture
            self._sequence = 0

    def check_status(self) -> None:
        """Verify the actual listener and stream format without taking the video client slot."""
        try:
            with urlopen(self._base_url + "/status", timeout=0.5) as response:
                status = json.load(response)
        except (URLError, OSError, ValueError) as exc:
            raise RuntimeError("Android camera bridge unavailable; enable Camera streaming in Bridge") from exc
        if not isinstance(status, dict) or status.get("state") != "streaming":
            raise RuntimeError("Android camera is not streaming; start Camera in Bridge and allow camera access")
        if status.get("codec") != "h264" or status.get("container") != "mpegts":
            raise RuntimeError("Android camera must provide H.264 video in MPEG-TS")

    def read(self) -> CameraFrame:
        with self._lock:
            capture = self._capture
            if self._closing.is_set() or capture is None or not capture.isOpened():
                raise RuntimeError("Bridge camera is not open")
            ok, image = capture.read()
            if self._closing.is_set():
                raise RuntimeError("Bridge camera read was cancelled")
            if not ok or image is None:
                raise RuntimeError("Android camera stream stopped or timed out; reopen Vision to reconnect")
            frame = CameraFrame(image, time.monotonic(), self._sequence)
            self._sequence += 1
            return frame

    def close(self) -> None:
        self._closing.set()
        with self._lock:
            capture, self._capture = self._capture, None
            if capture is not None:
                capture.release()
