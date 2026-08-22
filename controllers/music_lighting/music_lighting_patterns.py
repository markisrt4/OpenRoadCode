# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable music-reactive lighting pattern implementations."""
from __future__ import annotations

import colorsys
import time

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from controllers.lighting.lighting_types import RgbColor
from .music_lighting_output import MusicLightingOutput
from .music_lighting_pattern_if import MusicLightingPatternIf
from .music_lighting_types import MusicLightingPatternId


def _rgb(hue: float, saturation: float = 1.0, value: float = 1.0) -> RgbColor:
    red, green, blue = colorsys.hsv_to_rgb(hue % 1.0, saturation, value)
    return RgbColor(round(red * 255), round(green * 255), round(blue * 255))


class BeatPulsePattern:
    def render(self, state: MusicAnalysisState, intensity: float) -> MusicLightingOutput:
        p = state.percussion
        hit = max(p.kick, p.snare * 0.78, p.tom_low * 0.65, p.tom_mid * 0.58, p.tom_high * 0.52)
        brightness = min(1.0, (0.10 + state.audio.level * 0.28 + hit * 0.82) * intensity)
        hue = 0.01 if p.kick >= p.snare else 0.10
        return MusicLightingOutput(_rgb(hue), brightness, 45)


class SpectrumFlowPattern:
    def render(self, state: MusicAnalysisState, intensity: float) -> MusicLightingOutput:
        audio = state.audio
        total = max(0.001, audio.bass + audio.mid + audio.treble)
        hue = (audio.mid / total) * 0.28 + (audio.treble / total) * 0.58
        brightness = min(1.0, (0.12 + audio.level * 0.88) * intensity)
        return MusicLightingOutput(_rgb(hue, 0.92), brightness, 90)


class PercussionPattern:
    def render(self, state: MusicAnalysisState, intensity: float) -> MusicLightingOutput:
        p = state.percussion
        hits = (
            (p.kick, 0.00),
            (p.snare, 0.12),
            (p.tom_low, 0.58),
            (p.tom_mid, 0.46),
            (p.tom_high, 0.78),
            (p.cymbal, 0.16),
        )
        strength, hue = max(hits, key=lambda item: item[0])
        brightness = min(1.0, (0.06 + strength * 0.94) * intensity)
        saturation = 0.45 if hue == 0.16 else 1.0
        return MusicLightingOutput(_rgb(hue, saturation), brightness, 35)


class ColorWavePattern:
    def render(self, state: MusicAnalysisState, intensity: float) -> MusicLightingOutput:
        hue = time.monotonic() * 0.055 + state.audio.mid * 0.12
        brightness = min(1.0, (0.18 + state.audio.level * 0.72 + state.audio.bass * 0.10) * intensity)
        return MusicLightingOutput(_rgb(hue, 0.88), brightness, 120)


class AmbientPattern:
    def render(self, state: MusicAnalysisState, intensity: float) -> MusicLightingOutput:
        hue = 0.62 - state.audio.mid * 0.12 + state.audio.treble * 0.08
        brightness = min(0.68, (0.16 + state.audio.level * 0.42) * intensity)
        return MusicLightingOutput(_rgb(hue, 0.62), brightness, 220)


def create_default_music_lighting_patterns() -> dict[MusicLightingPatternId, MusicLightingPatternIf]:
    return {
        MusicLightingPatternId.SPECTRUM_FLOW: SpectrumFlowPattern(),
        MusicLightingPatternId.BEAT_PULSE: BeatPulsePattern(),
        MusicLightingPatternId.PERCUSSION: PercussionPattern(),
        MusicLightingPatternId.COLOR_WAVE: ColorWavePattern(),
        MusicLightingPatternId.AMBIENT: AmbientPattern(),
    }
