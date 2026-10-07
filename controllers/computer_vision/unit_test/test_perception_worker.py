# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import time
import threading
import unittest

from controllers.computer_vision.object_detector_if import DetectionFrame, ObjectDetectorIf
from controllers.computer_vision.perception_worker import PerceptionWorker
from hardware_io.camera.camera_if import CameraFrame


class _FakeDetector(ObjectDetectorIf):
    def detect(self, frame: CameraFrame) -> DetectionFrame:
        return DetectionFrame(
            timestamp_s=frame.timestamp_s,
            sequence=frame.sequence,
            inference_time_ms=1.0,
            detections=(),
        )


class _BlockingDetector(ObjectDetectorIf):
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def detect(self, frame: CameraFrame) -> DetectionFrame:
        self.started.set()
        self.release.wait()
        return DetectionFrame(frame.timestamp_s, frame.sequence, 1.0, ())


class PerceptionWorkerTest(unittest.TestCase):
    def test_processes_submitted_frame(self) -> None:
        worker = PerceptionWorker(_FakeDetector())
        worker.start()
        try:
            worker.submit(CameraFrame(image=None, timestamp_s=2.0, sequence=9))
            deadline = time.monotonic() + 1.0
            while worker.latest_result is None and time.monotonic() < deadline:
                time.sleep(0.01)

            self.assertIsNotNone(worker.latest_result)
            assert worker.latest_result is not None
            self.assertEqual(worker.latest_result.sequence, 9)
            self.assertEqual(worker.processed_frames, 1)
        finally:
            worker.stop()

    def test_stop_waits_for_native_inference_to_finish(self) -> None:
        detector = _BlockingDetector()
        worker = PerceptionWorker(detector)
        worker.start()
        worker.submit(CameraFrame(image=None, timestamp_s=2.0, sequence=9))
        self.assertTrue(detector.started.wait(1.0))

        stopped = threading.Event()
        thread = threading.Thread(target=lambda: (worker.stop(), stopped.set()))
        thread.start()
        self.assertFalse(stopped.wait(0.05))

        detector.release.set()
        self.assertTrue(stopped.wait(1.0))
        thread.join()


if __name__ == "__main__":
    unittest.main()
