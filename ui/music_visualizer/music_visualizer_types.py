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

    FREQUENCY_TUNNEL = "frequency_tunnel"
    SPECTRUM = "spectrum"
    BOOMBOX = "boombox"
    ORBITING_PLANETS = "orbiting_planets"
    ELECTRIC_FREEWAY = "electric_freeway"
    EXPLOSION_FIELD = "explosion_field"
    STAR_DANCE = "star_dance"
    ELECTRIC_RINGS = "electric_rings"
    NEON_RIBBON = "neon_ribbon"
    KALEIDOSCOPE = "kaleidoscope"


class MusicCaptureState(Enum):
    """Current capture lifecycle, including pending asynchronous connection."""

    IDLE = 'idle'
    STARTING = 'starting'
    RUNNING = 'running'


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

    beat: float = 0.0
    # Hann-window FFT bin amplitudes (dBFS), paired with actual bin frequencies.
    spectrum_dbfs: tuple[float, ...] = ()
    spectrum_hz: tuple[float, ...] = ()
    kick: float = 0.0
    snare: float = 0.0
    tom_high: float = 0.0
    tom_mid: float = 0.0
    tom_low: float = 0.0
    cymbal: float = 0.0


class MusicVisualizerView(Enum):
    """Visible native scene sharing the current analysis session."""

    VISUALIZER = "visualizer"
    DRUM_KIT = "drum_kit"


class AnalyzerPalette(str, Enum):
    """Analyzer color presets; custom colors are normalized RGB triples."""

    ORC = 'ORC blue'
    RETRO = 'Retro'
    MONO = 'Monochrome'
    FIRE = 'Fire'
    CUSTOM = 'Custom'


@dataclass(frozen=True, slots=True)
class AnalyzerAppearance:
    """Appearance and display timing; never changes FFT measurement or capture."""

    palette: AnalyzerPalette = AnalyzerPalette.ORC
    segmented: bool = False
    spacing: float = .2
    response_s: float = .05
    decay_s: float = .3
    peak_markers: bool = True
    band_count: int = 64
    low_color: tuple[float, float, float] = (.02, .35, .65)
    high_color: tuple[float, float, float] = (.15, .85, 1.0)


@dataclass(frozen=True, slots=True)
class MusicVisualizerOptions:
    """Presentation-only settings, independent of audio capture and calibration."""

    mode: MusicVisualizationMode = MusicVisualizationMode.FREQUENCY_TUNNEL
    view: MusicVisualizerView = MusicVisualizerView.VISUALIZER
    kick_mode: KickMode = KickMode.SINGLE
    beat_gain: float = 1.5
    drum_zoom: float = 1.6
    drum_gain: float = 0.6
    analyzer: AnalyzerAppearance = AnalyzerAppearance()
