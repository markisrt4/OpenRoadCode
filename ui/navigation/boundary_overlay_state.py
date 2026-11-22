"""Toolkit-independent geographic boundary presentation state."""

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class BoundaryRegionState:
    """One named boundary-line group in normalized SI angular units."""

    name: str
    emphasized: bool
    paths_rad: tuple[tuple[tuple[float, float], ...], ...]
    kind: str = 'state'

    def __post_init__(self):
        if (not self.name.strip() or type(self.emphasized) is not bool
                or self.kind not in {'country', 'disputed', 'state'}):
            raise ValueError('Boundary region needs a name and semantic emphasis')
        if not isinstance(self.paths_rad, tuple) or not 1 <= len(self.paths_rad) <= 512:
            raise ValueError('Boundary region needs a bounded immutable path collection')
        point_count = 0
        for path in self.paths_rad:
            if not isinstance(path, tuple) or len(path) < 2:
                raise ValueError('Boundary paths must be immutable lines')
            point_count += len(path)
            if any(not (math.isfinite(lon) and math.isfinite(lat)
                       and -math.pi <= lon <= math.pi
                       and -math.pi/2 <= lat <= math.pi/2)
                   for lon, lat in path):
                raise ValueError('Boundary coordinates must be finite radians')
        if point_count > 20000:
            raise ValueError('Boundary region exceeds the presentation point limit')

    def document(self):
        return {'name': self.name, 'kind': self.kind, 'emphasized': self.emphasized,
                'paths_rad': self.paths_rad}


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
