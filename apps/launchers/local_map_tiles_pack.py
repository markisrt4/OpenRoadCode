"""Verified local tile mounts, with no acquisition or renderer dependencies."""
from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import re

from common.navigation_data import navigation_data_root
from common.xdg_paths import openroadcode_data_dir
from ui.navigation.local_imagery_state import LocalImageryState
from ui.navigation.local_map_tiles_state import LocalMapTile, LocalMapTilesState


def detroit_tiles_directory():
    return openroadcode_data_dir('map-packs','detroit-midtown-tiles-v1')


def preferred_tiles_directory():
    directory = navigation_data_root()/'maps/3d/packs'
    if directory.exists():
        packs = sorted(p for p in directory.iterdir() if p.is_dir() and not p.name.startswith('.')
                       and not p.name.endswith('-terrain'))
        preferred = directory/'detroit-midtown'
        if preferred in packs:
            return preferred
        if packs:
            return packs[0]
    return detroit_tiles_directory()


def coverage(title, attribution, bounds):
    return LocalImageryState(title,attribution,*(math.radians(v) for v in bounds))


@dataclass(frozen=True)
class LocalMapTilesPack:
    state: LocalMapTilesState
    files: dict

    @classmethod
    def load(cls, directory):
        root = Path(directory).resolve()
        manifest = json.loads((root/'manifest.json').read_text())
        if manifest.get('schema') != 1 or not 1 <= len(manifest['tiles']) <= 32:
            raise ValueError('Unsupported or oversized tile pack')
        state = coverage(manifest['title'],manifest['attribution'],manifest['bounds_deg'])
        files, tiles = {}, []
        for tile in manifest['tiles']:
            tile_id = tile['id']
            if not re.fullmatch(r'[a-z0-9-]{1,32}',tile_id) or tile_id in files:
                raise ValueError('Invalid or duplicate tile identifier')
            local = coverage(tile['title'],tile['attribution'],tile['bounds_deg'])
            if not (state.west_rad <= local.west_rad < local.east_rad <= state.east_rad
                    and state.south_rad <= local.south_rad < local.north_rad <= state.north_rad):
                raise ValueError('Tile outside pack coverage')
            count = tile['buildings_count']
            if type(count) is not int or not 0 <= count <= 10000:
                raise ValueError('Invalid tile building count')
            mounted = {}
            assets = [('buildings.json',10*1024*1024)]
            if 'imagery.jpg' in tile['sha256']:
                assets.append(('imagery.jpg',20*1024*1024))
            for name, limit in assets:
                path = (root/tile_id/name).resolve()
                if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > limit:
                    raise ValueError('Tile asset outside pack or oversized')
                with path.open('rb') as stream:
                    digest = hashlib.file_digest(stream,'sha256').hexdigest()
                if digest != tile['sha256'][name]:
                    raise ValueError('Tile asset checksum mismatch')
                mounted[name] = path
            files[tile_id] = mounted
            tiles.append(LocalMapTile(tile_id,local,count,'imagery.jpg' in mounted))
        return cls(LocalMapTilesState(state,tuple(tiles)),files)


def load_viewer_tiles(directory):
    """Reuse matching previously downloaded aerial tiles with builder-owned geometry."""
    pack = LocalMapTilesPack.load(directory)
    cached = detroit_tiles_directory()
    if any(t.imagery_available for t in pack.state.tiles) or not cached.exists() or cached.resolve() == Path(directory).resolve():
        return pack
    imagery = LocalMapTilesPack.load(cached)
    tiles, files = [], {key:dict(value) for key,value in pack.files.items()}
    for tile in pack.state.tiles:
        matching = next((other for other in imagery.state.tiles if other.imagery_available
            and all(math.isclose(getattr(tile.coverage,k),getattr(other.coverage,k),abs_tol=1e-10)
                    for k in ('west_rad','south_rad','east_rad','north_rad'))),None)
        if matching is not None:
            files[tile.tile_id]['imagery.jpg'] = imagery.files[matching.tile_id]['imagery.jpg']
            tile = replace(tile,coverage=matching.coverage,imagery_available=True)
        tiles.append(tile)
    return LocalMapTilesPack(replace(pack.state,tiles=tuple(tiles)),files)
