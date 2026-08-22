# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared coordination and state for music-reactive lighting."""
from __future__ import annotations

from dataclasses import replace
from threading import RLock

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from .music_lighting_types import MusicLightingPatternId, MusicLightingState


class MusicLightingController:
    """Own music-lighting configuration independently of any UI panel.

    Pattern-to-device rendering is intentionally kept behind this controller;
    both Lighting and Music Visualizer frontends may observe and modify the
    same state without owning the effect engine.
    """

    def __init__(self) -> None:
        self._state = MusicLightingState()
        self._lock = RLock()
        self._uis: list[object] = []
        self._last_analysis: MusicAnalysisState | None = None

    @property
    def state(self) -> MusicLightingState:
        with self._lock:
            return self._state

    def attach_ui(self, ui: object) -> None:
        with self._lock:
            if ui not in self._uis:
                self._uis.append(ui)
            state = self._state
        ui.set_music_lighting_state(state)

    def detach_ui(self, ui: object) -> None:
        with self._lock:
            if ui in self._uis:
                self._uis.remove(ui)

    def request_enabled(self, enabled: bool) -> None:
        self._update(enabled=bool(enabled))

    def request_pattern(self, pattern: MusicLightingPatternId) -> None:
        self._update(pattern=pattern)

    def request_intensity(self, intensity: float) -> None:
        self._update(intensity=max(0.0, min(1.0, float(intensity))))

    def request_brightness_limit(self, percent: int) -> None:
        self._update(brightness_limit=max(0, min(100, int(percent))))

    def update_analysis(self, state: MusicAnalysisState) -> None:
        """Accept shared music state for the forthcoming effect engine."""
        with self._lock:
            self._last_analysis = state

    def _update(self, **changes: object) -> None:
        with self._lock:
            self._state = replace(self._state, **changes)
            state = self._state
            uis = tuple(self._uis)
        for ui in uis:
            ui.set_music_lighting_state(state)
