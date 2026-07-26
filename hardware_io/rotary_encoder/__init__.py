from hardware_io.rotary_encoder.rotary_encoder_if import (
    ButtonCallback,
    RotaryEncoderIf,
    RotationCallback,
)

__all__ = [
    "ButtonCallback",
    "GpioRotaryEncoder",
    "GpioRotaryEncoderPins",
    "RotaryEncoderIf",
    "RotationCallback",
    "SeesawRotaryEncoder",
]


def __getattr__(name: str):
    """Load platform-specific encoder drivers only when they are requested."""
    if name in {"GpioRotaryEncoder", "GpioRotaryEncoderPins"}:
        from hardware_io.rotary_encoder.gpio_rotary_encoder import (
            GpioRotaryEncoder,
            GpioRotaryEncoderPins,
        )

        return {
            "GpioRotaryEncoder": GpioRotaryEncoder,
            "GpioRotaryEncoderPins": GpioRotaryEncoderPins,
        }[name]
    if name == "SeesawRotaryEncoder":
        from hardware_io.rotary_encoder.seesaw_rotary_encoder import (
            SeesawRotaryEncoder,
        )

        return SeesawRotaryEncoder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
