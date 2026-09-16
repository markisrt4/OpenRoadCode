# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Background latest-frame perception worker."""

from __future__ import annotations

import threading

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
        if self._tracker is not None:
            self._tracker.reset()
        self._running = True
        self._thread = threading.Thread(target=self._run, name="PerceptionWorker", daemon=True)
        self._thread.start()

    def submit(self, frame: CameraFrame) -> None:
        if not self._running:
            raise RuntimeError("Perception worker is not running")
        with self._condition:
            self._pending = frame
            self._condition.notify()

    def stop(self) -> None:
        if not self._running:
            return
        with self._condition:
            self._running = False
            self._condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._running and self._pending is None:
                    self._condition.wait()
                if not self._running:
                    return
                frame = self._pending
                self._pending = None

            assert frame is not None
            result = self._detector.detect(frame)
            tracks = self._tracker.update(result) if self._tracker is not None else None
            with self._condition:
                self._latest = result
                self._latest_tracks = tracks
                self._processed += 1
