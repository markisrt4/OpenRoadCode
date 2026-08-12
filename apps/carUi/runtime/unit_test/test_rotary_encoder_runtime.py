# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from config.runtime_config import (
    GpioEncoderConfig,
    RotaryEncoderConfig,
    SeesawEncoderConfig,
)
from apps.carUi.runtime.rotary_encoder_runtime import (
    create_rotary_encoder_runtime,
)


class RotaryEncoderRuntimeTest(unittest.TestCase):
    @patch("apps.carUi.runtime.rotary_encoder_runtime._is_raspberry_pi")
    @patch("apps.carUi.runtime.rotary_encoder_runtime._create_hardware_encoder")
    def test_builds_heterogeneous_encoders(
        self,
        encoder_factory,
        is_raspberry_pi,
    ) -> None:
        i2c = MagicMock()
        is_raspberry_pi.return_value = True
        encoder_factory.side_effect = (
            ("seesaw-encoder", i2c),
            ("gpio-encoder", i2c),
        )

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
        self.assertEqual(2, encoder_factory.call_count)
        encoder_factory.assert_any_call(
            SeesawEncoderConfig(address=0x36),
            None,
        )
        encoder_factory.assert_any_call(
            GpioEncoderConfig(pin_a=11, pin_b=13, button=15),
            i2c,
        )

    @patch("apps.carUi.runtime.rotary_encoder_runtime._is_raspberry_pi")
    def test_uses_no_op_encoders_off_raspberry_pi(
        self,
        is_raspberry_pi,
    ) -> None:
        is_raspberry_pi.return_value = False
        runtime = create_rotary_encoder_runtime(
            RotaryEncoderConfig(
                devices=(
                    SeesawEncoderConfig(address=0x36),
                    GpioEncoderConfig(pin_a=11, pin_b=13),
                ),
                volume_index=0,
            )
        )

        self.assertEqual(2, len(runtime.encoders))
        for encoder in runtime.encoders:
            self.assertFalse(encoder.is_running)
            encoder.start(lambda _steps: None)
            self.assertTrue(encoder.is_running)
            encoder.stop()


if __name__ == "__main__":
    unittest.main()
