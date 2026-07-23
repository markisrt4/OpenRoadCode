from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import board

from apps.carUi.config.car_ui_runtime_config_parser import (
    GpioEncoderConfig,
    RotaryEncoderConfig,
    SeesawEncoderConfig,
)
from hardware_io.rotary_encoder import (
    GpioRotaryEncoder,
    GpioRotaryEncoderPins,
    RotaryEncoderIf,
    SeesawRotaryEncoder,
)


@dataclass(frozen=True, slots=True)
class RotaryEncoderRuntime:
    """Contain instantiated encoder devices and the volume-device index."""
    encoders: tuple[RotaryEncoderIf, ...]
    volume_index: int


def create_rotary_encoder_runtime(
    config: RotaryEncoderConfig,
) -> RotaryEncoderRuntime:
    """Instantiate rotary-encoder drivers from validated configuration."""
    i2c: Any | None = None
    encoders: list[RotaryEncoderIf] = []

    for device in config.devices:
        if isinstance(device, SeesawEncoderConfig):
            if i2c is None:
                i2c = board.I2C()
            encoder: RotaryEncoderIf = SeesawRotaryEncoder(
                address=device.address,
                i2c=i2c,
                reverse_direction=device.reverse_direction,
            )
        elif isinstance(device, GpioEncoderConfig):
            encoder = GpioRotaryEncoder(
                pins=GpioRotaryEncoderPins(
                    pin_a=device.pin_a,
                    pin_b=device.pin_b,
                    button=device.button,
                ),
                reverse_direction=device.reverse_direction,
            )
        else:
            raise TypeError(
                f"Unsupported rotary encoder config: {type(device).__name__}"
            )

        encoders.append(encoder)

    return RotaryEncoderRuntime(
        encoders=tuple(encoders),
        volume_index=config.volume_index,
    )
