"""Renderer-independent presentation metadata for a bounded local imagery layer."""

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class LocalImageryState:
    """Coverage in radians and source credit; storage remains in the adapter."""

    title: str
    attribution: str
    west_rad: float
    south_rad: float
    east_rad: float
    north_rad: float

    def __post_init__(self):
        values = (self.west_rad, self.south_rad, self.east_rad, self.north_rad)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Imagery coverage must be finite")
        if not (-math.pi <= self.west_rad < self.east_rad <= math.pi
                and -math.pi/2 <= self.south_rad < self.north_rad <= math.pi/2):
            raise ValueError("Imagery coverage is outside geographic bounds")
        if not self.title.strip() or not self.attribution.strip():
            raise ValueError("Imagery needs a title and source attribution")

    def document(self):
        """Produce a local-layer snapshot, not provider credentials or paths."""
        return {"title": self.title, "attribution": self.attribution,
                "west_rad": self.west_rad, "south_rad": self.south_rad,
                "east_rad": self.east_rad, "north_rad": self.north_rad}


@dataclass(frozen=True, slots=True)
class LocalImageryStackState:
    """Bounded offline catalog ordered from regional background to finer detail."""

    layers: tuple[LocalImageryState, ...] = ()

    def __post_init__(self):
        if not isinstance(self.layers, tuple) or len(self.layers) > 64 or any(
                not isinstance(layer, LocalImageryState) for layer in self.layers):
            raise ValueError('Imagery stack must contain at most 64 immutable layers')

    def document(self):
        return [layer.document() for layer in self.layers]


@dataclass(frozen=True, slots=True)
class LocalImageryPyramidState:
    """Coverage and zoom bounds for offline 256-pixel Web Mercator imagery."""

    coverage: LocalImageryState
    minimum_zoom: int
    maximum_zoom: int
    image_format: str

    def __post_init__(self):
        if (not isinstance(self.coverage, LocalImageryState)
                or type(self.minimum_zoom) is not int or type(self.maximum_zoom) is not int
                or not 0 <= self.minimum_zoom <= self.maximum_zoom <= 18
                or self.image_format not in ('png', 'jpg', 'jpeg', 'webp')):
            raise ValueError('Invalid offline imagery pyramid metadata')

    def document(self):
        return dict(self.coverage.document(), minimum_zoom=self.minimum_zoom,
                    maximum_zoom=self.maximum_zoom, tile_size=256)
