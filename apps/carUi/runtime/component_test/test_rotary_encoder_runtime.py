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
    @patch("apps.carUi.runtime.rotary_encoder_runtime._create_gpio_encoder")
    @patch("apps.carUi.runtime.rotary_encoder_runtime._create_seesaw_encoder")
    @patch("apps.carUi.runtime.rotary_encoder_runtime._create_i2c")
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

        seesaw_config = SeesawEncoderConfig(address=0x36)
        gpio_config = GpioEncoderConfig(
            pin_a=11,
            pin_b=13,
            button=15,
        )
        runtime = create_rotary_encoder_runtime(
            RotaryEncoderConfig(
                devices=(seesaw_config, gpio_config),
                volume_index=1,
            )
        )

        self.assertEqual(
            ("seesaw-encoder", "gpio-encoder"),
            runtime.encoders,
        )
        self.assertEqual(1, runtime.volume_index)
        encoder_factory.assert_called_once_with(seesaw_config, i2c)
        gpio_encoder_factory.assert_called_once_with(gpio_config)
        i2c_factory.assert_called_once_with()

    def test_missing_hardware_dependency_uses_disabled_encoder(self) -> None:
        config = RotaryEncoderConfig(
            devices=(
                SeesawEncoderConfig(address=0x36),
                GpioEncoderConfig(pin_a=11, pin_b=13, button=15),
            ),
            volume_index=1,
        )

        with patch(
            "apps.carUi.runtime.rotary_encoder_runtime._create_i2c",
            side_effect=ModuleNotFoundError("No module named 'board'"),
        ) as i2c_factory:
            with patch(
                "apps.carUi.runtime.rotary_encoder_runtime."
                "_create_gpio_encoder",
                side_effect=ModuleNotFoundError("No module named 'RPi'"),
            ):
                runtime = create_rotary_encoder_runtime(config)

        self.assertEqual(2, len(runtime.encoders))
        self.assertEqual(1, runtime.volume_index)
        self.assertTrue(
            all(not encoder.is_running for encoder in runtime.encoders)
        )
        i2c_factory.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
