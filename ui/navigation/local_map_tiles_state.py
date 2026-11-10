"""Immutable metadata for offline map tiles; geometry remains behind local URLs."""
from dataclasses import dataclass

from ui.navigation.local_imagery_state import LocalImageryState


@dataclass(frozen=True, slots=True)
class LocalMapTile:
    tile_id: str
    coverage: LocalImageryState
    buildings_count: int
    imagery_available: bool = True

    def document(self):
        document = {**self.coverage.document(), 'id':self.tile_id,
                'imagery_url':f'/data/tiles/{self.tile_id}/imagery.jpg' if self.imagery_available else None,
                'buildings_url':f'/data/tiles/{self.tile_id}/buildings.json',
                'buildings_count':self.buildings_count}
        return document


@dataclass(frozen=True, slots=True)
class LocalMapTilesState:
    coverage: LocalImageryState
    tiles: tuple[LocalMapTile, ...]

    def document(self):
        return {'coverage':self.coverage.document(), 'tiles':[t.document() for t in self.tiles]}
