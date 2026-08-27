# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Car UI background activity coordination."""

import unittest

from apps.carUi.car_ui_lifecycle import CarUiLifecycle


class RecordingInputRuntime:
    def __init__(self) -> None:
        self.starts = 0
        self.stops = 0

    def start(self) -> None:
        self.starts += 1

    def stop(self) -> None:
        self.stops += 1


class RecordingMessageDispatcher:
    def __init__(self) -> None:
        self.starts = 0
        self.closes = 0

    def start(self) -> None:
        self.starts += 1

    def close(self) -> None:
        self.closes += 1


class CarUiLifecycleTest(unittest.TestCase):
    def test_start_is_idempotent(self) -> None:
        input_runtime = RecordingInputRuntime()
        dispatcher = RecordingMessageDispatcher()
        lifecycle = CarUiLifecycle(input_runtime, dispatcher)  # type: ignore[arg-type]

        lifecycle.start()
        lifecycle.start()

        self.assertEqual(input_runtime.starts, 1)
        self.assertEqual(dispatcher.starts, 1)

    def test_stop_cleans_up_both_components(self) -> None:
        input_runtime = RecordingInputRuntime()
        dispatcher = RecordingMessageDispatcher()
        lifecycle = CarUiLifecycle(input_runtime, dispatcher)  # type: ignore[arg-type]

        lifecycle.start()
        lifecycle.stop()

        self.assertEqual(input_runtime.stops, 1)
        self.assertEqual(dispatcher.closes, 1)


if __name__ == "__main__":
    unittest.main()
