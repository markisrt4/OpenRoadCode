"""Immutable renderer-neutral state for an active navigation route."""

from dataclasses import dataclass
import math

from ui.navigation.map_ui_if import GeoPoint, RouteGeometry


@dataclass(frozen=True, slots=True)
class RouteOverlayState:
    """Complete route replacement consumed by map renderers."""

    geometry: RouteGeometry = RouteGeometry()
    destination: GeoPoint | None = None
    maneuver: GeoPoint | None = None
    instruction: str | None = None
    off_route: bool = False
    route_complete: bool = False

    def __post_init__(self):
        if len(self.geometry.points) > 4096:
            raise ValueError("Route overlay supports at most 4096 points")
        for point in (*self.geometry.points, self.destination, self.maneuver):
            if point is None:
                continue
            if (not math.isfinite(point.latitude_rad)
                    or not math.isfinite(point.longitude_rad)
                    or abs(point.latitude_rad) > math.pi / 2
                    or abs(point.longitude_rad) > math.pi):
                raise ValueError("Route overlay contains an invalid point")
        if self.instruction is not None and len(self.instruction) > 240:
            raise ValueError("Route instruction is too long")

    def document(self):
        def point(value):
            return None if value is None else {
                "latitude_rad": value.latitude_rad,
                "longitude_rad": value.longitude_rad,
            }
        return {
            "points": [point(value) for value in self.geometry.points],
            "destination": point(self.destination),
            "maneuver": point(self.maneuver),
            "instruction": self.instruction or "",
            "off_route": self.off_route,
            "route_complete": self.route_complete,
        }
