# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RgbColor:
    """Represent an RGB color using integer channels in the range 0..255."""

    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        for name, value in (("red", self.red), ("green", self.green), ("blue", self.blue)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be in range 0..255")


@dataclass(frozen=True, slots=True)
class HsvColor:
    """Represent HSV using hue degrees and normalized saturation/value."""

    hue_degrees: float
    saturation: float
    value: float

    def __post_init__(self) -> None:
        for name, channel in (
            ("hue_degrees", self.hue_degrees),
            ("saturation", self.saturation),
            ("value", self.value),
        ):
            if not isinstance(channel, (int, float)) or isinstance(channel, bool):
                raise TypeError(f"{name} must be numeric")
        if not 0.0 <= float(self.hue_degrees) <= 360.0:
            raise ValueError("hue_degrees must be in range 0..360")
        if not 0.0 <= float(self.saturation) <= 1.0:
            raise ValueError("saturation must be in range 0..1")
        if not 0.0 <= float(self.value) <= 1.0:
            raise ValueError("value must be in range 0..1")
