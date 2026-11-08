"""Build Metro Detroit OSM building tiles using ORC's existing PBF extractor."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from tools.map_builder.builder.build import _download_and_verify
from tools.map_builder.builder.geofabrik import fetch_index
from tools.map_builder.builder.map_3d import build_pack, digest
from tools.map_builder.builder.building_artifact import package


def michigan_region(regions):
    # The live Geofabrik index uses short IDs; older ORC fixtures use paths.
    address = 'https://download.geofabrik.de/north-america/us/michigan-latest.osm.pbf'
    matches = [region for region in regions if region.pbf_url == address]
    if len(matches) != 1:
        raise ValueError('Geofabrik catalog must contain one official Michigan PBF URL')
    return matches[0]


def build(output, cache, source=None):
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = dict(status='started', coverage='metro-detroit',
                  note='Simple closed OSM ways; complex polygons and courtyards omitted')
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
            pack = build_pack(dataset, 'metro-detroit')
            manifest = json.loads((pack/'manifest.json').read_text())
            report.update(height_counts=manifest['height_counts'], tiles=len(manifest['tiles']),
                          skipped_features=manifest['skipped_features'])
            descriptor = package(pack, output/'metro-detroit-buildings.zip', 'metro-detroit')
            report.update(status='validated', buildings=descriptor['buildings'],
                          tiles=descriptor['tiles'], archive_bytes=descriptor['bytes'],
                          height_counts=manifest['height_counts'], skipped_features=manifest['skipped_features'])
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 2)
        (output/'buildings-report.json').write_text(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--source', type=Path, help='Reuse an existing local Michigan OSM PBF')
    args = parser.parse_args()
    build(args.output, args.cache, args.source)


if __name__ == '__main__':
    main()
