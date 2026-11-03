"""Toolkit-independent geographic boundary presentation state."""

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class BoundaryRegionState:
    """One named region outline in normalized SI angular units."""

    name: str
    emphasized: bool
    rings_rad: tuple[tuple[tuple[float, float], ...], ...]

    def __post_init__(self):
        if not self.name.strip() or type(self.emphasized) is not bool:
            raise ValueError('Boundary region needs a name and semantic emphasis')
        if not isinstance(self.rings_rad, tuple) or not 1 <= len(self.rings_rad) <= 128:
            raise ValueError('Boundary region needs a bounded immutable ring collection')
        point_count = 0
        for ring in self.rings_rad:
            if not isinstance(ring, tuple) or len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError('Boundary rings must be immutable closed lines')
            point_count += len(ring)
            if any(not (math.isfinite(lon) and math.isfinite(lat)
                       and -math.pi <= lon <= math.pi
                       and -math.pi/2 <= lat <= math.pi/2)
                   for lon, lat in ring):
                raise ValueError('Boundary coordinates must be finite radians')
        if point_count > 10000:
            raise ValueError('Boundary region exceeds the presentation point limit')

    def document(self):
        return {'name': self.name, 'emphasized': self.emphasized,
                'rings_rad': self.rings_rad}


@dataclass(frozen=True, slots=True)
class BoundaryOverlayState:
    """Attributed state outlines ready for any geographic frontend."""

    regions: tuple[BoundaryRegionState, ...]
    attribution: str

    def __post_init__(self):
        if (not isinstance(self.regions, tuple) or not 1 <= len(self.regions) <= 16
                or any(not isinstance(region, BoundaryRegionState) for region in self.regions)):
            raise ValueError('Boundary overlay needs a bounded immutable region collection')
        if not self.attribution.strip() or len(self.attribution) > 240:
            raise ValueError('Boundary overlay needs concise source attribution')

    def document(self):
        return {'regions': [region.document() for region in self.regions],
                'attribution': self.attribution}
