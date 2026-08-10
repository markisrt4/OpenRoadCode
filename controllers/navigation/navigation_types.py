from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TravelMode(Enum):
    AUTO = auto()
    BICYCLE = auto()
    PEDESTRIAN = auto()
    MOTORCYCLE = auto()


@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")

        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")


@dataclass(frozen=True, slots=True)
class RouteRequest:
    origin: GeoPoint
    destination: GeoPoint
    travel_mode: TravelMode = TravelMode.AUTO


@dataclass(frozen=True, slots=True)
class NavigationManeuver:
    instruction: str
    verbal_instruction: str | None
    distance_miles: float
    duration_seconds: float
    begin_shape_index: int
    end_shape_index: int


@dataclass(frozen=True, slots=True)
class NavigationRoute:
    distance_miles: float
    duration_seconds: float
    shape: tuple[GeoPoint, ...]
    maneuvers: tuple[NavigationManeuver, ...]
