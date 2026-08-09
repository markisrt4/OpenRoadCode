"""Tests for mapping physical input into semantic UI actions."""

import unittest

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
)
from controllers.input import InputMapper
from ui.ui_action import UiAction


class InputMapperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.primary_encoder = InputDeviceId(InputDeviceType.ROTARY_ENCODER, 0)
        self.secondary_encoder = InputDeviceId(InputDeviceType.ROTARY_ENCODER, 1)
        self.volume_encoder = InputDeviceId(InputDeviceType.ROTARY_ENCODER, 2)
        self.mapper = InputMapper(
            user_encoder_id=(self.primary_encoder, self.secondary_encoder),
            volume_encoder_id=self.volume_encoder,
        )

    def test_all_user_encoders_map_to_navigation_actions(self) -> None:
        self.assertIs(
            self.mapper.map_input(
                InputEvent(
                    self.secondary_encoder,
                    InputEventType.ROTATED,
                    1,
                )
            ),
            UiAction.NAVIGATE_DOWN,
        )
        self.assertIs(
            self.mapper.map_input(
                InputEvent(
                    self.primary_encoder,
                    InputEventType.BUTTON_PRESSED,
                )
            ),
            UiAction.SELECT,
        )

    def test_volume_button_maps_to_mute_action(self) -> None:
        self.assertIs(
            self.mapper.map_input(
                InputEvent(
                    self.volume_encoder,
                    InputEventType.BUTTON_PRESSED,
                )
            ),
            UiAction.VOLUME_MUTE,
        )

    def test_volume_button_release_is_ignored(self) -> None:
        self.assertIsNone(
            self.mapper.map_input(
                InputEvent(
                    self.volume_encoder,
                    InputEventType.BUTTON_RELEASED,
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
