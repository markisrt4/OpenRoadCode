# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.computer_vision.object_tracker_if import ObjectTrack, TrackFrame


class ObjectTrackerContractTest(unittest.TestCase):
    def test_track_preserves_normalized_geometry_and_identity(self) -> None:
        track = ObjectTrack(
            track_id=7,
            label="car",
            confidence=0.91,
            x=0.2,
            y=0.3,
            width=0.4,
            height=0.2,
            age_s=3.5,
        )
        frame = TrackFrame(timestamp_s=10.0, sequence=42, tracks=(track,))
        self.assertEqual(frame.tracks[0].track_id, 7)
        self.assertEqual(frame.tracks[0].label, "car")
        self.assertEqual(frame.sequence, 42)

    def test_track_rejects_invalid_geometry(self) -> None:
        with self.assertRaises(ValueError):
            ObjectTrack(
                track_id=1,
                label="car",
                confidence=0.9,
                x=1.1,
                y=0.0,
                width=0.2,
                height=0.2,
                age_s=0.0,
            )

    def test_track_rejects_negative_age(self) -> None:
        with self.assertRaises(ValueError):
            ObjectTrack(
                track_id=1,
                label="car",
                confidence=0.9,
                x=0.1,
                y=0.1,
                width=0.2,
                height=0.2,
                age_s=-0.1,
            )


if __name__ == "__main__":
    unittest.main()
