from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from apps.carUi.config.car_ui_runtime_config_parser import (
    GpioEncoderConfig,
    RotaryEncoderConfig,
    SeesawEncoderConfig,
)
from hardware_io.rotary_encoder.rotary_encoder_if import (
    ButtonCallback,
    RotaryEncoderIf,
    RotationCallback,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RotaryEncoderRuntime:
    """Contain instantiated encoder devices and the volume-device index."""
    encoders: tuple[RotaryEncoderIf, ...]
    volume_index: int


class DisabledRotaryEncoder(RotaryEncoderIf):
    """No-op encoder used when hardware input is disabled."""

    @property
    def is_running(self) -> bool:
        return False

    def start(
        self,
        rotated: RotationCallback,
        button_pressed: ButtonCallback | None = None,
        button_released: ButtonCallback | None = None,
    ) -> None:
        return None

    def stop(self) -> None:
        return None

    def poll(self) -> None:
        return None


def _create_i2c() -> Any:
    import board

    return board.I2C()


def _create_seesaw_encoder(
    device: SeesawEncoderConfig,
    i2c: Any,
) -> RotaryEncoderIf:
    from hardware_io.rotary_encoder.seesaw_rotary_encoder import (
        SeesawRotaryEncoder,
    )

    return SeesawRotaryEncoder(
        address=device.address,
        i2c=i2c,
        reverse_direction=device.reverse_direction,
    )


def _create_gpio_encoder(
    device: GpioEncoderConfig,
) -> RotaryEncoderIf:
    from hardware_io.rotary_encoder.gpio_rotary_encoder import (
        GpioRotaryEncoder,
        GpioRotaryEncoderPins,
    )

    return GpioRotaryEncoder(
        pins=GpioRotaryEncoderPins(
            pin_a=device.pin_a,
            pin_b=device.pin_b,
            button=device.button,
        ),
        reverse_direction=device.reverse_direction,
    )


def create_rotary_encoder_runtime(
    config: RotaryEncoderConfig,
) -> RotaryEncoderRuntime:
    """Instantiate available encoder drivers and stub unavailable hardware."""
    i2c = None
    encoders: list[RotaryEncoderIf] = []

    for device in config.devices:
        try:
            if isinstance(device, SeesawEncoderConfig):
                if i2c is None:
                    i2c = _create_i2c()
                encoder = _create_seesaw_encoder(device, i2c)
            elif isinstance(device, GpioEncoderConfig):
                encoder = _create_gpio_encoder(device)
            else:
                raise TypeError(
                    "Unsupported rotary encoder config: "
                    f"{type(device).__name__}"
                )
        except ModuleNotFoundError as exc:
            LOGGER.warning(
                "Rotary encoder disabled because an optional hardware "
                "dependency is unavailable: %s",
                exc,
            )
            encoder = DisabledRotaryEncoder()

        encoders.append(encoder)

    return RotaryEncoderRuntime(
        encoders=tuple(encoders),
        volume_index=config.volume_index,
    )
