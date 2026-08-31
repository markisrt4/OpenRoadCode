# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent map presentation contract and value objects."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.navigation.map_request_handler_if import MapRequestHandlerIf


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """Represent a geographic point using SI angular units.

    @param latitude_rad Latitude in radians.
    @param longitude_rad Longitude in radians.
    @param altitude_m Optional altitude above sea level in metres.
    """

    latitude_rad: float
    longitude_rad: float
    altitude_m: float | None = None


@dataclass(frozen=True, slots=True)
class MapViewport:
    """Describe the desired map camera.

    @param center Geographic center of the viewport.
    @param zoom_level Renderer-neutral zoom level.
    @param bearing_rad Clockwise map bearing from true north in radians.
    @param pitch_rad Camera pitch from nadir in radians.
    """

    center: GeoPoint
    zoom_level: float
    bearing_rad: float = 0.0
    pitch_rad: float = 0.0


class MapMarkerKind(Enum):
    """Identify the semantic purpose of a map marker."""

    CURRENT_POSITION = auto()
    DESTINATION = auto()
    WAYPOINT = auto()
    SEARCH_RESULT = auto()
    POINT_OF_INTEREST = auto()


@dataclass(frozen=True, slots=True)
class MapMarker:
    """Describe one semantic marker without renderer-specific imagery.

    @param marker_id Stable identifier used to update the marker.
    @param position Geographic marker position.
    @param kind Semantic marker category.
    @param label Optional user-visible marker label.
    """

    marker_id: str
    position: GeoPoint
    kind: MapMarkerKind
    label: str | None = None


@dataclass(frozen=True, slots=True)
class RouteGeometry:
    """Represent an ordered route line for map rendering.

    @param points Ordered geographic points forming the route.
    """

    points: tuple[GeoPoint, ...] = ()


@dataclass(frozen=True, slots=True)
class MapState:
    """Contain one complete renderer-neutral map snapshot.

    @param viewport Current map viewport.
    @param markers Complete marker collection.
    @param route_geometry Optional route line.
    @param style_id Optional application-defined map style identifier.
    @param follow_enabled Whether the camera should follow current position.
    @param loading Whether map resources are loading.
    @param error_message Optional user-visible map error.
    """

    viewport: MapViewport
    markers: tuple[MapMarker, ...] = ()
    route_geometry: RouteGeometry | None = None
    style_id: str | None = None
    follow_enabled: bool = True
    loading: bool = False
    error_message: str | None = None


class MapUiIf(ABC):
    """Display map state and emit renderer-neutral map requests."""

    @abstractmethod
    def set_map_state(self, state: MapState | None) -> None:
        """Replace the displayed map state or clear unavailable state.

        @param state Complete map snapshot, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_map_request_handler(
        self,
        handler: "MapRequestHandlerIf | None",
    ) -> None:
        """Connect or clear the handler for semantic map requests.

        @param handler Request consumer, or None to disconnect it.
        """
        ...
