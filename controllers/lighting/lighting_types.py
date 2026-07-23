from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


@dataclass(frozen=True, slots=True)
class RgbColor:
    """Represent an RGB color using channels in the range 0 through 255."""
    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        for name, value in (
            ("red", self.red),
            ("green", self.green),
            ("blue", self.blue),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be in range 0..255")


class CustomPatternMode(Enum):
    """Animation modes supported by LED-DMX custom patterns."""
    GRADUAL = 0
    FADE = 1
    FORWARD = 2
    FLASH = 3
    OFF = 4
    PULSE = 5
    FLOW = 6
    HOP = 7


@dataclass(frozen=True, slots=True)
class LightingState:
    """Immutable snapshot of lighting connection and output settings."""
    connected: bool = False
    power_enabled: bool = False
    color: RgbColor = RgbColor(255, 255, 255)
    brightness_percent: int = 100
    color_temperature_percent: int = 50
    pattern_index: int = 0
    music_mode: int = 0
    custom_pattern_mode: CustomPatternMode = CustomPatternMode.OFF
    custom_pattern_forward: bool = True

    def __post_init__(self) -> None:
        _validate_range(
            "brightness_percent",
            self.brightness_percent,
            0,
            100,
        )
        _validate_range(
            "color_temperature_percent",
            self.color_temperature_percent,
            0,
            100,
        )
        _validate_range("pattern_index", self.pattern_index, 0, 210)
        _validate_range("music_mode", self.music_mode, 0, 255)

    def updated(self, **changes: object) -> "LightingState":
        """Return a copy with selected fields replaced.

        @param changes Field names and replacement values.
        @return Updated, validated lighting state.
        """
        return replace(self, **changes)


def _validate_range(
    name: str,
    value: int,
    minimum: int,
    maximum: int,
) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} must be in range {minimum}..{maximum}"
        )
