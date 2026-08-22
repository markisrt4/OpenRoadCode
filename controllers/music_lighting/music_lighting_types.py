# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral state and pattern identifiers for music-reactive lighting."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MusicLightingPatternId(Enum):
    SPECTRUM_FLOW = "spectrum_flow"
    BEAT_PULSE = "beat_pulse"
    PERCUSSION = "percussion"
    COLOR_WAVE = "color_wave"
    AMBIENT = "ambient"


@dataclass(frozen=True, slots=True)
class MusicLightingState:
    enabled: bool = False
    pattern: MusicLightingPatternId = MusicLightingPatternId.SPECTRUM_FLOW
    intensity: float = 0.75
    brightness_limit: int = 100
    target_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError("intensity must be in range 0.0..1.0")
        if not 0 <= self.brightness_limit <= 100:
            raise ValueError("brightness_limit must be in range 0..100")
