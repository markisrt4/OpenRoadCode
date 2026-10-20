"""Immutable sampled ground relief in SI units, independent of its renderer."""

from dataclasses import dataclass
import math

from ui.navigation.local_imagery_state import LocalImageryState


@dataclass(frozen=True, slots=True)
class LocalTerrainState:
    """North-to-south row-major samples; original source datum is preserved."""

    coverage: LocalImageryState
    width: int
    height: int
    heights_m: tuple[float, ...]
    reference_height_m: float
    vertical_datum: str
    detail_level: int = 0
    minimum_zoom: int = 0

    def __post_init__(self):
        if not (2 <= self.width <= 129 and 2 <= self.height <= 129):
            raise ValueError("Terrain dimensions must be between 2 and 129")
        if len(self.heights_m) != self.width*self.height:
            raise ValueError("Terrain sample count does not match dimensions")
        if not all(math.isfinite(v) and -500 <= v <= 9000 for v in self.heights_m):
            raise ValueError("Terrain contains invalid or missing elevations")
        if not math.isfinite(self.reference_height_m) or not self.vertical_datum.strip():
            raise ValueError("Terrain requires a reference height and source datum")
        if type(self.detail_level) is not int or not 0 <= self.detail_level <= 8:
            raise ValueError("Terrain detail level must be between 0 and 8")
        if type(self.minimum_zoom) is not int or not 0 <= self.minimum_zoom <= 18:
            raise ValueError("Terrain minimum zoom must be between 0 and 18")

    def document(self):
        document = self.coverage.document()
        document.update(width=self.width, height=self.height, heights_m=self.heights_m,
                        reference_height_m=self.reference_height_m, vertical_datum=self.vertical_datum,
                        detail_level=self.detail_level, minimum_zoom=self.minimum_zoom,
                        display_mode="relative-relief")
        return document


@dataclass(frozen=True, slots=True)
class LocalTerrainMosaicState:
    """Bounded collection of independently validated terrain grids."""

    tiles: tuple[LocalTerrainState, ...]
    attribution: str = "USGS 3DEP · The National Map"
    maximum_zoom: int = 13

    def __post_init__(self):
        if (not 1 <= len(self.tiles) <= 64 or not self.attribution.strip()
                or type(self.maximum_zoom) is not int or not 1 <= self.maximum_zoom <= 18):
            raise ValueError("Terrain mosaic requires 1–64 attributed tiles")

    def document(self):
        lowest_detail = min(tile.detail_level for tile in self.tiles)
        baseline = [tile.reference_height_m for tile in self.tiles
                    if tile.detail_level == lowest_detail]
        reference = sum(baseline) / len(baseline)
        tiles = []
        for tile in self.tiles:
            document = tile.document()
            document["reference_height_m"] = reference
            tiles.append(document)
        return {
            "tiles": tiles,
            "attribution": self.attribution,
            "maximum_zoom": self.maximum_zoom,
            "display_mode": "relative-relief",
        }
