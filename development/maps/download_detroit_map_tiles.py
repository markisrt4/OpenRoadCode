"""Build bounded, resumable regional building packs with optional imagery."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from common.xdg_paths import openroadcode_data_dir
from tools.map_builder.builder.map_3d import PRESETS
from apps.launchers.local_map_tiles_pack import detroit_tiles_directory, LocalMapTilesPack
from development.maps.download_detroit_imagery import download as download_imagery
from development.maps.download_detroit_buildings import request_tile, parse_buildings

BOUNDS = (-83.085,42.315,-83.025,42.375)
ATTRIBUTION = 'USGS / USDA NAIP · © OpenStreetMap contributors · ODbL 1.0'


def tiles(bounds=BOUNDS):
    west,south,east,north = bounds
    for row in range(4):
        for col in range(2):
            yield f'r{row}-c{col}', (west+(east-west)*col/2, south+(north-south)*row/4,
                                    west+(east-west)*(col+1)/2, south+(north-south)*(row+1)/4)


def download(destination, *, bounds=BOUNDS, title="Detroit Downtown–Midtown", imagery=True):
    if destination.exists():
        LocalMapTilesPack.load(destination)
        print(f'Tile pack already installed: {destination}')
        return
    cache = destination.with_name(destination.name+'.download')
    cache.mkdir(parents=True,exist_ok=True)
    records = []
    region_bounds = bounds
    for index,(tile_id,bounds) in enumerate(tiles(bounds)):
        print(f'Tile {index+1}/8: {tile_id}',flush=True)
        directory = cache/tile_id
        directory.mkdir(exist_ok=True)
        image_dir = directory/'imagery'
        if imagery:
            download_imagery(image_dir,bounds=bounds,title=title)
        source = directory/'source-osm.json'
        if not source.exists():
            raw = request_tile(bounds)
            temporary = source.with_suffix('.tmp')
            temporary.write_bytes(raw)
            temporary.replace(source)
        buildings, skipped = parse_buildings(json.loads(source.read_bytes()),region_bounds)
        # Each complete outline belongs to one tile by mean vertex location.
        # Preserve boundary-crossing buildings without drawing them twice.
        west,south,east,north = bounds
        owned = []
        for building in buildings:
            ring = building.ring[:-1]
            lon = math.degrees(sum(p[0] for p in ring)/len(ring))
            lat = math.degrees(sum(p[1] for p in ring)/len(ring))
            if west <= lon < east and south <= lat < north:
                owned.append(building.document())
        content = json.dumps({'attribution':'© OpenStreetMap contributors · ODbL 1.0',
                              'buildings':owned}).encode()
        if len(content) > 10*1024*1024 or len(owned) > 10000:
            raise ValueError('Building tile exceeds prototype limit')
        (directory/'buildings.json').write_bytes(content)
        image_manifest = json.loads((image_dir/'manifest.json').read_text()) if imagery else {'title':title,'attribution':'© OpenStreetMap contributors · ODbL 1.0'}
        records.append({'id':tile_id,'bounds_deg':bounds,'title':image_manifest['title'],
                        'attribution':image_manifest['attribution'], 'buildings_count':len(owned),
                        'skipped':skipped,'sha256':{'buildings.json':hashlib.sha256(content).hexdigest(),
                                                **({'imagery.jpg':image_manifest['sha256']} if imagery else {})}})
    manifest = {'schema':1,'title':title, 'attribution':ATTRIBUTION if imagery else '© OpenStreetMap contributors · ODbL 1.0',
                'bounds_deg':region_bounds,'tiles':records,'downloaded_utc':datetime.now(timezone.utc).isoformat(),
                'building_license':'https://opendatacommons.org/licenses/odbl/1-0/'}
    with TemporaryDirectory(dir=destination.parent,prefix='.map-tiles-') as temporary:
        prepared = Path(temporary)/'pack'
        prepared.mkdir()
        for record in records:
            tile_id = record['id']
            source = cache/tile_id
            target = prepared/tile_id
            if imagery:
                shutil.copytree(source/'imagery',target)
            else:
                target.mkdir(parents=True)
            shutil.copy2(source/'buildings.json',target/'buildings.json')
            shutil.copy2(source/'source-osm.json',target/'source-osm.json')
        (prepared/'manifest.json').write_text(json.dumps(manifest,indent=2))
        LocalMapTilesPack.load(prepared)
        prepared.rename(destination)
    total = sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
    print(f'Installed {len(records)} tiles, {sum(record["buildings_count"] for record in records):,} outlines, {total/1024/1024:.1f} MiB (source records included).')
    print(f'Resume cache retained at {cache}; remove it after verifying the pack to reclaim duplicate storage.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--coverage',choices=('detroit-midtown','rochester','southfield'),default='detroit-midtown')
    parser.add_argument('--layer',choices=('buildings','both'),default='both')
    parser.add_argument('--download',action='store_true',help='Download after reviewing the printed plan')
    args = parser.parse_args()
    title,bounds=PRESETS[args.coverage]
    imagery=args.layer == 'both'
    destination=args.destination or (detroit_tiles_directory() if args.coverage == 'detroit-midtown' and imagery
        else openroadcode_data_dir('map-packs',args.coverage+'-buildings-v1' if not imagery else args.coverage+'-tiles-v1'))
    print(f'{title}: 8 tiles · rectangular bounds {bounds}; simple OSM outlines with tagged or estimated heights.')
    print(('Imagery cap: 160 MiB. ' if imagery else 'Buildings only: no imagery download. ')+'Caps: 160 MiB OSM source + 80 MiB geometry, plus metadata.')
    print('Actual size is usually lower but is unknown before the services respond. Installation temporarily duplicates cached data.')
    if args.download:
        try:
            download(destination,bounds=bounds,title=title,imagery=imagery)
        except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:
            parser.exit(1,f'Map tile download: {error}\n')
    else:
        print('Plan only. Add --download to install; interrupted downloads resume per tile.')


if __name__ == '__main__':
    main()
