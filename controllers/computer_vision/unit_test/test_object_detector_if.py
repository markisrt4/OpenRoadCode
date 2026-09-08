# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.computer_vision.object_detector_if import Detection, DetectionFrame


class DetectionTest(unittest.TestCase):
    def test_accepts_normalized_detection(self) -> None:
        detection = Detection(
            label="car",
            confidence=0.92,
            x=0.10,
            y=0.20,
            width=0.30,
            height=0.40,
        )

        frame = DetectionFrame(
            timestamp_s=12.5,
            sequence=7,
            inference_time_ms=18.4,
            detections=(detection,),
        )

        self.assertEqual(frame.sequence, 7)
        self.assertEqual(frame.detections[0].label, "car")
        self.assertEqual(frame.inference_time_ms, 18.4)

    def test_rejects_invalid_confidence(self) -> None:
        with self.assertRaises(ValueError):
            Detection("car", 1.1, 0.1, 0.1, 0.2, 0.2)

    def test_rejects_non_normalized_box(self) -> None:
        with self.assertRaises(ValueError):
            Detection("car", 0.9, 0.1, 0.1, 1.2, 0.2)

    def test_rejects_negative_inference_time(self) -> None:
        with self.assertRaises(ValueError):
            DetectionFrame(1.0, 1, -1.0, ())


if __name__ == "__main__":
    unittest.main()
