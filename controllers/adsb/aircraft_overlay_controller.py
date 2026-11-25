# SPDX-License-Identifier: MIT
"""Toolkit-independent aircraft presentation controller."""

from collections.abc import Iterable
from dataclasses import replace

from ui.adsb.aircraft_overlay_request_handler_if import AircraftOverlayRequestHandlerIf
from ui.adsb.aircraft_overlay_state import AircraftOverlayState, AircraftPoint
from ui.adsb.aircraft_overlay_ui_if import AircraftOverlayUiIf


class AircraftOverlayController(AircraftOverlayRequestHandlerIf):
    def __init__(self, view: AircraftOverlayUiIf, *, visible: bool = True) -> None:
        self._view = view
        self._state = AircraftOverlayState(enabled=visible)
        self._publish()

    @property
    def state(self) -> AircraftOverlayState:
        return self._state

    def _publish(self) -> None:
        self._view.set_aircraft_overlay_state(self._state)

    def set_aircraft(self, aircraft: Iterable[AircraftPoint]) -> None:
        """Replace the full snapshot, dropping selections that have expired."""
        snapshot = tuple(aircraft)
        ids = {item.icao.upper() for item in snapshot}
        selected = self._state.selected_icao
        follow = self._state.follow_icao
        self._state = replace(
            self._state,
            aircraft=snapshot,
            selected_icao=selected if selected in ids else None,
            follow_icao=follow if follow in ids else None,
        )
        self._publish()

    def request_aircraft_visible(self, visible: bool) -> None:
        self._state = replace(self._state, enabled=bool(visible))
        self._publish()

    def request_aircraft_selection(self, icao: str | None) -> None:
        icao = icao.upper() if icao else None
        if icao and icao not in {item.icao.upper() for item in self._state.aircraft}:
            icao = None
        self._state = replace(self._state, selected_icao=icao)
        self._publish()

    def request_aircraft_follow(self, icao: str | None) -> None:
        icao = icao.upper() if icao else None
        if icao and icao not in {item.icao.upper() for item in self._state.aircraft}:
            icao = None
        self._state = replace(self._state, follow_icao=icao)
        self._publish()

    def request_aircraft_replay(self) -> None:
        self._publish()
