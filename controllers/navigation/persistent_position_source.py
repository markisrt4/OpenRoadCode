"""Position-source decorator that restores and records valid fixes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_snapshot_cache import PositionSnapshotCache
from controllers.navigation.position_source_if import (
    PositionSourceIf,
    PositionStateCallback,
)


class PersistentPositionSource(PositionSourceIf):
    """Publish a recent cached fix before forwarding live source updates."""

    def __init__(
        self,
        source: PositionSourceIf,
        cache: PositionSnapshotCache,
        *,
        max_age_seconds: float = 604800.0,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds cannot be negative")
        self._source = source
        self._cache = cache
        self._max_age_seconds = max_age_seconds
        self._clock = clock
        self._callback: PositionStateCallback | None = None

    def start(self, callback: PositionStateCallback) -> None:
        """Publish a recent cached fix, then start the live source."""
        self._callback = callback
        cached = self._cache.load()
        if cached is not None:
            age = (self._clock() - cached.received_at).total_seconds()
            if 0 <= age <= self._max_age_seconds:
                callback(cached)
        try:
            self._source.start(self._position_received)
        except Exception:
            self._callback = None
            raise

    def stop(self) -> None:
        """Stop the live source and release the consumer callback."""
        self._source.stop()
        self._callback = None

    def _position_received(self, state: PositionState) -> None:
        if (
            not state.is_cached
            and state.has_fix
            and state.latitude_deg is not None
            and state.longitude_deg is not None
        ):
            try:
                self._cache.store(state)
            except OSError:
                pass
        callback = self._callback
        if callback is not None:
            callback(state)
