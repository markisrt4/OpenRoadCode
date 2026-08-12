# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for platform-specific audio runtime composition."""

import unittest

from apps.carUi.runtime.audio_runtime_factory import (
    _match_wpctl_sink,
    _resolve_output,
    create_audio_controller,
)
from config.runtime_target import RuntimeTarget
from controllers.audio import PactlAudioController, PipewireAudioController


class AudioRuntimeFactoryTest(unittest.TestCase):
    def test_auto_output_follows_pi_hardware(self) -> None:
        self.assertEqual(
            "onboard-analog", _resolve_output("auto", RuntimeTarget.RPI4)
        )
        self.assertEqual("usb", _resolve_output("auto", RuntimeTarget.RPI5))

    def test_wpctl_sink_is_matched_by_stable_description(self) -> None:
        status = """
        Sinks:
         * 42. alsa_output.platform-bcm2835_audio.analog-stereo
           57. alsa_output.usb-C-Media_USB_Audio-00.analog-stereo
        """
        self.assertEqual("42", _match_wpctl_sink(status, "onboard-analog", None))
        self.assertEqual("57", _match_wpctl_sink(status, "usb", None))

    def test_linux_dev_uses_pactl(self) -> None:
        self.assertIsInstance(
            create_audio_controller(target=RuntimeTarget.LINUX_DEV),
            PactlAudioController,
        )

    def test_raspberry_pi_uses_wpctl(self) -> None:
        for target in (RuntimeTarget.RPI4, RuntimeTarget.RPI5):
            with self.subTest(target=target):
                self.assertIsInstance(
                    create_audio_controller(target=target),
                    PipewireAudioController,
                )


if __name__ == "__main__":
    unittest.main()
