"""Immutable SI state for the standalone 3D map rendering experiment."""

from dataclasses import dataclass
import math

from ui.navigation import GeoPoint


@dataclass(frozen=True, slots=True)
class CesiumViewerState:
    """A static destination; no vehicle tracking or dataset ownership."""

    destination: GeoPoint
    label: str = "Detroit"
    distance_m: float = 1500.0
    tilt_rad: float = math.pi / 4
    buildings_visible: bool = True
    references_visible: bool = False
    terrain_visible: bool = True
    pitch_step_rad: float = math.pi / 18
    maximum_tilt_rad: float = math.radians(80)

    def __post_init__(self):
        if any(type(value) is not bool for value in
               (self.buildings_visible, self.references_visible, self.terrain_visible)):
            raise ValueError("Layer visibility must be boolean")
        if not (math.isfinite(self.pitch_step_rad) and math.isfinite(self.maximum_tilt_rad)
                and 0 < self.pitch_step_rad <= self.maximum_tilt_rad < math.pi/2):
            raise ValueError("Camera pitch step and maximum tilt must be finite and above ground")
        lat, lon = self.destination.latitude_rad, self.destination.longitude_rad
        if not (math.isfinite(lat) and math.isfinite(lon)
                and -math.pi/2 <= lat <= math.pi/2 and -math.pi <= lon <= math.pi):
            raise ValueError("Destination must be finite and within geographic bounds")
        if not math.isfinite(self.distance_m) or not 100 <= self.distance_m <= 10000000:
            raise ValueError("Viewing distance must be between 100 and 10000000 metres")
        if not math.isfinite(self.tilt_rad) or not 0 <= self.tilt_rad <= math.pi/2:
            raise ValueError("Tilt must be between zero and pi/2 radians")
        if not self.label.strip() or len(self.label) > 120:
            raise ValueError("Destination label must contain 1–120 characters")

    def document(self) -> dict:
        """Serialize the presentation snapshot without browser-specific units."""
        return {"latitude_rad": self.destination.latitude_rad,
                "longitude_rad": self.destination.longitude_rad,
                "label": self.label, "distance_m": self.distance_m,
                "tilt_rad": self.tilt_rad,
                "buildings_visible": self.buildings_visible,
                "references_visible": self.references_visible,
                "terrain_visible": self.terrain_visible,
                "pitch_step_rad": self.pitch_step_rad,
                "maximum_tilt_rad": self.maximum_tilt_rad}
