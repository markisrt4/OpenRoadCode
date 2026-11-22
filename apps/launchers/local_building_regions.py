"""Mount installed Michigan building packs as one bounded-streaming tile catalog."""
from dataclasses import replace

from common.navigation_data import navigation_data_root
from common.xdg_paths import openroadcode_data_dir
from development.maps.terrain_regions import MICHIGAN_SHARDS
from ui.navigation.local_imagery_state import LocalImageryState
from ui.navigation.local_map_tiles_state import LocalMapTilesState, MAX_MAP_TILES


def installed_regions():
    root = openroadcode_data_dir('map-packs')
    shared = navigation_data_root()/'maps/3d/packs'
    result = []
    for key in MICHIGAN_SHARDS:
        for candidate in (root/(key+'-buildings-active'),shared/key):
            if (candidate/'manifest.json').is_file():
                result.append((key,candidate))
                break
    return result


def combined_buildings(fallback):
    from apps.launchers.local_map_tiles_pack import LocalMapTilesPack
    regions = installed_regions()
    if not regions:
        return None
    managed = [path for _,path in regions]+[
        openroadcode_data_dir('map-packs','metro-detroit-buildings-active'),
        navigation_data_root()/'maps/3d/packs/metro-detroit']
    if fallback.resolve() not in {path.resolve() for path in managed}:
        return None  # Explicit custom tile-pack requests remain standalone.
    packs = [(key,LocalMapTilesPack.load(path)) for key,path in regions]
    # Southeast includes Metro Detroit. Do not draw both overlapping revisions.
    if 'mi-lower-southeast' not in dict(regions):
        candidates = (openroadcode_data_dir('map-packs','metro-detroit-buildings-active'),
                      navigation_data_root()/'maps/3d/packs/metro-detroit',fallback)
        regional_paths = {path.resolve() for _,path in regions}
        for candidate in candidates:
            if ((candidate/'manifest.json').is_file()
                    and candidate.resolve() not in regional_paths):
                packs.append(('legacy',LocalMapTilesPack.load(candidate)))
                break
    if sum(len(pack.state.tiles) for _,pack in packs) > (len(MICHIGAN_SHARDS)+1)*MAX_MAP_TILES:
        raise ValueError('Combined Michigan building catalog exceeds regional limits')
    tiles,files = [],{}
    for index,(_,pack) in enumerate(packs):
        for tile in pack.state.tiles:
            identity = f'b{index}-'+tile.tile_id
            if len(identity)>32:
                raise ValueError('Regional tile identifier too long')
            files[identity] = pack.files[tile.tile_id]
            tiles.append(replace(tile,tile_id=identity))
    coverage = LocalImageryState('Michigan regional buildings',
        '© OpenStreetMap contributors · ODbL 1.0',
        min(pack.state.coverage.west_rad for _,pack in packs),
        min(pack.state.coverage.south_rad for _,pack in packs),
        max(pack.state.coverage.east_rad for _,pack in packs),
        max(pack.state.coverage.north_rad for _,pack in packs))
    return LocalMapTilesPack(LocalMapTilesState(coverage,tuple(tiles)),files)
