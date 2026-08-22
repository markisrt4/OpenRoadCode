# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Normalized output produced by music-reactive lighting patterns."""
from __future__ import annotations

from dataclasses import dataclass

from controllers.lighting.lighting_types import RgbColor


@dataclass(frozen=True, slots=True)
class MusicLightingOutput:
    color: RgbColor
    brightness: float
    transition_ms: int = 80

    def __post_init__(self) -> None:
        if not 0.0 <= self.brightness <= 1.0:
            raise ValueError("brightness must be in range 0.0..1.0")
        if self.transition_ms < 0:
            raise ValueError("transition_ms must be non-negative")
