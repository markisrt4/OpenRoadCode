"""Tests for Car UI background activity coordination."""

import unittest

from apps.carUi.car_ui_lifecycle import CarUiLifecycle


class RecordingRuntimeComponent:
    def __init__(self) -> None:
        self.starts = 0
        self.stops = 0

    def start(self) -> None:
        self.starts += 1

    def stop(self) -> None:
        self.stops += 1


class CarUiLifecycleTest(unittest.TestCase):
    def test_start_is_idempotent(self) -> None:
        gps = RecordingRuntimeComponent()
        encoders = RecordingRuntimeComponent()
        lifecycle = CarUiLifecycle(gps, encoders)  # type: ignore[arg-type]

        lifecycle.start()
        lifecycle.start()

        self.assertEqual(gps.starts, 1)
        self.assertEqual(encoders.starts, 1)

    def test_stop_cleans_up_both_components(self) -> None:
        gps = RecordingRuntimeComponent()
        encoders = RecordingRuntimeComponent()
        lifecycle = CarUiLifecycle(gps, encoders)  # type: ignore[arg-type]

        lifecycle.start()
        lifecycle.stop()

        self.assertEqual(gps.stops, 1)
        self.assertEqual(encoders.stops, 1)


if __name__ == "__main__":
    unittest.main()
