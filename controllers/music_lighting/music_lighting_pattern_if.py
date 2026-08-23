# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Pattern boundary for music-reactive lighting."""
from __future__ import annotations

from typing import Protocol

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from .music_lighting_output import MusicLightingOutput


class MusicLightingPatternIf(Protocol):
    def render(self, state: MusicAnalysisState, intensity: float) -> MusicLightingOutput:
        """Convert normalized music analysis into one lighting output frame.

        @param state Latest normalized music analysis.
        @param intensity User-selected effect intensity.
        @return Hardware-neutral color and brightness output.
        """
        ...
