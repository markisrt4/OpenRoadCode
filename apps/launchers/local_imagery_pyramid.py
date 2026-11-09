"""Read-only offline MBTiles imagery, separate from its web presentation."""

from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sqlite3

from common.xdg_paths import openroadcode_data_dir
from ui.navigation.local_imagery_state import LocalImageryState, LocalImageryPyramidState

MAX_TILE_BYTES = 512*1024
MAX_DATABASE_BYTES = 2*1024*1024*1024
PILOT_BOUNDS = {
    'detroit-midtown': (-83.085, 42.315, -83.025, 42.375),
    'auburn-hills': (-83.27, 42.625, -83.195, 42.695),
}


def _connect(database):
    return sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1', uri=True)


@dataclass(frozen=True, slots=True)
class LocalImageryPyramidPack:
    state: LocalImageryPyramidState
    database: Path

    @classmethod
    def load(cls, directory):
        root = Path(directory).resolve()
        manifest = json.loads((root/'manifest.json').read_text())
        if manifest.get('schema') != 1 or manifest.get('kind') != 'imagery-pyramid':
            raise ValueError('Unsupported imagery pyramid manifest')
        database = (root/manifest['database']).resolve()
        if not database.is_relative_to(root) or not database.is_file():
            raise ValueError('Imagery database must remain inside its pack')
        if not 0 < database.stat().st_size <= MAX_DATABASE_BYTES:
            raise ValueError('Imagery database exceeds offline limits')
        with database.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        if checksum != manifest['sha256']:
            raise ValueError('Imagery pyramid checksum mismatch')
        with closing(_connect(database)) as connection:
            metadata = dict(connection.execute('SELECT name,value FROM metadata'))
            state = LocalImageryPyramidState(LocalImageryState(manifest['title'],
                manifest['attribution'], *(math.radians(value) for value in manifest['bounds_deg'])),
                int(metadata['minzoom']), int(metadata['maxzoom']), metadata['format'])
            count, low, high, largest = connection.execute(
                'SELECT count(*),min(zoom_level),max(zoom_level),max(length(tile_data)) FROM tiles').fetchone()
            if (not 1 <= count <= 100000 or low != state.minimum_zoom or high != state.maximum_zoom
                    or largest is None or largest > MAX_TILE_BYTES):
                raise ValueError('Imagery pyramid tiles exceed declared limits')
            invalid = connection.execute('SELECT 1 FROM tiles WHERE zoom_level < 0 OR zoom_level > 18 '
                'OR tile_column < 0 OR tile_column >= (1 << zoom_level) '
                'OR tile_row < 0 OR tile_row >= (1 << zoom_level) LIMIT 1').fetchone()
            if invalid:
                raise ValueError('Imagery pyramid contains invalid tile coordinates')
        return cls(state, database)

    def tile(self, zoom, x, y):
        """Read one XYZ tile, converting MBTiles' south-origin row internally."""
        if (any(type(value) is not int for value in (zoom,x,y))
                or not self.state.minimum_zoom <= zoom <= self.state.maximum_zoom
                or not 0 <= x < 2**zoom or not 0 <= y < 2**zoom):
            raise ValueError('Invalid offline imagery tile address')
        with closing(_connect(self.database)) as connection:
            row = connection.execute('SELECT substr(tile_data,1,?) FROM tiles '
                'WHERE zoom_level=? AND tile_column=? AND tile_row=? LIMIT 1',
                (MAX_TILE_BYTES+1, zoom, x, 2**zoom-1-y)).fetchone()
        if row is None:
            return None
        if len(row[0]) > MAX_TILE_BYTES:
            raise ValueError('Offline imagery tile exceeds byte limit')
        return row[0]


def installed_imagery_pyramids():
    packs = []
    for coverage in PILOT_BOUNDS:
        directory = openroadcode_data_dir('map-packs',coverage+'-imagery-detail-active')
        if (directory/'manifest.json').is_file():
            packs.append(LocalImageryPyramidPack.load(directory))
    return tuple(packs)
