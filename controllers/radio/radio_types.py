from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RadioRange:
    """Define an inclusive tuning range and its initial frequency.

    All frequency values are expressed in hertz.
    """
    min_frequency_hz: int
    max_frequency_hz: int
    start_frequency_hz: int

    def __post_init__(self) -> None:
        if self.min_frequency_hz <= 0:
            raise ValueError("min_frequency_hz must be greater than zero")
        if self.max_frequency_hz < self.min_frequency_hz:
            raise ValueError(
                "max_frequency_hz must be greater than or equal to min_frequency_hz"
            )
        if not self.min_frequency_hz <= self.start_frequency_hz <= self.max_frequency_hz:
            raise ValueError("start_frequency_hz must be within the radio range")


@dataclass(frozen=True, slots=True)
class RadioMode:
    """Define a normalized demodulation mode and tuning step."""
    name: str
    bandwidth: int
    step_hz: int

    def __post_init__(self) -> None:
        normalized_name = self.name.strip().upper()
        if not normalized_name:
            raise ValueError("mode name must not be empty")
        if self.bandwidth < 0:
            raise ValueError("bandwidth must not be negative")
        if self.step_hz <= 0:
            raise ValueError("step_hz must be greater than zero")
        object.__setattr__(self, "name", normalized_name)


@dataclass(frozen=True, slots=True)
class RadioPreset:
    """Associate a user-visible label with a frequency and mode."""
    label: str
    frequency_hz: int
    mode: RadioMode

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("preset label must not be empty")
        if self.frequency_hz <= 0:
            raise ValueError("frequency_hz must be greater than zero")

    @property
    def frequency_mhz(self) -> float:
        """Return the preset frequency in megahertz.

        @return Frequency converted from hertz to megahertz.
        """
        return self.frequency_hz / 1_000_000
