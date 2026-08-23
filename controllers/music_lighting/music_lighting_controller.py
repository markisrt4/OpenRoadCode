# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared coordination and effect rendering for music-reactive lighting."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from threading import RLock

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from ui.music_lighting.music_lighting_request_handler_if import MusicLightingRequestHandlerIf
from ui.music_lighting.music_lighting_ui_if import MusicLightingUiIf
from .music_lighting_output import MusicLightingOutput
from .music_lighting_pattern_if import MusicLightingPatternIf
from .music_lighting_patterns import create_default_music_lighting_patterns
from .music_lighting_types import MusicLightingPatternId, MusicLightingState


MusicLightingOutputCallback = Callable[[MusicLightingOutput], None]
MusicLightingEnabledCallback = Callable[[bool], None]


class MusicLightingController(MusicLightingRequestHandlerIf):
    """Own shared music-lighting configuration and render effect frames."""

    def __init__(
        self,
        *,
        patterns: dict[MusicLightingPatternId, MusicLightingPatternIf] | None = None,
        output_callback: MusicLightingOutputCallback | None = None,
        enabled_callback: MusicLightingEnabledCallback | None = None,
    ) -> None:
        self._state = MusicLightingState()
        self._lock = RLock()
        self._uis: list[MusicLightingUiIf] = []
        self._last_analysis: MusicAnalysisState | None = None
        self._patterns = patterns or create_default_music_lighting_patterns()
        self._output_callback = output_callback
        self._enabled_callback = enabled_callback

    @property
    def state(self) -> MusicLightingState:
        with self._lock:
            return self._state

    @property
    def last_analysis(self) -> MusicAnalysisState | None:
        with self._lock:
            return self._last_analysis

    def set_output_callback(self, callback: MusicLightingOutputCallback | None) -> None:
        with self._lock:
            self._output_callback = callback

    def set_enabled_callback(self, callback: MusicLightingEnabledCallback | None) -> None:
        with self._lock:
            self._enabled_callback = callback

    def attach_ui(self, ui: MusicLightingUiIf) -> None:
        with self._lock:
            if ui not in self._uis:
                self._uis.append(ui)
            state = self._state
        ui.set_music_lighting_state(state)

    def detach_ui(self, ui: MusicLightingUiIf) -> None:
        with self._lock:
            if ui in self._uis:
                self._uis.remove(ui)

    def request_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        with self._lock:
            callback = self._enabled_callback
        if callback is not None:
            callback(enabled)
        self._update(enabled=enabled)

    def request_pattern(self, pattern: MusicLightingPatternId) -> None:
        if pattern not in self._patterns:
            raise ValueError(f"Unsupported music lighting pattern: {pattern}")
        self._update(pattern=pattern)

    def request_intensity(self, intensity: float) -> None:
        self._update(intensity=max(0.0, min(1.0, float(intensity))))

    def request_brightness_limit(self, percent: int) -> None:
        self._update(brightness_limit=max(0, min(100, int(percent))))

    def update_analysis(self, state: MusicAnalysisState) -> None:
        """Render one hardware-neutral lighting frame from shared analysis."""
        with self._lock:
            self._last_analysis = state
            config = self._state
            callback = self._output_callback
            pattern = self._patterns.get(config.pattern)
        if not config.enabled or callback is None or pattern is None:
            return
        output = pattern.render(state, config.intensity)
        limited = replace(
            output,
            brightness=min(output.brightness, config.brightness_limit / 100.0),
        )
        callback(limited)

    def _update(self, **changes: object) -> None:
        with self._lock:
            self._state = replace(self._state, **changes)
            state = self._state
            uis = tuple(self._uis)
        for ui in uis:
            ui.set_music_lighting_state(state)
