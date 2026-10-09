"""Immutable building geometry in radians and heights in metres."""
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class LocalBuilding:
    ring: tuple[tuple[float, float], ...]
    height_m: float
    height_source: str

    def __post_init__(self):
        if not 4 <= len(self.ring) <= 2000 or self.ring[0] != self.ring[-1]:
            raise ValueError("Building outline must be a bounded closed ring")
        if any(not math.isfinite(v) for point in self.ring for v in point):
            raise ValueError("Building coordinates must be finite")
        if any(not (-math.pi <= lon <= math.pi and -math.pi/2 <= lat <= math.pi/2)
               for lon, lat in self.ring):
            raise ValueError("Building coordinates outside geographic bounds")
        if not math.isfinite(self.height_m) or not 1 <= self.height_m <= 1000:
            raise ValueError("Invalid building height")
        if self.height_source not in ("osm-height", "levels-estimate", "placeholder"):
            raise ValueError("Unknown building height source")

    def document(self):
        return {"ring_rad": self.ring, "height_m": self.height_m,
                "height_source": self.height_source}


@dataclass(frozen=True, slots=True)
class LocalBuildingState:
    buildings: tuple[LocalBuilding, ...]
    attribution: str = "© OpenStreetMap contributors · ODbL 1.0"

    def __post_init__(self):
        if not self.buildings or len(self.buildings) > 10000 or not self.attribution.strip():
            raise ValueError("Building pack must contain 1–10000 attributed outlines")

    def document(self):
        return {"attribution": self.attribution,
                "buildings": [building.document() for building in self.buildings]}
