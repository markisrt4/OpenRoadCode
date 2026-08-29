# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Map shared music-analysis state onto application lighting controls."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from time import monotonic

from controllers.audio.music_analysis.music_analysis_types import MusicAnalysisState
from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.lighting.lighting_types import RgbColor


@dataclass(frozen=True, slots=True)
class MusicReactiveLightingState:
    """Lighting values derived from one music-analysis frame."""

    color: RgbColor
    brightness_percent: int


class MusicReactiveLightingMapper:
    """Convert analyzer bands and percussion estimates into RGB lighting."""

    def map(self, state: MusicAnalysisState) -> MusicReactiveLightingState:
        """Derive RGB chroma and brightness from an analysis snapshot."""
        red = max(_unit(state.bass), _unit(state.percussion.kick))
        green = max(_unit(state.mid), _unit(state.percussion.snare))
        blue = max(_unit(state.treble), _unit(state.percussion.cymbal))
        peak = max(red, green, blue)

        if peak <= 0.0:
            color = RgbColor(0, 0, 0)
        else:
            color = RgbColor(
                _channel(red / peak),
                _channel(green / peak),
                _channel(blue / peak),
            )

        return MusicReactiveLightingState(
            color=color,
            brightness_percent=round(_unit(state.level) * 100.0),
        )


class MusicReactiveLighting:
    """Rate-limited bridge from music analysis to a lighting controller."""

    def __init__(
        self,
        controller: LightingControllerIf,
        *,
        mapper: MusicReactiveLightingMapper | None = None,
        update_interval_seconds: float = 0.05,
        enabled: bool = False,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if update_interval_seconds < 0.0:
            raise ValueError("update_interval_seconds must be non-negative")

        self._controller = controller
        self._mapper = mapper or MusicReactiveLightingMapper()
        self._update_interval_seconds = update_interval_seconds
        self._clock = clock
        self._enabled = bool(enabled)
        self._last_update_time: float | None = None
        self._last_state: MusicReactiveLightingState | None = None

    @property
    def is_enabled(self) -> bool:
        """Return whether analyzer frames may control the lighting output."""
        return self._enabled

    @property
    def is_connected(self) -> bool:
        """Return whether the underlying lighting controller is connected."""
        return self._controller.is_connected

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable music-reactive output."""
        enabled = bool(enabled)
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self.reset()

    def update(
        self,
        analysis: MusicAnalysisState,
    ) -> tuple[Future[None], ...]:
        """Apply one analyzer frame when reactive control is enabled."""
        if not self._enabled or not self._controller.is_connected:
            return ()

        now = self._clock()
        if (
            self._last_update_time is not None
            and now - self._last_update_time < self._update_interval_seconds
        ):
            return ()

        derived = self._mapper.map(analysis)
        previous = self._last_state
        commands: list[Future[None]] = []

        if previous is None or derived.color != previous.color:
            commands.append(self._controller.set_color(derived.color))
        if (
            previous is None
            or derived.brightness_percent != previous.brightness_percent
        ):
            commands.append(
                self._controller.set_brightness(derived.brightness_percent)
            )

        self._last_update_time = now
        self._last_state = derived
        return tuple(commands)

    def reset(self) -> None:
        """Forget rate-limit and last-output state."""
        self._last_update_time = None
        self._last_state = None


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _channel(value: float) -> int:
    return round(_unit(value) * 255.0)
