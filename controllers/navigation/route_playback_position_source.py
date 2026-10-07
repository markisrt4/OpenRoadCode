# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Select live or route-generated positions without changing the live provider."""

from __future__ import annotations

import threading

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_source_if import PositionSourceIf, PositionStateCallback
from controllers.navigation.route_simulation_if import RouteSimulationIf
from controllers.navigation.simulated_position_source import SimulatedPositionSource
from controllers.route_planning.route_planning_types import RouteResult


class RoutePlaybackPositionSource(PositionSourceIf, RouteSimulationIf):
    """Keep live GPS running while route playback temporarily replaces delivery."""

    def __init__(
        self,
        live_source: PositionSourceIf,
        simulator: SimulatedPositionSource | None = None,
    ) -> None:
        self._live_source = live_source
        self._simulator = simulator if simulator is not None else SimulatedPositionSource()
        self._lifecycle_lock = threading.RLock()
        self._delivery_lock = threading.RLock()
        self._callback: PositionStateCallback | None = None
        self._generation = 0
        self._playback_generation = 0
        self._playing = False

    def start(self, callback: PositionStateCallback) -> None:
        """Start live delivery; restarting never resumes an old simulation."""
        with self._lifecycle_lock:
            with self._delivery_lock:
                if self._callback is not None:
                    return
                self._generation += 1
                generation = self._generation
                self._callback = callback
            try:
                self._live_source.start(
                    lambda state: self._deliver(state, generation, None)
                )
            except BaseException:
                self.stop()
                raise

    def stop(self) -> None:
        """Invalidate pending reports and stop both position producers."""
        with self._lifecycle_lock:
            with self._delivery_lock:
                self._callback = None
                self._generation += 1
            try:
                self.stop_route()
            finally:
                self._live_source.stop()

    def follow_route(self, route: RouteResult, *, time_scale: float = 60.0) -> None:
        """Play a route locally while the live source continues receiving GPS."""
        with self._lifecycle_lock:
            if self._callback is None:
                raise RuntimeError("position source is not running")
            self.stop_route()
            self._simulator.follow_route(route, time_scale=time_scale)
            with self._delivery_lock:
                self._playing = True
                generation = self._generation
                playback_generation = self._playback_generation
            try:
                self._simulator.start(
                    lambda state: self._deliver(state, generation, playback_generation)
                )
            except BaseException:
                self.stop_route()
                raise

    def stop_route(self) -> None:
        """Resume delivery of fresh live reports and reject stale playback reports."""
        with self._lifecycle_lock:
            with self._delivery_lock:
                self._playing = False
                self._playback_generation += 1
            self._simulator.stop()
            self._simulator.stop_route()

    def _deliver(
        self, state: PositionState, generation: int, playback_generation: int | None
    ) -> None:
        with self._delivery_lock:
            callback = self._callback
            if callback is None or generation != self._generation:
                return
            if playback_generation is None:
                if self._playing:
                    return
            elif not self._playing or playback_generation != self._playback_generation:
                return
            callback(state)
