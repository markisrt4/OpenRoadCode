"""Build coarse state baselines through the existing USGS terrain downloader."""
import argparse
import json
from pathlib import Path
import time

from apps.launchers.local_terrain_pack import load_terrain
from development.maps.state_map_catalog import state_plan
from tools.map_builder.builder.terrain import download_bounds
from tools.map_builder.builder.terrain_artifact import package


def definitions(identifier):
    state = state_plan(identifier)
    # Alaska is already split at the dateline by the shared state catalog.
    return state, state['overview_regions']


def build(identifier, output, cache):
    state, regions = definitions(identifier)
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    report = dict(state=state['abbreviation'], status='started', grid_size=33,
                  profile='us-coarse-state-33-v1', source='USGS 3DEP', regions=[])
    started = time.monotonic()
    try:
        for region in regions:
            key = region['coverage']
            destination = cache/key
            download_bounds(destination, state['name']+' coarse baseline',
                            region['bounds_deg'], size=33)
            load_terrain(destination)
            descriptor = package(destination, output/(key+'-terrain.zip'), key)
            report['regions'].append(dict(coverage=key, bytes=descriptor['bytes'],
                                          sha256=descriptor['sha256']))
        report['status'] = 'validated'
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
    args = parser.parse_args()
    build(args.state, args.output, args.cache)


if __name__ == '__main__':
    main()
