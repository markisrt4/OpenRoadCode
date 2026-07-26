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


class UnavailableRotaryEncoder(RotaryEncoderIf):
    """Keep desktop UI composition valid when Pi hardware is unavailable."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(
        self,
        rotated: RotationCallback,
        button_pressed: ButtonCallback | None = None,
        button_released: ButtonCallback | None = None,
    ) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False


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
            try:
                if i2c is None:
                    i2c = _create_i2c_bus()
                encoder = _create_seesaw_encoder(device, i2c)
            except (ImportError, ModuleNotFoundError, OSError, RuntimeError) as exc:
                encoder = _unavailable_encoder(device, exc)
        elif isinstance(device, GpioEncoderConfig):
            try:
                encoder = _create_gpio_encoder(device)
            except (ImportError, ModuleNotFoundError, OSError, RuntimeError) as exc:
                encoder = _unavailable_encoder(device, exc)
        else:
            raise TypeError(
                f"Unsupported rotary encoder config: {type(device).__name__}"
            )

        encoders.append(encoder)

    return RotaryEncoderRuntime(
        encoders=tuple(encoders),
        volume_index=config.volume_index,
    )


def _create_i2c_bus() -> Any:
    import board

    return board.I2C()


def _create_seesaw_encoder(
    config: SeesawEncoderConfig,
    i2c: Any,
) -> RotaryEncoderIf:
    from hardware_io.rotary_encoder.seesaw_rotary_encoder import (
        SeesawRotaryEncoder,
    )

    return SeesawRotaryEncoder(
        address=config.address,
        i2c=i2c,
        reverse_direction=config.reverse_direction,
    )


def _create_gpio_encoder(config: GpioEncoderConfig) -> RotaryEncoderIf:
    from hardware_io.rotary_encoder.gpio_rotary_encoder import (
        GpioRotaryEncoder,
        GpioRotaryEncoderPins,
    )

    return GpioRotaryEncoder(
        pins=GpioRotaryEncoderPins(
            pin_a=config.pin_a,
            pin_b=config.pin_b,
            button=config.button,
        ),
        reverse_direction=config.reverse_direction,
    )


def _unavailable_encoder(
    config: SeesawEncoderConfig | GpioEncoderConfig,
    error: Exception,
) -> UnavailableRotaryEncoder:
    reason = (
        f"{type(config).__name__} unavailable: "
        f"{type(error).__name__}: {error}"
    )
    LOGGER.warning(reason)
    return UnavailableRotaryEncoder(reason)
