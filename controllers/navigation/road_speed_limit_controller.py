# SPDX-License-Identifier: MIT
"""Bounded road matching, GPS freshness, and stale-result retirement."""

from collections import deque
from collections.abc import Callable
import math
from time import monotonic
from typing import Protocol

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.road_speed_limit_ui_if import RoadSpeedLimitState, RoadSpeedLimitUiIf
from ui.ui_dispatcher_if import UiDispatcherIf


class RoadLimitProvider(Protocol):
    def lookup(self, trace: tuple[GeoPoint, ...]) -> RoadSpeedLimitState:
        """Read map attributes for a position trail.
        @param trace Recent positions in radians.
        @return A normalized SI limit, or unknown when no usable match exists.
        """
        ...


def distance_m(a: GeoPoint, b: GeoPoint) -> float:
    x = (a.longitude_rad - b.longitude_rad) * math.cos((a.latitude_rad + b.latitude_rad) / 2)
    return math.hypot(a.latitude_rad - b.latitude_rad, x) * 6371000


class RoadSpeedLimitController:
    def __init__(self, provider: RoadLimitProvider, ui: RoadSpeedLimitUiIf,
                 dispatcher: UiDispatcherIf, run_work: Callable[[Callable[[], None]], None],
                 clock: Callable[[], float] = monotonic) -> None:
        self._provider, self._ui, self._dispatcher = provider, ui, dispatcher
        self._run_work, self._clock = run_work, clock
        self._trace: deque[GeoPoint] = deque(maxlen=8)
        self._last_fix = -math.inf
        self._last_lookup = -math.inf
        self._matched_at = -math.inf
        self._matched_position: GeoPoint | None = None
        self._pending = False
        self._closed = False
        self._generation = 0
        self._timer: object | None = None

    def start(self) -> None:
        if not self._closed and self._timer is None:
            self._tick()

    def update_position(self, point: GeoPoint | None, accuracy_m: float | None = None) -> None:
        if self._closed:
            return
        if point is None or not all(math.isfinite(x) for x in (point.latitude_rad, point.longitude_rad)) or (
            abs(point.latitude_rad) > math.pi / 2 or abs(point.longitude_rad) > math.pi or
            accuracy_m is not None and (not math.isfinite(accuracy_m) or not 0 <= accuracy_m <= 25)
        ):
            self._clear()
            return
        now = self._clock()
        if now - self._last_fix > 8 or self._trace and distance_m(self._trace[-1], point) > 500:
            self._clear()
        self._last_fix = now
        if not self._trace or distance_m(self._trace[-1], point) >= 3:
            self._trace.append(point)
        if self._matched_position is not None and distance_m(self._matched_position, point) > 40:
            self._ui.set_road_speed_limit(RoadSpeedLimitState())
            self._matched_position = None
        if len(self._trace) < 2 or self._pending or now - self._last_lookup < 2:
            return
        trace, generation = tuple(self._trace), self._generation
        self._last_lookup, self._pending = now, True
        def work() -> None:
            if self._closed:
                return
            try:
                result = self._provider.lookup(trace) if generation == self._generation else RoadSpeedLimitState()
            except Exception:
                result = RoadSpeedLimitState()
            def deliver() -> None:
                self._pending = False
                if self._closed or generation != self._generation:
                    return
                if self._clock() - self._last_fix > 8 or not self._trace or distance_m(trace[-1], self._trace[-1]) > 40:
                    self._clear()
                    return
                self._matched_at = self._clock()
                self._matched_position = trace[-1]
                self._ui.set_road_speed_limit(result)
            self._dispatcher.dispatch_ui(deliver)
        self._run_work(work)

    def _clear(self) -> None:
        self._generation += 1
        self._trace.clear()
        self._matched_position = None
        self._ui.set_road_speed_limit(RoadSpeedLimitState())

    def _tick(self) -> None:
        if self._closed:
            return
        if self._clock() - self._last_fix > 8 or self._clock() - self._matched_at > 8:
            self._ui.set_road_speed_limit(RoadSpeedLimitState())
        if self._clock() - self._last_fix > 8:
            self._clear()
        self._timer = self._dispatcher.schedule_ui_callback(1000, self._tick)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._generation += 1
        if self._timer is not None:
            self._dispatcher.cancel_ui_callback(self._timer)
            self._timer = None
