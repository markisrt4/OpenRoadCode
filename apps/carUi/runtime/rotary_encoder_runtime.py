from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

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


class _NoOpRotaryEncoder(RotaryEncoderIf):
    """Preserve configured input slots on hosts without Pi hardware."""

    def __init__(self) -> None:
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(
        self,
        rotated: RotationCallback,
        button_pressed: ButtonCallback | None = None,
        button_released: ButtonCallback | None = None,
    ) -> None:
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False


def _is_raspberry_pi() -> bool:
    model_path = Path("/proc/device-tree/model")
    try:
        return "Raspberry Pi" in model_path.read_text(errors="ignore")
    except OSError:
        return False


def _create_hardware_encoder(
    device: SeesawEncoderConfig | GpioEncoderConfig,
    i2c: object | None,
) -> tuple[RotaryEncoderIf, object | None]:
    if isinstance(device, SeesawEncoderConfig):
        import board
        from hardware_io.rotary_encoder.seesaw_rotary_encoder import (
            SeesawRotaryEncoder,
        )

        if i2c is None:
            i2c = board.I2C()
        return (
            SeesawRotaryEncoder(
                address=device.address,
                i2c=i2c,
                reverse_direction=device.reverse_direction,
            ),
            i2c,
        )

    if isinstance(device, GpioEncoderConfig):
        from hardware_io.rotary_encoder.gpio_rotary_encoder import (
            GpioRotaryEncoder,
            GpioRotaryEncoderPins,
        )

        return (
            GpioRotaryEncoder(
                pins=GpioRotaryEncoderPins(
                    pin_a=device.pin_a,
                    pin_b=device.pin_b,
                    button=device.button,
                ),
                reverse_direction=device.reverse_direction,
            ),
            i2c,
        )

    raise TypeError(
        f"Unsupported rotary encoder config: {type(device).__name__}"
    )


def create_rotary_encoder_runtime(
    config: RotaryEncoderConfig,
) -> RotaryEncoderRuntime:
    """Instantiate configured encoders, using no-ops away from Raspberry Pi."""

    i2c: object | None = None
    encoders: list[RotaryEncoderIf] = []
    raspberry_pi = _is_raspberry_pi()

    for device in config.devices:
        if raspberry_pi:
            encoder, i2c = _create_hardware_encoder(device, i2c)
        else:
            LOGGER.info(
                "Using a no-op %s encoder on a non-Raspberry Pi host",
                type(device).__name__,
            )
            encoder = _NoOpRotaryEncoder()
        encoders.append(encoder)

    return RotaryEncoderRuntime(
        encoders=tuple(encoders),
        volume_index=config.volume_index,
    )
