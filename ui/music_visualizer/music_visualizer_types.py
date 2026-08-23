# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class KickMode(Enum):
    SINGLE = "single"
    DOUBLE = "double"


class MusicVisualizationMode(Enum):
    """Semantic visualization choices shared by frontend implementations."""

    SPECTRUM = "spectrum"
    ORBITING_PLANETS = "orbiting_planets"
    ELECTRIC_FREEWAY = "electric_freeway"
    EXPLOSION_FIELD = "explosion_field"
    STAR_DANCE = "star_dance"
    ELECTRIC_RINGS = "electric_rings"
    NEON_RIBBON = "neon_ribbon"
    KALEIDOSCOPE = "kaleidoscope"


@dataclass(frozen=True, slots=True)
class SongRecognitionUiState:
    configured: bool
    recognizing: bool = False
    ready: bool = False
    buffered_seconds: float = 0.0
    provider: str | None = None
    message: str | None = None
