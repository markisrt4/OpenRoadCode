# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Prefer recent primary fixes while allowing an explicitly shared host fix."""

from __future__ import annotations

import logging
import math
import threading
from collections.abc import Callable
from time import monotonic

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_source_if import PositionSourceIf, PositionStateCallback


class FallbackPositionSource(PositionSourceIf):
    """Run both sources; stale or invalid primary reports cannot suppress fallback."""

    def __init__(
        self,
        primary: PositionSourceIf,
        fallback: PositionSourceIf,
        *,
        freshness_s: float = 10.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if not math.isfinite(freshness_s) or freshness_s <= 0:
            raise ValueError("freshness_s must be finite and positive")
        self._primary, self._fallback = primary, fallback
        self._freshness_s, self._clock = freshness_s, clock
        self._lifecycle_lock = threading.RLock()
        self._delivery_lock = threading.RLock()
        self._callback: PositionStateCallback | None = None
        self._generation = 0
        self._primary_at: float | None = None

    def start(self, callback: PositionStateCallback) -> None:
        """Offer the host source even if the primary cannot connect at startup."""
        with self._lifecycle_lock:
            with self._delivery_lock:
                if self._callback is not None:
                    return
                self._generation += 1
                generation = self._generation
                self._callback = callback
                self._primary_at = None
            started = False
            for source, primary in ((self._primary, True), (self._fallback, False)):
                try:
                    source.start(lambda state, primary=primary: self._deliver(state, generation, primary))
                    started = True
                except Exception as error:
                    logging.getLogger(__name__).warning(
                        "%s position source unavailable: %s", "Primary" if primary else "Host", error
                    )
                    source.stop()
            if not started:
                self.stop()
                raise RuntimeError("Neither primary nor host position source could start")

    def stop(self) -> None:
        """Invalidate queued reports before stopping both providers."""
        with self._lifecycle_lock:
            with self._delivery_lock:
                self._generation += 1
                self._callback = None
                self._primary_at = None
            try:
                self._primary.stop()
            finally:
                self._fallback.stop()

    def _deliver(self, state: PositionState, generation: int, primary: bool) -> None:
        if (not state.has_fix or state.is_cached or state.latitude_deg is None
                or state.longitude_deg is None or not math.isfinite(state.latitude_deg)
                or not math.isfinite(state.longitude_deg)
                or not -90 <= state.latitude_deg <= 90 or not -180 <= state.longitude_deg <= 180):
            return
        with self._delivery_lock:
            if self._callback is None or generation != self._generation:
                return
            now = self._clock()
            if primary:
                self._primary_at = now
            elif self._primary_at is not None and now - self._primary_at < self._freshness_s:
                return
            self._callback(state)
