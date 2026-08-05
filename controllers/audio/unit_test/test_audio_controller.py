"""Tests for alternate audio controller implementations."""

from __future__ import annotations

import unittest

from controllers.audio import (
    AudioControllerIf,
    AudioControllerStub,
    PipewireAudioController,
    UnconfiguredAudioController,
)


class AudioControllerContractTests(unittest.TestCase):
    def test_all_implementations_derive_from_interface(self) -> None:
        for controller_type in (
            PipewireAudioController,
            AudioControllerStub,
            UnconfiguredAudioController,
        ):
            with self.subTest(controller_type=controller_type):
                self.assertTrue(
                    issubclass(controller_type, AudioControllerIf)
                )

    def test_pipewire_controller_reports_available(self) -> None:
        controller = PipewireAudioController()

        self.assertTrue(controller.is_available)
        self.assertIsNone(controller.status_message)


class AudioControllerStubTests(unittest.TestCase):
    def test_tracks_volume_and_mute_state(self) -> None:
        controller = AudioControllerStub(
            maximum_level=10,
            initial_level=5,
        )

        self.assertEqual(controller.volume_up(), 6)
        self.assertEqual(controller.volume_down(), 5)
        self.assertTrue(controller.toggle_mute())
        self.assertTrue(controller.is_muted())
        self.assertTrue(controller.is_available)

    def test_clamps_volume_to_supported_range(self) -> None:
        controller = AudioControllerStub(maximum_level=10)

        self.assertEqual(controller.set_volume_level(20), 10)
        self.assertEqual(controller.adjust_volume(-20), 0)


class UnconfiguredAudioControllerTests(unittest.TestCase):
    def test_reports_unavailable_reason(self) -> None:
        controller = UnconfiguredAudioController("PipeWire disabled")

        self.assertFalse(controller.is_available)
        self.assertEqual(controller.status_message, "PipeWire disabled")
        self.assertEqual(controller.maximum_level, 20)

    def test_audio_operations_raise_reason(self) -> None:
        controller = UnconfiguredAudioController("PipeWire disabled")

        operations = (
            controller.volume_up,
            controller.volume_down,
            controller.get_volume_level,
            lambda: controller.set_volume_level(5),
            controller.is_muted,
            controller.toggle_mute,
        )
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "PipeWire disabled",
                ):
                    operation()


if __name__ == "__main__":
    unittest.main()
