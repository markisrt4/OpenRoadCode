# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Present navigation aligned approximately to the displayed camera frame."""

from collections import deque
from collections.abc import Callable
from dataclasses import replace
import math
from threading import RLock
import time
from typing import TypeVar

from ui.ui_dispatcher_if import UiDispatcherIf
from ui.vision.navigation_overlay import (
    NavigationOverlayRequestHandlerIf, NavigationOverlayState, NavigationOverlayUiIf,
    OverlayGuidance, OverlayMotion, OverlayPosition, OverlayGpsStatus,
)

Sample = TypeVar("Sample", OverlayPosition, OverlayMotion, OverlayGuidance)


class NavigationOverlayController(NavigationOverlayRequestHandlerIf):
    """Keep bounded telemetry history; timers and rendering run on the UI thread.

    Ingress may append samples from workers. Each displayed frame selects only
    samples received at or before its capture timestamp. No route or camera
    business state is changed by the overlay.
    """

    def __init__(self, dispatcher: UiDispatcherIf, ui: NavigationOverlayUiIf, *,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._dispatcher = dispatcher
        self._ui = ui
        self._clock = clock
        self._lock = RLock()
        self._positions: deque[OverlayPosition] = deque(maxlen=128)
        self._motions: deque[OverlayMotion] = deque(maxlen=256)
        self._guidance: deque[OverlayGuidance] = deque(maxlen=128)
        self._active = False
        self._closed = False
        self._enabled = True
        self._generation = 0
        self._timer: object | None = None
        self._frame: float | None = None
        self._last_state: NavigationOverlayState | None = None
        ui.set_navigation_overlay_handler(self)
        ui.set_navigation_overlay(NavigationOverlayState())

    def update_position(self, sample: OverlayPosition) -> None:
        self._append(self._positions, sample)

    def update_motion(self, sample: OverlayMotion) -> None:
        self._append(self._motions, sample)

    def update_guidance(self, sample: OverlayGuidance) -> None:
        self._append(self._guidance, sample)

    def _append(self, history: deque[Sample], sample: Sample) -> None:
        with self._lock:
            if self._closed or not math.isfinite(sample.timestamp_s):
                return
            if history and sample.timestamp_s <= history[-1].timestamp_s:
                return
            history.append(sample)

    def set_frame(self, timestamp_s: float | None) -> None:
        """Observe the camera frame that the frontend has just displayed."""
        if self._closed:
            return
        self._frame = timestamp_s
        if self._active:
            self._publish()

    def request_activate(self) -> None:
        if self._closed or self._active:
            return
        self._active = True
        self._generation += 1
        self._publish()
        self._schedule()

    def request_deactivate(self) -> None:
        self._active = False
        self._generation += 1
        self._frame = None
        if self._timer is not None:
            self._dispatcher.cancel_ui_callback(self._timer)
            self._timer = None

    def request_enabled(self, enabled: bool) -> None:
        if self._closed:
            return
        self._enabled = enabled
        if self._active:
            self._publish()

    def close(self) -> None:
        if self._closed:
            return
        self.request_deactivate()
        with self._lock:
            self._closed = True
            self._positions.clear()
            self._motions.clear()
            self._guidance.clear()
        self._ui.set_navigation_overlay_handler(None)

    def _schedule(self) -> None:
        if self._closed or not self._active:
            return
        generation = self._generation
        def tick() -> None:
            if self._closed or not self._active or generation != self._generation:
                return
            self._timer = None
            self._publish()
            self._schedule()
        self._timer = self._dispatcher.schedule_ui_callback(250, tick)

    @staticmethod
    def _select(history: deque[Sample], frame: float) -> Sample | None:
        return next((sample for sample in reversed(history) if sample.timestamp_s <= frame), None)

    def snapshot(self) -> NavigationOverlayState:
        """Build one SI snapshot with independently stale GPS, motion, and guidance."""
        now = self._clock()
        frame = self._frame
        state = NavigationOverlayState(enabled=self._enabled, frame_timestamp_s=frame)
        if frame is None:
            return state
        if not math.isfinite(frame) or frame > now + 0.1 or now - frame > 1.5:
            return replace(state, video_stale=True)
        with self._lock:
            position = self._select(self._positions, frame)
            motion = self._select(self._motions, frame)
            guidance = self._select(self._guidance, frame)
        status = OverlayGpsStatus.NO_FIX
        accuracy = None
        if position is not None:
            if now - position.timestamp_s > 3.0:
                status = OverlayGpsStatus.STALE
            elif position.is_cached:
                status = OverlayGpsStatus.CACHED
            elif position.has_fix:
                accuracy = position.accuracy_m
                status = (OverlayGpsStatus.WEAK if accuracy is not None and accuracy > 25
                          else OverlayGpsStatus.LIVE)
        speed = None
        if (motion is not None and not motion.is_cached and now - motion.timestamp_s <= 3.0
                and status in (OverlayGpsStatus.LIVE, OverlayGpsStatus.WEAK)):
            value = motion.speed_m_s
            if value is not None and math.isfinite(value) and value >= 0:
                speed = value
        state = replace(state, gps_status=status, accuracy_m=accuracy, speed_m_s=speed)
        if guidance is None:
            return state
        if now - guidance.timestamp_s > 5.0:
            return replace(state, guidance_stale=True, guidance_timestamp_s=guidance.timestamp_s)
        distance = guidance.distance_m
        if distance is not None and (not math.isfinite(distance) or distance < 0):
            distance = None
        return replace(state, instruction=guidance.instruction, turn=guidance.turn,
                       road_name=guidance.road_name, distance_m=distance,
                       off_route=guidance.off_route, complete=guidance.complete,
                       guidance_timestamp_s=guidance.timestamp_s)

    def _publish(self) -> None:
        state = self.snapshot()
        if state != self._last_state:
            self._last_state = state
            self._ui.set_navigation_overlay(state)
