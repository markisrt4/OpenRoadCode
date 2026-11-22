"""Build Metro Detroit OSM building tiles using ORC's existing PBF extractor."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from tools.map_builder.builder.build import _download_and_verify
from tools.map_builder.builder.geofabrik import fetch_index
from tools.map_builder.builder.map_3d import build_pack, digest, PRESETS
from tools.map_builder.builder.building_artifact import package


def michigan_region(regions):
    # The live Geofabrik index uses short IDs; older ORC fixtures use paths.
    address = 'https://download.geofabrik.de/north-america/us/michigan-latest.osm.pbf'
    matches = [region for region in regions if region.pbf_url == address]
    if len(matches) != 1:
        raise ValueError('Geofabrik catalog must contain one official Michigan PBF URL')
    return matches[0]


def build(output, cache, source=None, coverage='metro-detroit'):
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = dict(status='started', coverage=coverage,
                  note='OSM ways and assembled multipolygon relations; courtyards and building parts preserved; unknown heights use approximate 9 m blocks at close zoom')
    try:
        if source is None:
            regions = fetch_index(cache/'geofabrik-index.json', refresh=True)
            region = michigan_region(regions)
            source = _download_and_verify(region, cache_root=cache)
            report['source_url'] = region.pbf_url
        source = Path(source).resolve()
        report.update(source_sha256=digest(source), source_bytes=source.stat().st_size)
        with TemporaryDirectory(dir=output.parent, prefix='.osm-buildings-') as temporary:
            dataset = Path(temporary)
            sources = dataset/'maps/source'
            sources.mkdir(parents=True)
            (sources/source.name).symlink_to(source)
            pack = build_pack(dataset, coverage)
            manifest = json.loads((pack/'manifest.json').read_text())
            report.update(geometry_schema=manifest['schema'],
                          part_components=manifest['part_components'],
                          outlines_with_parts=manifest['outlines_with_parts'],
                          relation_components=manifest['relation_components'],
                          courtyard_components=manifest['courtyard_components'],
                          duplicate_member_ways_removed=manifest['duplicate_member_ways_removed'],
                          site_components=site_components(pack,manifest) if coverage in ('metro-detroit','mi-lower-southeast') else [],
                          height_counts=manifest['height_counts'], tiles=len(manifest['tiles']),
                          skipped_features=manifest['skipped_features'])
            descriptor = package(pack, output/(coverage+'-buildings.zip'), coverage)
            report.update(status='validated', buildings=descriptor['buildings'],
                          unpacked_bytes=descriptor['unpacked_bytes'],
                          tiles=descriptor['tiles'], archive_bytes=descriptor['bytes'],
                          height_counts=manifest['height_counts'], skipped_features=manifest['skipped_features'])
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 2)
        (output/'buildings-report.json').write_text(json.dumps(report, indent=2))
        print('Building report: '+json.dumps(report, sort_keys=True), flush=True)


def site_components(pack, manifest):
    """Report accepted Chrysler campus relation geometry for source review."""
    import math
    result = []
    for tile in manifest['tiles']:
        data = json.loads((pack/tile['id']/'buildings.json').read_text())
        for building in data['buildings']:
            if not building.get('source_id'):
                continue
            ring = building['ring_rad'][:-1]
            lon = math.degrees(sum(p[0] for p in ring)/len(ring))
            lat = math.degrees(sum(p[1] for p in ring)/len(ring))
            if -83.235 <= lon <= -83.224 and 42.651 <= lat <= 42.658:
                result.append(dict(source_id=building['source_id'],height_m=building['height_m'],
                                   height_source=building['height_source'],min_height_m=building.get('min_height_m',0),
                                   is_part=building.get('is_part',False),outline_only=building.get('outline_only',False),holes=len(building.get('holes_rad',()))))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage',choices=tuple(PRESETS),default='metro-detroit')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--source', type=Path, help='Reuse an existing local Michigan OSM PBF')
    args = parser.parse_args()
    build(args.output, args.cache, args.source,args.coverage)


if __name__ == '__main__':
    main()
