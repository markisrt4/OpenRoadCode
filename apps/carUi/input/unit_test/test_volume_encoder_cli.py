from __future__ import annotations

import unittest
from unittest.mock import patch

from apps.carUi.config.car_ui_runtime_config_parser import (
    GpioEncoderConfig,
    RotaryEncoderConfig,
    SeesawEncoderConfig,
)
from apps.carUi.input.component_test.volume_encoder_cli import (
    DEFAULT_VOLUME_STEPS,
    parse_args,
    select_volume_encoder,
)


class VolumeEncoderCliTest(unittest.TestCase):
    @patch("sys.argv", ["volume_encoder_cli.py"])
    def test_default_reported_volume_range_matches_five_percent_steps(
        self,
    ) -> None:
        self.assertEqual(20, DEFAULT_VOLUME_STEPS)
        self.assertEqual(20, parse_args().volume_steps)

    def test_selects_only_the_configured_volume_device(self) -> None:
        selected = select_volume_encoder(
            RotaryEncoderConfig(
                devices=(
                    SeesawEncoderConfig(address=0x36),
                    GpioEncoderConfig(pin_a=11, pin_b=13, button=15),
                    SeesawEncoderConfig(address=0x38),
                ),
                volume_index=1,
            )
        )

        self.assertEqual(
            (GpioEncoderConfig(pin_a=11, pin_b=13, button=15),),
            selected.devices,
        )
        self.assertEqual(0, selected.volume_index)


if __name__ == "__main__":
    unittest.main()
