"""Immutable building geometry in radians and heights in metres."""
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class LocalBuilding:
    ring: tuple[tuple[float, float], ...]
    height_m: float
    height_source: str
    holes: tuple[tuple[tuple[float, float], ...], ...] = ()
    source_id: str = ""
    min_height_m: float = 0.0
    is_part: bool = False
    outline_only: bool = False

    def __post_init__(self):
        rings = (self.ring, *self.holes)
        if not isinstance(self.holes, tuple) or len(self.holes) > 64 or sum(map(len,rings)) > 2000:
            raise ValueError("Building geometry exceeds bounded ring limits")
        for ring in rings:
            if (not isinstance(ring,tuple) or not 4 <= len(ring) <= 2000
                    or ring[0] != ring[-1] or any(not isinstance(p,tuple) or len(p)!=2 for p in ring)):
                raise ValueError("Building outline must be a bounded closed ring")
            if any(not isinstance(v,(int,float)) or not math.isfinite(v) for p in ring for v in p):
                raise ValueError("Building coordinates must be finite")
            if any(not (-math.pi <= lon <= math.pi and -math.pi/2 <= lat <= math.pi/2)
                   for lon,lat in ring):
                raise ValueError("Building coordinates outside geographic bounds")
            if len(set(ring[:-1])) < 3:
                raise ValueError("Building ring needs three distinct vertices")
        for hole in self.holes:
            if not all(_inside_ring(point,self.ring) for point in hole[:-1]):
                raise ValueError("Courtyard must remain inside its outer ring")
        if not isinstance(self.source_id,str) or len(self.source_id)>160 or "\x00" in self.source_id:
            raise ValueError("Invalid building source identifier")
        if not math.isfinite(self.height_m) or not 1 <= self.height_m <= 1000:
            raise ValueError("Invalid building height")
        if (not math.isfinite(self.min_height_m) or not 0 <= self.min_height_m < self.height_m
                or type(self.is_part) is not bool or type(self.outline_only) is not bool):
            raise ValueError("Invalid building base or part classification")
        if self.height_source not in ("osm-height", "levels-estimate", "placeholder"):
            raise ValueError("Unknown building height source")

    @classmethod
    def from_document(cls, building):
        """Read legacy outer-only documents and optional courtyard geometry."""
        try:
            return cls(tuple(tuple(p) for p in building["ring_rad"]),
                       building["height_m"],building["height_source"],
                       tuple(tuple(tuple(p) for p in ring) for ring in building.get("holes_rad",())),
                       building.get("source_id",""),building.get("min_height_m",0.0),
                       building.get("is_part",False),building.get("outline_only",False))
        except (TypeError,KeyError) as error:
            raise ValueError("Invalid building document") from error

    def document(self):
        result = {"ring_rad": self.ring, "height_m": self.height_m,
                  "height_source": self.height_source}
        if self.holes:
            result["holes_rad"] = self.holes
        if self.source_id:
            result["source_id"] = self.source_id
        if self.min_height_m:
            result["min_height_m"] = self.min_height_m
        if self.is_part:
            result["is_part"] = True
        if self.outline_only:
            result["outline_only"] = True
        return result


def _inside_ring(point, ring):
    """Basic courtyard containment; source area assembly remains Osmium-owned."""
    x,y = point
    inside = False
    for first,second in zip(ring,ring[1:]):
        if (first[1]>y) != (second[1]>y):
            crossing = first[0]+(second[0]-first[0])*(y-first[1])/(second[1]-first[1])
            if x < crossing:
                inside = not inside
    return inside



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
