"""Immutable renderer-neutral state for dynamic map search markers."""

from dataclasses import dataclass
import math

from ui.navigation.map_ui_if import MapMarker


@dataclass(frozen=True, slots=True)
class PoiOverlayState:
    """Complete dynamic POI marker replacement for every active renderer."""

    markers: tuple[MapMarker, ...] = ()
    category: str = ""
    focused_category: str | None = None

    def __post_init__(self):
        if (not isinstance(self.markers, tuple) or len(self.markers) > 250
                or any(not isinstance(marker, MapMarker) for marker in self.markers)):
            raise ValueError("POI overlay requires at most 250 immutable map markers")
        identifiers = set()
        for marker in self.markers:
            point = marker.position
            if (not marker.marker_id or len(marker.marker_id) > 160
                    or marker.marker_id in identifiers or not math.isfinite(point.latitude_rad)
                    or not math.isfinite(point.longitude_rad)
                    or abs(point.latitude_rad) > math.pi/2 or abs(point.longitude_rad) > math.pi
                    or (marker.label is not None and len(marker.label) > 120)):
                raise ValueError("POI overlay contains an invalid marker")
            identifiers.add(marker.marker_id)
        if len(self.category) > 80 or (self.focused_category is not None
                                      and len(self.focused_category) > 80):
            raise ValueError("POI overlay category is too long")

    def document(self):
        return {
            "category": self.category,
            "focused_category": self.focused_category,
            "markers": [{
                "id": marker.marker_id,
                "latitude_rad": marker.position.latitude_rad,
                "longitude_rad": marker.position.longitude_rad,
                "label": marker.label or "",
                "kind": marker.kind.name.casefold(),
            } for marker in self.markers],
        }
