"""Install a finished OSM building pack; no PBF processing on the viewer device."""

import argparse
from pathlib import Path
import uuid

from apps.launchers.local_map_tiles_pack import LocalMapTilesPack
from common.xdg_paths import openroadcode_data_dir
from development.maps.prebuilt_imagery import read_local_archive, unpack
from tools.map_builder.builder.map_3d import PRESETS, validate_pack
from tools.map_builder.builder.building_artifact import MAX_UNPACKED_BYTES


def install(archive, *, destination=None):
    descriptor, archive = read_local_archive(archive, 'metro-detroit')
    if descriptor.get('kind') != 'buildings':
        raise ValueError('Descriptor is not a buildings artifact')
    active = destination or openroadcode_data_dir('map-packs','metro-detroit-buildings-active')
    if active.exists() and not active.is_symlink():
        raise ValueError('Active buildings path must be a managed revision link')
    active.parent.mkdir(parents=True, exist_ok=True)
    revision = active.parent/('.metro-buildings-'+uuid.uuid4().hex)
    def validate(root):
        validate_pack(root)
        LocalMapTilesPack.load(root)
    unpack(archive, revision, PRESETS['metro-detroit'][1], loader=validate,
           max_unpacked_bytes=MAX_UNPACKED_BYTES)
    pending = active.parent/('.active-buildings-'+uuid.uuid4().hex)
    try:
        pending.symlink_to(revision.name, target_is_directory=True)
        pending.replace(active)
    finally:
        pending.unlink(missing_ok=True)
    print(f'Ready: {descriptor["buildings"]:,} building outlines. Reopen Terrain in ORC.')
    print('Tagged heights and floor estimates retain separate classifications; placeholders remain hidden.')
    return active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack-file', type=Path, required=True)
    args = parser.parse_args()
    try:
        install(args.pack_file)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        parser.exit(1, f'Building install failed: {error}\n')


if __name__ == '__main__':
    main()
