"""Build Michigan region imagery and tiled relief from existing NAIP/3DEP rasters.

Build-host GDAL only; packs use the existing offline installers. Missing imagery
stays transparent; incomplete terrain tiles are omitted and explicitly reported.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
import math
from pathlib import Path
import time

from PIL import Image

from apps.launchers.local_imagery_pack import LocalImageryPack
from apps.launchers.local_terrain_pack import load_terrain
from development.maps.regional_imagery import _save_overview
from development.maps.regional_terrain import terrain_tiles
from development.maps.static_region_sources import crop_source, discover_imagery, discover_terrain
from development.maps.static_tile_trial import RIGHTS, command, digest, write_json
from development.maps.terrain_regions import MICHIGAN_SHARDS
from tools.map_builder.builder.imagery_artifact import package as package_imagery
from tools.map_builder.builder.terrain_artifact import package as package_terrain


def source_crops(sources, cache, bounds, size, kind):
    cache.mkdir(parents=True, exist_ok=True)
    def crop(item):
        return crop_source(item, cache, bounds, size, kind)
    results = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        # map retains oldest-to-newest overlay ordering even with concurrent reads.
        for index, result in enumerate(executor.map(crop, sources), 1):
            results.append(result)
            print(f'{kind}: {index}/{len(sources)} source crops · {index*100/len(sources):.0f}%', flush=True)
    return [path for path, _ in results], [receipt for _, receipt in results]


def imagery_pack(root, coverage, sources, crops, *, pixels=4096):
    title, bounds = MICHIGAN_SHARDS[coverage]
    scratch = root/'processing'
    scratch.mkdir(parents=True, exist_ok=True)
    # All crops are aligned EPSG:4326 RGB+alpha rasters. VRT avoids repeatedly
    # rewriting a region-sized TIFF for every individual NAIP file.
    listing = scratch/'imagery-inputs.txt'
    listing.write_text('\n'.join(str(path.resolve()) for path in crops)+'\n')
    vrt = scratch/'imagery.vrt'
    command('gdalbuildvrt', '-overwrite', '-input_file_list', listing, vrt)
    mosaic = scratch/'imagery.tif'
    command('gdalwarp', '-overwrite', '-wm', '128', '-t_srs', 'EPSG:4326',
            '-te', *bounds, '-ts', pixels, pixels, '-r', 'bilinear',
            '-srcalpha', '-dstalpha', vrt, mosaic)
    destination = root/f'{coverage}-imagery'
    destination.mkdir(exist_ok=True)
    with Image.open(mosaic) as image:
        image.load()
        histogram = image.getchannel('A').histogram()
        fraction = (pixels*pixels-histogram[0])/(pixels*pixels)
        if fraction == 0:
            raise ValueError('Regional imagery contains no valid pixels')
        output = destination/'imagery.webp'
        _save_overview(image, output, transparent=True)
    write_json(destination/'manifest.json', dict(schema=1, image=output.name,
        title=title+' staged NAIP regional coverage', attribution='USDA NAIP / USGS · The National Map',
        bounds_deg=bounds, width=pixels, height=pixels, sha256=digest(output),
        rights='Public-domain USDA NAIP imagery', rights_reference=RIGHTS['imagery'],
        source_records=sources, usable_pixel_fraction=fraction,
        missing_coverage='Transparent pixels are source gaps or water; not qualified as complete land coverage',
        assembly='Existing raster crops; dated NAIP sources may differ by footprint'))
    LocalImageryPack.load(destination)
    return destination, dict(usable_pixel_fraction=fraction, imagery_bytes=output.stat().st_size,
                             imagery_pixels=[pixels, pixels])


def split_terrain(heights, size, root, coverage):
    """Emit endpoint-aligned 129x129 children; reject incomplete children."""
    title, bounds = MICHIGAN_SHARDS[coverage]
    if size != 1025 or len(heights) != size*size:
        raise ValueError('Regional terrain requires an endpoint-aligned 1025 grid')
    records, gaps = [], []
    for index, (tile_id, tile_bounds) in enumerate(terrain_tiles(bounds, 8)):
        row, column = divmod(index, 8)
        samples = [heights[(row*128+y)*size+column*128+x] for y in range(129) for x in range(129)]
        if any(not math.isfinite(value) or not -500 <= value <= 9000 for value in samples):
            gaps.append(dict(id=tile_id, bounds_deg=tile_bounds, reason='Missing/invalid staged DEM samples'))
            continue
        tile = root/tile_id
        tile.mkdir(parents=True, exist_ok=True)
        write_json(tile/'terrain.json', dict(width=129, height=129, heights_m=samples,
            reference_height_m=samples[len(samples)//2],
            vertical_datum='USGS 3DEP source datum unresolved; relative relief, not ellipsoid heights'))
        checksum = digest(tile/'terrain.json')
        write_json(tile/'manifest.json', dict(schema=1, title=title+' '+tile_id,
            bounds_deg=tile_bounds, attribution='USGS 3DEP · The National Map', sha256=checksum,
            rights='Public-domain USGS 3DEP', rights_reference=RIGHTS['terrain']))
        records.append(dict(id=tile_id, path=tile_id, bounds_deg=tile_bounds,
                            sha256=checksum, detail_level=0, minimum_zoom=0))
    if not records:
        raise ValueError('No complete regional terrain tiles; no terrain pack published')
    return records, gaps


def terrain_pack(root, coverage, sources, crops):
    title, bounds = MICHIGAN_SHARDS[coverage]
    west, south, east, north = bounds
    dx, dy = (east-west)/1024, (north-south)/1024
    sample_bounds = (west-dx/2, south-dy/2, east+dx/2, north+dy/2)
    scratch = root/'processing'
    scratch.mkdir(parents=True, exist_ok=True)
    listing = scratch/'terrain-inputs.txt'
    listing.write_text('\n'.join(str(path.resolve()) for path in crops)+'\n')
    vrt = scratch/'terrain.vrt'
    command('gdalbuildvrt', '-overwrite', '-srcnodata', '-9999', '-vrtnodata', '-9999',
            '-input_file_list', listing, vrt)
    grid = scratch/'terrain.tif'
    command('gdalwarp', '-overwrite', '-wm', '128', '-t_srs', 'EPSG:4326',
            '-te', *sample_bounds, '-ts', '1025', '1025', '-r', 'bilinear',
            '-ot', 'Float32', '-dstnodata', '-9999', vrt, grid)
    xyz = scratch/'terrain.xyz'
    command('gdal_translate', '-of', 'XYZ', grid, xyz)
    heights = [float(line.split()[2]) for line in xyz.read_text().splitlines()]
    destination = root/f'{coverage}-terrain'
    destination.mkdir(exist_ok=True)
    records, gaps = split_terrain(heights, 1025, destination, coverage)
    write_json(destination/'manifest.json', dict(schema=3, layers=['terrain'],
        title=title+' staged 3DEP regional relief', bounds_deg=bounds,
        attribution='USGS 3DEP · The National Map', tiles=records, maximum_zoom=16,
        source_records=sources, missing_coverage=gaps,
        rights='Public-domain USGS 3DEP', rights_reference=RIGHTS['terrain']))
    load_terrain(destination)
    return destination, dict(terrain_tiles=len(records), missing_terrain_tiles=gaps,
                             terrain_grid=[1025, 1025])


def build(output, cache, coverage):
    title, bounds = MICHIGAN_SHARDS[coverage]
    output.mkdir(parents=True, exist_ok=True)
    report = dict(status='started', coverage=coverage, bounds_deg=bounds,
                  network_transfer_bytes=None, note='Cached bytes are storage, not network transfer')
    started = time.monotonic()
    try:
        # Snapshot completed discovery, so a retry does not repeat huge catalogs.
        plan_path = cache/'source-plan.json'
        cache.mkdir(parents=True, exist_ok=True)
        if plan_path.is_file():
            plan = json.loads(plan_path.read_text())
            if plan.get('coverage') != coverage or plan.get('bounds_deg') != list(bounds):
                raise ValueError('Cached source plan coverage mismatch')
        else:
            plan = dict(coverage=coverage, bounds_deg=bounds, rights=RIGHTS,
                        imagery=discover_imagery(bounds), terrain=discover_terrain(bounds))
            write_json(plan_path, plan)
        write_json(output/'source-plan.json', plan)
        report['imagery_source_count'] = len(plan['imagery'])
        report['terrain_source_count'] = len(plan['terrain'])
        print(f'{title}: {len(plan["imagery"])} NAIP files; {len(plan["terrain"])} DEM files', flush=True)
        for kind in ('imagery', 'terrain'):
            # DEM cells include half a sample beyond the public coverage to keep
            # every tile edge on the same endpoint sample lattice.
            west, south, east, north = bounds
            dx, dy = (east-west)/1024, (north-south)/1024
            crop_bounds = bounds if kind == 'imagery' else (west-dx/2, south-dy/2, east+dx/2, north+dy/2)
            crops, receipts = source_crops(plan[kind], cache/kind, crop_bounds,
                                          4096 if kind == 'imagery' else 1025, kind)
            pack, detail = (imagery_pack(output, coverage, plan[kind], crops) if kind == 'imagery'
                            else terrain_pack(output, coverage, plan[kind], crops))
            write_json(pack/'source-receipts.json', receipts)
            packager = package_imagery if kind == 'imagery' else package_terrain
            descriptor = packager(pack, output/f'{coverage}-{kind}.zip', coverage)
            descriptor.update(build_profile='staged-region-4096px-8x8-129grid',
                              build_revision='staged-region-v1',
                              build_fingerprint=hashlib.sha256(json.dumps(
                                  dict(plan=plan, kind=kind, revision='staged-region-v1'),
                                  sort_keys=True).encode()).hexdigest())
            write_json(output/f'{coverage}-{kind}.zip.json', descriptor)
            report.update(detail)
        report['status'] = 'validated-with-explicit-coverage-gaps'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 2)
        write_json(output/'build-report.json', report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage', choices=tuple(MICHIGAN_SHARDS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    build(args.output, args.cache, args.coverage)


if __name__ == '__main__':
    main()
