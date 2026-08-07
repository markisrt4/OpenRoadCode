"""Tests for radio controller contracts and alternate implementations."""

from __future__ import annotations

import unittest

from controllers.radio import (
    RadioController,
    RadioControllerIf,
    RadioControllerStub,
    RadioMode,
    RadioPreset,
    UnconfiguredRadioController,
)


class RadioControllerContractTests(unittest.TestCase):
    def test_all_implementations_derive_from_interface(self) -> None:
        for controller_type in (
            RadioController,
            RadioControllerStub,
            UnconfiguredRadioController,
        ):
            with self.subTest(controller_type=controller_type):
                self.assertTrue(
                    issubclass(controller_type, RadioControllerIf)
                )
                self.assertFalse(controller_type.__abstractmethods__)


class RadioControllerStubTests(unittest.TestCase):
    def test_tracks_lifecycle_tuning_and_telemetry(self) -> None:
        controller = RadioControllerStub()

        self.assertEqual(controller.start(), 88_100_000)
        self.assertTrue(controller.is_started)
        self.assertTrue(controller.is_available)
        self.assertIsNone(controller.status_message)
        self.assertEqual(controller.frequency_up(), 88_200_000)
        self.assertEqual(controller.frequency_down(), 88_100_000)
        self.assertEqual(controller.get_signal_strength(), -42.0)
        self.assertEqual(controller.get_snr(), 30.0)
        self.assertEqual(controller.get_rds(), "OpenRoadCode")

        controller.stop()
        self.assertFalse(controller.is_started)

    def test_navigates_configured_presets(self) -> None:
        mode = RadioMode("NFM", bandwidth=12_500, step_hz=25_000)
        presets = (
            RadioPreset("First", 100_000_000, mode),
            RadioPreset("Second", 101_000_000, mode),
        )
        controller = RadioControllerStub(presets=presets)

        controller.start()

        self.assertEqual(controller.next_preset(), presets[1])
        self.assertEqual(controller.next_preset(), presets[0])
        self.assertEqual(controller.previous_preset(), presets[1])


class UnconfiguredRadioControllerTests(unittest.TestCase):
    def test_reports_unavailable_reason_and_presets(self) -> None:
        mode = RadioMode("WFM", bandwidth=180_000, step_hz=100_000)
        preset = RadioPreset("FM", 101_100_000, mode)
        controller = UnconfiguredRadioController(
            "SDR is disabled",
            presets=(preset,),
        )

        self.assertFalse(controller.is_available)
        self.assertFalse(controller.is_started)
        self.assertEqual(controller.status_message, "SDR is disabled")
        self.assertEqual(controller.presets, (preset,))

    def test_radio_operations_raise_reason(self) -> None:
        controller = UnconfiguredRadioController("SDR is disabled")
        mode = RadioMode("WFM", bandwidth=180_000, step_hz=100_000)
        preset = RadioPreset("FM", 101_100_000, mode)
        operations = (
            controller.start,
            controller.get_frequency,
            controller.refresh_frequency,
            lambda: controller.set_mode(mode),
            lambda: controller.tune_preset(preset),
            lambda: controller.tune_preset_index(0),
            controller.next_preset,
            controller.previous_preset,
            controller.next_station,
            controller.previous_station,
            controller.frequency_up,
            controller.frequency_down,
            lambda: controller.set_frequency(101_100_000),
            controller.get_signal_strength,
            controller.get_snr,
            controller.get_rds,
        )

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(RuntimeError, "SDR is disabled"):
                    operation()

        controller.stop()


if __name__ == "__main__":
    unittest.main()
