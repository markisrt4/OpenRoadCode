# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Drain a live camera independently of downstream image processing."""

from threading import Condition, Event, Thread

from hardware_io.camera.camera_if import CameraFrame, CameraIf


class LatestFrameCamera(CameraIf):
    """Keep one unread frame, replacing it when a newer frame arrives.

    The wrapped camera must support close during a bounded read. Only the reader
    thread decodes; consumers wait for a new frame without replaying old pixels.
    """

    def __init__(self, source: CameraIf) -> None:
        self._source = source
        self._condition = Condition()
        self._closing = Event()
        self._closing.set()
        self._thread: Thread | None = None
        self._latest: CameraFrame | None = None
        self._error: Exception | None = None

    @property
    def is_open(self) -> bool:
        with self._condition:
            return self._thread is not None and not self._closing.is_set() and self._error is None

    def open(self) -> None:
        with self._condition:
            if self.is_open:
                return
            if self._thread is not None:
                raise RuntimeError("Close the previous camera session before reopening")
            self._closing.clear()
            self._latest = None
            self._error = None
            self._source.open()
            if self._closing.is_set():
                raise RuntimeError("Camera startup was cancelled")
            thread = Thread(target=self._drain, name="BridgeFrameReader", daemon=True)
            self._thread = thread
            try:
                thread.start()
            except Exception:
                self._thread = None
                self._source.close()
                raise

    def _drain(self) -> None:
        try:
            while not self._closing.is_set():
                frame = self._source.read()
                with self._condition:
                    if self._closing.is_set():
                        return
                    self._latest = frame
                    self._condition.notify_all()
        except Exception as error:
            with self._condition:
                self._error = error
                self._condition.notify_all()

    def read(self) -> CameraFrame:
        with self._condition:
            self._condition.wait_for(lambda: self._closing.is_set() or self._error is not None
                                     or self._latest is not None or self._thread is None)
            if self._closing.is_set() or self._thread is None:
                raise RuntimeError("Camera read was cancelled")
            if self._error is not None:
                raise RuntimeError(str(self._error)) from self._error
            frame, self._latest = self._latest, None
            assert frame is not None
            return frame

    def close(self) -> None:
        self._closing.set()
        # AndroidBridgeCamera serializes native release against its bounded read.
        self._source.close()
        with self._condition:
            thread = self._thread
            self._latest = None
            self._condition.notify_all()
        if thread is not None:
            thread.join(timeout=2.0)
            if thread.is_alive():
                raise RuntimeError("Camera reader did not stop")
        with self._condition:
            self._thread = None
