from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GpioPin:
    """
    Describes one physical pin on a Raspberry Pi GPIO header.
    """

    physical_pin: int
    bcm: int | None
    name: str
    function: str

    @property
    def is_gpio(self) -> bool:
        """Return whether this value identifies a GPIO pin.

        @retval True The header position maps to a BCM GPIO number.
        @retval False The position is power, ground, or otherwise non-GPIO.
        """
        return self.bcm is not None
