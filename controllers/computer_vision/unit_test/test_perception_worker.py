# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import time
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


if __name__ == "__main__":
    unittest.main()
