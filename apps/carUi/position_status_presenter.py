# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Present provider-independent position updates in the Car UI shell."""

from __future__ import annotations

from collections.abc import Callable

from controllers.navigation import PositionSourceIf, PositionState


class PositionStatusPresenter:
    """Bridge a position source into UI-thread-safe shell updates."""

    def __init__(
        self,
        *,
        source: PositionSourceIf,
        dispatch: Callable[[Callable[[], None]], None],
        set_position: Callable[[float | None, float | None], None],
        set_status: Callable[[str], None] | None = None,
        on_position_state: Callable[[PositionState], None] | None = None,
    ) -> None:
        self._source = source
        self._dispatch = dispatch
        self._set_position = set_position
        self._set_status = set_status
        self._on_position_state = on_position_state
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._publish_status("Position source starting")
        try:
            self._source.start(self._position_received)
        except Exception:
            self._running = False
            raise

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._source.stop()

    def _position_received(self, state: PositionState) -> None:
        if self._running:
            self._dispatch(lambda current=state: self._apply_position(current))

    def _apply_position(self, state: PositionState) -> None:
        if not self._running:
            return
        if self._on_position_state is not None:
            self._on_position_state(state)
        if (
            state.has_fix
            and state.latitude_deg is not None
            and state.longitude_deg is not None
        ):
            self._set_position(state.latitude_deg, state.longitude_deg)
            self._publish_status(self._format_fix_status(state))
            return
        self._set_position(None, None)
        self._publish_status("Position unavailable")

    @staticmethod
    def _format_fix_status(state: PositionState) -> str:
        if state.is_cached:
            return "Last known position restored; waiting for a live fix"
        provider = "GPS" if state.source == "gpsd" else "Position"
        if state.satellites_used is None:
            if state.accuracy_m is not None:
                return f"{provider} acquired: ±{state.accuracy_m:.0f} m"
            return f"{provider} acquired"
        visible = (
            state.satellites_visible
            if state.satellites_visible is not None
            else "?"
        )
        return (
            f"{provider} acquired: "
            f"{state.satellites_used}/{visible} satellites"
        )

    def _publish_status(self, message: str) -> None:
        if self._set_status is not None:
            self._set_status(message)
