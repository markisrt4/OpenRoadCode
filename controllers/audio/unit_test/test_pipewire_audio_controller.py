# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
import subprocess
from unittest.mock import call, patch

from controllers.audio import PipewireAudioController


class PipewireAudioControllerTest(unittest.TestCase):
    def test_set_volume_falls_back_to_pactl_when_wpctl_is_missing(self) -> None:
        controller = PipewireAudioController(steps=20)
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        with patch(
            "controllers.audio.pipewire_audio_controller.subprocess.run",
            side_effect=[FileNotFoundError(), completed],
        ) as run:
            level = controller.set_volume_level(13)

        self.assertEqual(13, level)
        self.assertEqual(
            [
                call(
                    ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.65"],
                    capture_output=True,
                    text=True,
                    check=True,
                ),
                call(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "65%"],
                    capture_output=True,
                    text=True,
                    check=True,
                ),
            ],
            run.call_args_list,
        )

    def test_get_volume_normalizes_pactl_output(self) -> None:
        controller = PipewireAudioController(steps=20)
        volume = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Volume: front-left: 42598 / 65% / -11.00 dB\n",
            stderr="",
        )
        mute = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Mute: no\n", stderr=""
        )

        with patch(
            "controllers.audio.pipewire_audio_controller.subprocess.run",
            side_effect=[FileNotFoundError(), volume, mute],
        ):
            level = controller.get_volume_level()

        self.assertEqual(13, level)

    def test_volume_up_limits_pipewire_to_one_hundred_percent(self) -> None:
        controller = PipewireAudioController(
            steps=20,
            step_percent=5,
        )

        with patch.object(
            controller,
            "_run_wpctl",
            side_effect=["", "Volume: 1.00"],
        ) as run_wpctl:
            level = controller.volume_up()

        self.assertEqual(20, level)
        self.assertEqual(
            [
                call(
                    [
                        "set-volume",
                        controller.DEFAULT_SINK,
                        "5%+",
                        "--limit",
                        "1.0",
                    ]
                ),
                call(
                    [
                        "get-volume",
                        controller.DEFAULT_SINK,
                    ],
                    capture=True,
                ),
            ],
            run_wpctl.call_args_list,
        )

    def test_toggle_mute_returns_resulting_state(self) -> None:
        controller = PipewireAudioController()

        with patch.object(
            controller,
            "_run_wpctl",
            side_effect=["", "Volume: 0.50 [MUTED]"],
        ) as run_wpctl:
            muted = controller.toggle_mute()

        self.assertTrue(muted)
        self.assertEqual(
            [
                call(
                    [
                        "set-mute",
                        controller.DEFAULT_SINK,
                        "toggle",
                    ]
                ),
                call(
                    [
                        "get-volume",
                        controller.DEFAULT_SINK,
                    ],
                    capture=True,
                ),
            ],
            run_wpctl.call_args_list,
        )

    def test_adjusts_multiple_cached_steps_with_one_command(self) -> None:
        controller = PipewireAudioController(
            steps=20,
            step_percent=5,
        )

        with patch.object(
            controller,
            "_run_wpctl",
            return_value="Volume: 0.50",
        ) as run_wpctl:
            self.assertEqual(10, controller.get_volume_level())
            run_wpctl.reset_mock()

            level = controller.adjust_volume(3)

        self.assertEqual(13, level)
        run_wpctl.assert_called_once_with(
            [
                "set-volume",
                controller.DEFAULT_SINK,
                "15%+",
                "--limit",
                str(controller.MAX_VOLUME),
            ]
        )


if __name__ == "__main__":
    unittest.main()
