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

    def __post_init__(self):
        if not (2 <= self.width <= 129 and 2 <= self.height <= 129):
            raise ValueError("Terrain dimensions must be between 2 and 129")
        if len(self.heights_m) != self.width*self.height:
            raise ValueError("Terrain sample count does not match dimensions")
        if not all(math.isfinite(v) and -500 <= v <= 9000 for v in self.heights_m):
            raise ValueError("Terrain contains invalid or missing elevations")
        if not math.isfinite(self.reference_height_m) or not self.vertical_datum.strip():
            raise ValueError("Terrain requires a reference height and source datum")

    def document(self):
        document = self.coverage.document()
        document.update(width=self.width, height=self.height, heights_m=self.heights_m,
                        reference_height_m=self.reference_height_m, vertical_datum=self.vertical_datum,
                        display_mode="relative-relief")
        return document
