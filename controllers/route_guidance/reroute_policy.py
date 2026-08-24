# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Policy for deciding when sustained off-route guidance warrants rerouting."""

from __future__ import annotations

import time
from collections.abc import Callable

from .route_guidance_types import RouteGuidanceState


class ReroutePolicy:
    """Request rerouting only after a sustained off-route condition."""

    def __init__(
        self,
        *,
        off_route_delay_s: float = 3.0,
        cooldown_s: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if off_route_delay_s < 0.0:
            raise ValueError("off_route_delay_s must not be negative")
        if cooldown_s < 0.0:
            raise ValueError("cooldown_s must not be negative")

        self._off_route_delay_s = off_route_delay_s
        self._cooldown_s = cooldown_s
        self._clock = clock
        self._off_route_since: float | None = None
        self._last_reroute_at: float | None = None
        self._reroute_pending = False

    def update(self, state: RouteGuidanceState) -> bool:
        """Return True once when current state warrants a reroute request."""
        now = self._clock()

        if state.route_complete or not state.off_route:
            self._off_route_since = None
            return False

        if self._off_route_since is None:
            self._off_route_since = now

        if self._reroute_pending:
            return False

        if now - self._off_route_since < self._off_route_delay_s:
            return False

        if (
            self._last_reroute_at is not None
            and now - self._last_reroute_at < self._cooldown_s
        ):
            return False

        self._reroute_pending = True
        self._last_reroute_at = now
        return True

    def reroute_completed(self) -> None:
        """Clear pending state after a replacement route is installed."""
        self._reroute_pending = False
        self._off_route_since = None

    def reroute_failed(self) -> None:
        """Allow another attempt after cooldown if rerouting fails."""
        self._reroute_pending = False

    def reset(self) -> None:
        """Reset all route-session-specific policy state."""
        self._off_route_since = None
        self._last_reroute_at = None
        self._reroute_pending = False
