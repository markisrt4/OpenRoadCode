# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Background latest-frame perception worker."""

from __future__ import annotations

import threading
import logging

from common.logging.diagnostics import ComponentLog
from common.logging.structured import operation

from controllers.computer_vision.object_detector_if import DetectionFrame, ObjectDetectorIf
from controllers.computer_vision.object_tracker_if import ObjectTrackerIf, TrackFrame
from hardware_io.camera.camera_if import CameraFrame


class PerceptionWorker:
    """Run detection/tracking off the capture thread while dropping stale frames."""

    def __init__(
        self,
        detector: ObjectDetectorIf,
        tracker: ObjectTrackerIf | None = None,
    ) -> None:
        self._diagnostics = ComponentLog("vision.perception", "vision")
        self._generation = 0
        self._operation_id = None
        self._detector = detector
        self._tracker = tracker
        self._condition = threading.Condition()
        self._pending: CameraFrame | None = None
        self._latest: DetectionFrame | None = None
        self._latest_tracks: TrackFrame | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._processed = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def processed_frames(self) -> int:
        return self._processed

    @property
    def latest_result(self) -> DetectionFrame | None:
        with self._condition:
            return self._latest

    @property
    def latest_tracks(self) -> TrackFrame | None:
        with self._condition:
            return self._latest_tracks

    def start(self) -> None:
        if self._running:
            return
        with self._diagnostics.action("start") as operation_id:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("Previous perception worker is still stopping")
            if self._tracker is not None:
                with self._diagnostics.action("tracker_reset"):
                    self._tracker.reset()
            with self._condition:
                self._generation += 1
                generation = self._generation
                self._operation_id = operation_id
                self._pending = None
                self._latest = None
                self._latest_tracks = None
                self._processed = 0
                self._running = True
            self._thread = threading.Thread(
                target=self._run, args=(generation, operation_id),
                name="PerceptionWorker", daemon=True,
            )
            try:
                self._thread.start()
            except Exception:
                with self._condition:
                    self._running = False
                self._thread = None
                raise
            self._diagnostics.changed("lifecycle", "running")

    def submit(self, frame: CameraFrame) -> None:
        if not self._running:
            raise RuntimeError("Perception worker is not running")
        with self._condition:
            if self._pending is not None:
                self._diagnostics.emit(logging.DEBUG, "frame_replaced", self._operation_id)
            self._pending = frame
            self._condition.notify()

    def stop(self) -> None:
        if not self._running:
            return
        with self._condition:
            self._running = False
            self._generation += 1
            self._pending = None
            self._condition.notify_all()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        if thread is not None and thread.is_alive():
            self._diagnostics.failed("stop", operation_id=self._operation_id,
                                     reason="timeout")
        else:
            self._thread = None
            self._diagnostics.succeeded("stop", self._operation_id)
        self._diagnostics.changed("lifecycle", "stopped", self._operation_id)

    def _run(self, generation: int, operation_id: str) -> None:
        with operation(operation_id):
            self._process_pending(generation)

    def _process_pending(self, generation: int) -> None:
        while True:
            with self._condition:
                while self._running and generation == self._generation and self._pending is None:
                    self._condition.wait()
                if not self._running or generation != self._generation:
                    return
                frame = self._pending
                self._pending = None

            assert frame is not None
            try:
                with self._diagnostics.action("inference"):
                    result = self._detector.detect(frame)
                with self._diagnostics.action("tracking"):
                    tracks = self._tracker.update(result) if self._tracker is not None else None
            except Exception:
                # A bad frame/provider must not silently kill the background worker.
                with self._condition:
                    if generation == self._generation:
                        self._latest = None
                        self._latest_tracks = None
                continue
            with self._condition:
                if not self._running or generation != self._generation:
                    self._diagnostics.emit(logging.DEBUG, "result_discarded")
                    return
                self._latest = result
                self._latest_tracks = tracks
                self._processed += 1
