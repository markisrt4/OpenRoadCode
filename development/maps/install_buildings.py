"""Install a finished OSM building pack; no PBF processing on the viewer device."""

import argparse
from pathlib import Path
import uuid

from apps.launchers.local_map_tiles_pack import LocalMapTilesPack
from common.xdg_paths import openroadcode_data_dir
from development.maps.prebuilt_imagery import read_local_archive, unpack
from tools.map_builder.builder.map_3d import PRESETS, validate_pack
from tools.map_builder.builder.building_artifact import limits
from development.maps.terrain_regions import MICHIGAN_SHARDS


def install(archive, *, destination=None, coverage='metro-detroit'):
    if coverage not in PRESETS:
        raise ValueError('Unknown building coverage')
    archive_limit,unpacked_limit = limits(coverage)
    descriptor, archive = read_local_archive(archive, coverage, max_archive_bytes=archive_limit)
    if descriptor.get('kind') != 'buildings':
        raise ValueError('Descriptor is not a buildings artifact')
    active = destination or openroadcode_data_dir('map-packs',coverage+'-buildings-active')
    if active.exists() and not active.is_symlink():
        raise ValueError('Active buildings path must be a managed revision link')
    active.parent.mkdir(parents=True, exist_ok=True)
    revision = active.parent/('.'+coverage+'-buildings-'+uuid.uuid4().hex)
    def validate(root):
        validate_pack(root)
        LocalMapTilesPack.load(root)
    unpack(archive, revision, PRESETS[coverage][1], loader=validate,
           max_unpacked_bytes=unpacked_limit)
    pending = active.parent/('.active-buildings-'+uuid.uuid4().hex)
    try:
        pending.symlink_to(revision.name, target_is_directory=True)
        pending.replace(active)
    finally:
        pending.unlink(missing_ok=True)
    print(f'Ready: {descriptor["buildings"]:,} building outlines. Reopen Terrain in ORC.')
    print('Tagged heights and floor estimates retain separate classifications; unknown heights render as approximate blocks at close zoom.')
    return active


def install_michigan(directory):
    """Preflight all eight archives before replacing any per-region pointer."""
    archives = []
    for coverage in MICHIGAN_SHARDS:
        found = list(Path(directory).rglob(coverage+'-buildings.zip'))
        if len(found) != 1:
            raise ValueError(f'Expected one {coverage} building archive; found {len(found)}')
        read_local_archive(found[0],coverage,max_archive_bytes=limits(coverage)[0])
        archives.append((coverage,found[0]))
    for coverage,archive in archives:
        install(archive,coverage=coverage)
    print('Michigan regional buildings installed. Reopen Terrain to load the combined catalog.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack-file', type=Path)
    parser.add_argument('--coverage',choices=tuple(PRESETS),default='metro-detroit')
    parser.add_argument('--michigan-directory',type=Path,help='Install all eight verified regional artifacts from this directory')
    args = parser.parse_args()
    try:
        if args.michigan_directory:
            install_michigan(args.michigan_directory)
        elif args.pack_file:
            install(args.pack_file,coverage=args.coverage)
        else:
            parser.error('Provide --pack-file or --michigan-directory')
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        parser.exit(1, f'Building install failed: {error}\n')


if __name__ == '__main__':
    main()
