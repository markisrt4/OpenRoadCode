"""Build coarse baselines with the existing staged-raster discovery/crop pipeline."""
import argparse
import json
from pathlib import Path
import time

from apps.launchers.local_terrain_pack import load_terrain
from development.maps.state_map_catalog import state_plan
from development.maps.static_region_sources import discover_terrain
from development.maps.static_region_build import source_crops, terrain_pack
from development.maps.static_tile_trial import write_json
from tools.map_builder.builder.terrain_artifact import package


def definitions(identifier):
    state = state_plan(identifier)
    # Alaska is already split at the dateline by the shared state catalog.
    return state, state['overview_regions']


DATASET = 'National Elevation Dataset (NED) 1 arc-second'
PROFILE = 'us-staged-1arc-coarse-v1'
PROBES = {'CO': (-106, 39, -105, 40), 'AK': (-150.5, 60.5, -149.5, 61.5),
          'HI': (-156, 19, -155, 20)}


def raster_region(region, title, output, cache):
    key, bounds = region['coverage'], tuple(region['bounds_deg'])
    # Reuse the endpoint-aligned grid and existing 64-tile bounds. Missing
    # children stay explicit gaps; never manufacture heights for water/no-data.
    divisions = 8
    size = divisions * 128 + 1
    west, south, east, north = bounds
    dx, dy = (east-west)/(size-1), (north-south)/(size-1)
    sample_bounds = (max(-180, west-dx/2), max(-90, south-dy/2),
                     min(180, east+dx/2), min(90, north+dy/2))
    region_cache = cache/key
    region_cache.mkdir(parents=True, exist_ok=True)
    plan_path = region_cache/'source-plan.json'
    if plan_path.is_file():
        plan = json.loads(plan_path.read_text())
        if (plan.get('profile') != PROFILE or plan.get('bounds_deg') != list(bounds)
                or plan.get('dataset') != DATASET):
            raise ValueError('Cached coarse terrain plan does not match this build')
    else:
        plan = dict(profile=PROFILE, bounds_deg=bounds, dataset=DATASET,
                    terrain=discover_terrain(sample_bounds, dataset=DATASET))
        write_json(plan_path, plan)
    crops, receipts = source_crops(plan['terrain'], region_cache/'crops', sample_bounds, size, 'terrain')
    pack, metrics = terrain_pack(output, key, plan['terrain'], crops,
                                bounds=bounds, title=title, divisions=divisions)
    write_json(pack/'source-plan.json', plan)
    write_json(pack/'source-receipts.json', receipts)
    manifest_path = pack/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.update(build_profile=PROFILE, maximum_zoom=10, source_product=DATASET,
                    coverage_complete=not metrics['missing_terrain_tiles'])
    write_json(manifest_path, manifest)
    load_terrain(pack)
    descriptor = package(pack, output/(key+'-terrain.zip'), key)
    return dict(coverage=key, bytes=descriptor['bytes'], sha256=descriptor['sha256'],
                source_dates=sorted({source['date'] for source in plan['terrain']}),
                source_date_note='Catalog publication/update dates, not verified acquisition dates',
                **metrics)


def build(identifier, output, cache, *, probe=False):
    state, regions = definitions(identifier)
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    if probe:
        abbreviation = state['abbreviation']
        if abbreviation not in PROBES:
            raise ValueError('Only reviewed mainland/Alaska/Hawaii probes are supported')
        regions = [dict(coverage='us-'+abbreviation.lower()+'-raster-probe',
                        bounds_deg=PROBES[abbreviation])]
    report = dict(state=state['abbreviation'], status='started', grid_size=1025,
                  profile=PROFILE, source=DATASET, probe=probe, regions=[])
    started = time.monotonic()
    try:
        for region in regions:
            key = region['coverage']
            report['regions'].append(raster_region(region, state['name']+' coarse baseline', output, cache))
        report['status'] = 'validated'
        report['coverage_complete'] = all(not region['missing_terrain_tiles'] for region in report['regions'])
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 2)
        (output/'us-terrain-report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--probe', action='store_true', help='Build a small representative source probe only')
    args = parser.parse_args()
    build(args.state, args.output, args.cache, probe=args.probe)


if __name__ == '__main__':
    main()
