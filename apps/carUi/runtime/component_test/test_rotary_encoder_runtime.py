from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from apps.carUi.config.car_ui_runtime_config_parser import (
    GpioEncoderConfig,
    RotaryEncoderConfig,
    SeesawEncoderConfig,
)
from apps.carUi.runtime.rotary_encoder_runtime import (
    UnavailableRotaryEncoder,
    create_rotary_encoder_runtime,
)


class RotaryEncoderRuntimeTest(unittest.TestCase):
    @patch("apps.carUi.runtime.rotary_encoder_runtime._create_gpio_encoder")
    @patch("apps.carUi.runtime.rotary_encoder_runtime._create_seesaw_encoder")
    @patch("apps.carUi.runtime.rotary_encoder_runtime._create_i2c_bus")
    def test_builds_heterogeneous_encoders(
        self,
        i2c_factory,
        encoder_factory,
        gpio_encoder_factory,
    ) -> None:
        i2c = MagicMock()
        i2c_factory.return_value = i2c
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
            RotaryEncoderConfig(
                devices=(
                    SeesawEncoderConfig(address=0x36),
                    GpioEncoderConfig(pin_a=11, pin_b=13, button=15),
                ),
                volume_index=1,
            ).devices[0],
            i2c,
        )
        gpio_encoder_factory.assert_called_once_with(
            RotaryEncoderConfig(
                devices=(
                    SeesawEncoderConfig(address=0x36),
                    GpioEncoderConfig(pin_a=11, pin_b=13, button=15),
                ),
                volume_index=1,
            ).devices[1],
        )
        i2c_factory.assert_called_once_with()

    @patch(
        "apps.carUi.runtime.rotary_encoder_runtime._create_i2c_bus",
        side_effect=ModuleNotFoundError("No module named 'board'"),
    )
    def test_missing_pi_dependencies_use_inert_encoders(
        self,
        _i2c_factory,
    ) -> None:
        runtime = create_rotary_encoder_runtime(
            RotaryEncoderConfig(
                devices=(
                    SeesawEncoderConfig(address=0x36),
                    SeesawEncoderConfig(address=0x37),
                ),
                volume_index=0,
            )
        )

        self.assertEqual(2, len(runtime.encoders))
        self.assertTrue(
            all(
                isinstance(encoder, UnavailableRotaryEncoder)
                for encoder in runtime.encoders
            )
        )


if __name__ == "__main__":
    unittest.main()
