# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Map UI adapter backed by the native OpenRoadCode map renderer."""

from __future__ import annotations

import math
from typing import Protocol

from ui.navigation import (
    MapMarkerKind,
    MapRequestHandlerIf,
    MapState,
    MapUiIf,
)


class MapRendererIf(Protocol):
    """Minimal renderer command surface required by MapRendererUi."""

    def set_camera(
        self,
        latitude: float,
        longitude: float,
        zoom: float,
        bearing: float = 0.0,
        pitch: float = 0.0,
    ) -> None:
        ...

    def set_position(self, latitude: float, longitude: float) -> None:
        ...

    def set_route(self, geojson: dict[str, object]) -> None:
        ...


class MapRendererUi(MapUiIf):
    """Translate renderer-neutral map state into native renderer commands."""

    def __init__(self, renderer: MapRendererIf) -> None:
        self._renderer = renderer
        self._request_handler: MapRequestHandlerIf | None = None

    @property
    def request_handler(self) -> MapRequestHandlerIf | None:
        """Return the currently connected semantic request handler."""

        return self._request_handler

    def set_map_request_handler(
        self,
        handler: MapRequestHandlerIf | None,
    ) -> None:
        self._request_handler = handler

    def set_map_state(self, state: MapState | None) -> None:
        if state is None:
            return

        current_position = next(
            (
                marker.position
                for marker in state.markers
                if marker.kind is MapMarkerKind.CURRENT_POSITION
            ),
            None,
        )
        if current_position is not None:
            self._renderer.set_position(
                math.degrees(current_position.latitude_rad),
                math.degrees(current_position.longitude_rad),
            )

        if state.route_geometry is not None:
            coordinates = [
                [
                    math.degrees(point.longitude_rad),
                    math.degrees(point.latitude_rad),
                ]
                for point in state.route_geometry.points
            ]
            self._renderer.set_route(
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                }
            )

        if state.follow_enabled:
            viewport = state.viewport
            self._renderer.set_camera(
                latitude=math.degrees(viewport.center.latitude_rad),
                longitude=math.degrees(viewport.center.longitude_rad),
                zoom=viewport.zoom_level,
                bearing=math.degrees(viewport.bearing_rad),
                pitch=math.degrees(viewport.pitch_rad),
            )
