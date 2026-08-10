"""Public data types for route planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TravelMode(Enum):
    """Supported route-planning travel modes."""

    AUTO = auto()
    BICYCLE = auto()
    PEDESTRIAN = auto()
    MOTORCYCLE = auto()


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """Geographic coordinate in decimal degrees."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(
                "latitude must be between -90 and 90 degrees"
            )

        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(
                "longitude must be between -180 and 180 degrees"
            )


@dataclass(frozen=True, slots=True)
class RouteRequest:
    """Request for a route between two geographic locations."""

    origin: GeoPoint
    destination: GeoPoint
    travel_mode: TravelMode = TravelMode.AUTO


@dataclass(frozen=True, slots=True)
class RouteManeuver:
    """One maneuver in a calculated route."""

    instruction: str
    verbal_instruction: str | None

    distance_miles: float
    duration_seconds: float

    begin_shape_index: int
    end_shape_index: int


@dataclass(frozen=True, slots=True)
class RouteResult:
    """Calculated route returned by a route-planning controller."""

    distance_miles: float
    duration_seconds: float

    shape: tuple[GeoPoint, ...]
    maneuvers: tuple[RouteManeuver, ...]

