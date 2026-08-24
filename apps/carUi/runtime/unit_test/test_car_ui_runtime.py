# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for resources owned by the assembled Car UI runtime."""

import unittest

from apps.carUi.runtime.car_ui_runtime import CarUiRuntime, RadioRuntime
from apps.carUi.runtime.radio_runtime_registry import RadioRuntimeRegistry


class RecordingRadioController:
    def __init__(self, fail: bool = False) -> None:
        self.stops = 0
        self.fail = fail

    def stop(self) -> None:
        self.stops += 1
        if self.fail:
            raise RuntimeError("radio stop failed")


class CarUiRuntimeTest(unittest.TestCase):
    def test_close_stops_every_radio_controller(self) -> None:
        first = RecordingRadioController()
        second = RecordingRadioController()
        runtime = self._runtime(first, second)

        runtime.close()

        self.assertEqual(first.stops, 1)
        self.assertEqual(second.stops, 1)

    def test_close_continues_after_radio_failure(self) -> None:
        first = RecordingRadioController(fail=True)
        second = RecordingRadioController()
        runtime = self._runtime(first, second)

        with self.assertLogs(
            "apps.carUi.runtime.car_ui_runtime", level="ERROR"
        ):
            runtime.close()

        self.assertEqual(second.stops, 1)

    @staticmethod
    def _runtime(*controllers) -> CarUiRuntime:
        radio_runtimes = {
            f"radio-{index}": RadioRuntime(
                key=f"radio-{index}",
                config=object(),
                controller=controller,  # type: ignore[arg-type]
                launcher=object(),  # type: ignore[arg-type]
            )
            for index, controller in enumerate(controllers)
        }
        return CarUiRuntime(
            remote_display=":2",
            auxiliary_display=":0",
            rotary_encoders=object(),  # type: ignore[arg-type]
            radios=RadioRuntimeRegistry(radio_runtimes),
            adsb_launcher=None,
            weather_controller=None,
            sdr_resource_manager=object(),
        )


if __name__ == "__main__":
    unittest.main()
