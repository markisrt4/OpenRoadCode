from __future__ import annotations

import unittest
from unittest.mock import call, patch

from controllers.audio import PipewireAudioController


class PipewireAudioControllerTest(unittest.TestCase):
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
