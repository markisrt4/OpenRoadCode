from __future__ import annotations

import unittest

from controllers.lighting import (
    CustomPatternMode,
    DummyLightingController,
    LightingState,
    RgbColor,
)


class DummyLightingControllerTest(unittest.TestCase):
    def test_commands_update_state(self) -> None:
        controller = DummyLightingController()

        controller.connect().result()
        controller.set_power(True).result()
        controller.set_color(RgbColor(10, 20, 30)).result()
        controller.set_brightness(75).result()
        controller.set_color_temperature(60).result()
        controller.set_pattern(23).result()
        controller.set_music_mode(2).result()
        controller.set_custom_pattern_mode(
            CustomPatternMode.FLOW
        ).result()
        controller.set_custom_pattern_direction(False).result()

        self.assertEqual(
            LightingState(
                connected=True,
                power_enabled=True,
                color=RgbColor(10, 20, 30),
                brightness_percent=75,
                color_temperature_percent=60,
                pattern_index=23,
                music_mode=2,
                custom_pattern_mode=CustomPatternMode.FLOW,
                custom_pattern_forward=False,
            ),
            controller.current_state(),
        )

    def test_close_rejects_future_commands(self) -> None:
        controller = DummyLightingController()
        controller.close()

        with self.assertRaisesRegex(RuntimeError, "closed"):
            controller.set_power(True).result()

    def test_invalid_values_are_rejected(self) -> None:
        controller = DummyLightingController()

        with self.assertRaises(ValueError):
            controller.set_brightness(101)

        with self.assertRaises(ValueError):
            controller.set_pattern(-1)


if __name__ == "__main__":
    unittest.main()
