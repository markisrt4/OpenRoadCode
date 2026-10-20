# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Install optional offline terrain directly on the viewer device; no Docker."""

import argparse
from pathlib import Path
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory
import uuid
import zipfile

from apps.launchers.local_terrain_pack import detroit_terrain_directory, metro_detroit_terrain_directory, midtown_terrain_directory, pine_knob_terrain_directory, regional_terrain_directory, load_terrain
from common.xdg_paths import openroadcode_data_dir
from development.maps.install_region import COVERAGES
from development.maps.prebuilt_imagery import fetch_archive, read_descriptor, read_local_archive, verify_archive
from development.maps.regional_terrain import build as build_regional_terrain
from tools.map_builder.builder.map_3d import PRESETS
from tools.map_builder.builder.map_3d_menu import choose_coverage
from tools.map_builder.builder.terrain import download
from development.maps.terrain_regions import MICHIGAN_COVERAGES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    regional_coverages = ('metro-detroit',) + tuple(MICHIGAN_COVERAGES)
    parser.add_argument('--coverage', choices=tuple(PRESETS) + regional_coverages)
    parser.add_argument('--output', type=Path, help='Override the device-owned pack directory')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation; requires --coverage')
    parser.add_argument('--pack-manifest', help='HTTPS descriptor for a published terrain archive')
    parser.add_argument('--pack-file', type=Path, help='Local terrain archive with adjacent .json descriptor')
    parser.add_argument('--build-only', type=Path, help='Build a terrain pack without activating it')
    args = parser.parse_args()
    if args.yes and not args.coverage:
        parser.error('--yes requires --coverage')
    if sum(bool(value) for value in (args.pack_manifest, args.pack_file, args.build_only)) > 1:
        parser.error('--pack-manifest, --pack-file and --build-only cannot be combined')
    try:
        coverage = args.coverage or choose_coverage(layer='terrain')
        if coverage is None:
            print('Cancelled')
            return 0
        title, bounds = (COVERAGES[coverage] if coverage == 'metro-detroit' else
                         MICHIGAN_COVERAGES[coverage] if coverage in MICHIGAN_COVERAGES else
                         PRESETS[coverage])
        directories = {'detroit-downtown': detroit_terrain_directory,
                       'detroit-midtown': midtown_terrain_directory,
                       'pine-knob': pine_knob_terrain_directory}
        destination = args.output or (metro_detroit_terrain_directory() if coverage == 'metro-detroit'
            else regional_terrain_directory(coverage) if coverage in MICHIGAN_COVERAGES
            else directories[coverage]() if coverage in directories else openroadcode_data_dir('map-packs',coverage+'-terrain-v1'))
        print(f'Coverage: {title} · {bounds}')
        if coverage == 'metro-detroit':
            print('USGS 3DEP: streamed overview, 200 m-class regional, and focus-area LOD grids.')
        elif coverage in MICHIGAN_COVERAGES:
            print('USGS 3DEP: 64 resumable 129×129 grids; rectangular coverage includes water and neighboring areas.')
        else:
            print('USGS 3DEP: one grid for the selected local coverage.')
        print('Internet needed for downloading; viewing works offline.')
        print('Source elevations in metres; scene displays relative relief, not converted ellipsoid heights.')
        print(f'Install directory: {destination}')
        if not args.yes and input('Download this optional terrain pack now? [y/N] ').strip().lower() != 'y':
            print('Cancelled')
            return 0
        artifact = read_local_archive(args.pack_file, coverage) if args.pack_file else (
            read_descriptor(args.pack_manifest, coverage) if args.pack_manifest else None
        )
        installed = args.build_only or destination
        if artifact:
            descriptor, source = artifact
            if descriptor.get('kind') != 'terrain':
                raise ValueError('Descriptor is not a terrain artifact')
            archive = source if isinstance(source, Path) else fetch_archive(
                source, descriptor, destination.with_name(destination.name + '.artifacts'))
            verify_archive(archive, descriptor)
            _install_archive(archive, destination)
            installed = destination
        elif coverage in regional_coverages:
            target = args.build_only or destination
            build_regional_terrain(target, coverage=coverage)
        else:
            download(args.build_only or destination, coverage)
        state = load_terrain(installed)
        detail = (f'{len(state.tiles)} tiled grids' if hasattr(state, 'tiles')
                  else f'{state.width}×{state.height} samples')
        action = 'Pack built.' if args.build_only else 'Close and reopen the 3D viewer.'
        print(f'Ready: {detail}. {action}')
        return 0
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled; no incomplete pack was installed.')
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as error:
        print(f'Terrain install failed: {error}')
        return 1


def _install_archive(archive: Path, active: Path) -> None:
    active.parent.mkdir(parents=True, exist_ok=True)
    revision = active.parent / ('.terrain-' + uuid.uuid4().hex)
    with TemporaryDirectory(dir=active.parent, prefix='.terrain-unpack-') as temporary:
        root = Path(temporary) / 'pack'
        root.mkdir()
        with zipfile.ZipFile(archive) as source:
            members = source.infolist()
            if len(members) > 4096 or sum(item.file_size for item in members) > 64*1024*1024:
                raise ValueError('Terrain archive exceeds extraction limits')
            names = set()
            for item in members:
                path = PurePosixPath(item.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                        or not path.parts or item.filename in names
                        or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('Unsafe terrain archive entry')
                names.add(item.filename)
                target = root.joinpath(*path.parts)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(item) as incoming, target.open('xb') as outgoing:
                        while chunk := incoming.read(65536):
                            outgoing.write(chunk)
        load_terrain(root)
        root.rename(revision)
    pending = active.parent / ('.active-terrain-' + uuid.uuid4().hex)
    pending.symlink_to(revision.name, target_is_directory=True)
    pending.replace(active)


if __name__ == '__main__':
    raise SystemExit(main())
