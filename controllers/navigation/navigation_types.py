from dataclasses import dataclass


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RouteRequest:
    origin: GeoPoint
    destination: GeoPoint


@dataclass(frozen=True)
class NavigationManeuver:
    instruction: str
    verbal_instruction: str | None
    distance_miles: float
    duration_seconds: float
    begin_shape_index: int
    end_shape_index: int


@dataclass(frozen=True)
class NavigationRoute:
    distance_miles: float
    duration_seconds: float
    shape: tuple[GeoPoint, ...]
    maneuvers: tuple[NavigationManeuver, ...]
