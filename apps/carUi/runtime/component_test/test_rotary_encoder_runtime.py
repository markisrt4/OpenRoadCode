from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from apps.carUi.config.car_ui_runtime_config_parser import (
    GpioEncoderConfig,
    RotaryEncoderConfig,
    SeesawEncoderConfig,
)
from apps.carUi.runtime.rotary_encoder_runtime import (
    create_rotary_encoder_runtime,
)


class RotaryEncoderRuntimeTest(unittest.TestCase):
    @patch("apps.carUi.runtime.rotary_encoder_runtime.SeesawRotaryEncoder")
    @patch("apps.carUi.runtime.rotary_encoder_runtime.GpioRotaryEncoder")
    @patch("apps.carUi.runtime.rotary_encoder_runtime.GpioRotaryEncoderPins")
    @patch("apps.carUi.runtime.rotary_encoder_runtime.board.I2C")
    def test_builds_heterogeneous_encoders(
        self,
        i2c_factory,
        pins_factory,
        gpio_encoder_factory,
        encoder_factory,
    ) -> None:
        i2c = MagicMock()
        pins = MagicMock()
        i2c_factory.return_value = i2c
        pins_factory.return_value = pins
        encoder_factory.return_value = "seesaw-encoder"
        gpio_encoder_factory.return_value = "gpio-encoder"

        runtime = create_rotary_encoder_runtime(
            RotaryEncoderConfig(
                devices=(
                    SeesawEncoderConfig(address=0x36),
                    GpioEncoderConfig(pin_a=11, pin_b=13, button=15),
                ),
                volume_index=1,
            )
        )

        self.assertEqual(
            ("seesaw-encoder", "gpio-encoder"),
            runtime.encoders,
        )
        self.assertEqual(1, runtime.volume_index)
        encoder_factory.assert_called_once_with(
            address=0x36,
            i2c=i2c,
            reverse_direction=False,
        )
        pins_factory.assert_called_once_with(
            pin_a=11,
            pin_b=13,
            button=15,
        )
        gpio_encoder_factory.assert_called_once_with(
            pins=pins,
            reverse_direction=False,
        )
        i2c_factory.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
