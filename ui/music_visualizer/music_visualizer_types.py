# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral music visualizer state types."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass


class KickMode(Enum):
    """Rendered kick-drum layout."""

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


class MusicVisualizerSource(str, Enum):
    """Semantic capture source choices."""

    SIMULATED = "simulated"
    PIPEWIRE = "pipewire"
    ANDROID_PLAYBACK = "android-playback"


@dataclass(frozen=True, slots=True)
class VisualizerFrame:
    """Small frontend-facing snapshot produced by an audio-analysis source."""

    level: float
    bass: float
    mid: float
    treble: float
    spectrum: tuple[float, ...]
