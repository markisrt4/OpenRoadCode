from importlib import import_module
from typing import TYPE_CHECKING, Any

from hardware_io.rotary_encoder.rotary_encoder_if import (
    ButtonCallback,
    RotaryEncoderIf,
    RotationCallback,
)

if TYPE_CHECKING:
    from hardware_io.rotary_encoder.gpio_rotary_encoder import (
        GpioRotaryEncoder,
        GpioRotaryEncoderPins,
    )
    from hardware_io.rotary_encoder.seesaw_rotary_encoder import (
        SeesawRotaryEncoder,
    )

__all__ = [
    "ButtonCallback",
    "GpioRotaryEncoder",
    "GpioRotaryEncoderPins",
    "RotaryEncoderIf",
    "RotationCallback",
    "SeesawRotaryEncoder",
]


def __getattr__(name: str) -> Any:
    """Load optional hardware implementations only when explicitly requested."""

    implementation_modules = {
        "GpioRotaryEncoder": (
            "hardware_io.rotary_encoder.gpio_rotary_encoder"
        ),
        "GpioRotaryEncoderPins": (
            "hardware_io.rotary_encoder.gpio_rotary_encoder"
        ),
        "SeesawRotaryEncoder": (
            "hardware_io.rotary_encoder.seesaw_rotary_encoder"
        ),
    }
    module_name = implementation_modules.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
