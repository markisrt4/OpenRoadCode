"""Interactive device-side imagery packs; base navigation stays in the map builder."""

import argparse
from http.client import IncompleteRead
from zipfile import BadZipFile
from pathlib import Path
import uuid

from apps.launchers.local_imagery_pack import LocalImageryPack
from tools.map_builder.builder.map_3d import PRESETS
from common.xdg_paths import openroadcode_data_dir
from development.maps.regional_imagery import download as download_overview
from development.maps.prebuilt_imagery import (read_descriptor, read_local_archive,
                                               verify_archive, fetch_archive, unpack,
                                               github_release_descriptor)

# Rectangular planning envelopes, not county boundaries. No Canadian imagery promised.
COVERAGES = {
    'metro-detroit': ('Metro Detroit overview', (-83.75, 42.0, -82.55, 42.9)),
    'detroit-midtown': ('Detroit Downtown–Midtown detail', (-83.085, 42.315, -83.025, 42.375)),
    'rochester': PRESETS['rochester'],
    'southfield': PRESETS['southfield'],
}


def imagery_directory(coverage):
    return openroadcode_data_dir('map-packs', coverage+'-imagery-active')


def install(coverage, *, update=False, artifact=None):
    """Validate a new revision before atomically switching the active symlink."""
    active = imagery_directory(coverage)
    if active.exists() and not update:
        pack = LocalImageryPack.load(active)
        print(f'Already installed: {pack.state.title}. Use --update to fetch a new revision.')
        return
    if active.exists() and not active.is_symlink():
        raise ValueError('Active pack must be a managed revision link; existing directory left untouched')
    active.parent.mkdir(parents=True, exist_ok=True)
    revision = active.parent / ('.'+coverage+'-imagery-'+uuid.uuid4().hex)
    title, bounds = COVERAGES[coverage]
    if artifact is not None:
        descriptor, source = artifact
        if isinstance(source, Path):
            verify_archive(source, descriptor)
            archive = source
        else:
            archive = fetch_archive(source, descriptor, active.with_name(active.name+'.artifacts'))
        unpack(archive, revision, bounds)
    else:
        download_overview(revision, bounds=bounds, title=title,
                          cache_directory=active.with_name(active.name+'.download'),
                          image_size=(4096,4096) if coverage != 'metro-detroit' else (2048,1536))
    LocalImageryPack.load(revision)
    pending = active.parent / ('.active-'+uuid.uuid4().hex)
    try:
        pending.symlink_to(revision.name, target_is_directory=True)
        pending.replace(active)
    finally:
        pending.unlink(missing_ok=True)
    print('Ready. Reopen Terrain in ORC. Earlier revisions are retained for recovery.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage', choices=COVERAGES)
    parser.add_argument('--update', action='store_true', help='Fetch and validate a fresh imagery revision')
    parser.add_argument('--yes', action='store_true', help='Confirm the printed plan; requires --coverage')
    parser.add_argument('--pack-manifest', help='HTTPS URL of a published .zip.json; downloads a prebuilt pack instead of contacting USGS')
    parser.add_argument('--github-release', metavar='TAG', help='Install latest or a versioned published Metro Detroit GitHub Release')
    parser.add_argument('--pack-file', type=Path, help='Install a local .zip and its adjacent .zip.json without network access')
    parser.add_argument('--build-only', type=Path, help='Build imagery into this directory for packaging; do not activate it on this host')
    args = parser.parse_args()
    if args.yes and not args.coverage:
        parser.error('--yes requires --coverage')
    if sum(bool(value) for value in (args.pack_manifest, args.github_release, args.pack_file, args.build_only)) > 1:
        parser.error('--pack-manifest, --github-release, --pack-file and --build-only cannot be combined')
    try:
        coverage = args.coverage
        if coverage is None:
            for index, (_, (title, _)) in enumerate(COVERAGES.items(), 1):
                print(f'{index}. {title}')
            choice = input(f'Choose coverage [1–{len(COVERAGES)}, Enter cancels]: ').strip()
            if not choice:
                return 0
            if not choice.isdigit() or not 1 <= int(choice) <= len(COVERAGES):
                raise ValueError(f'Choose 1–{len(COVERAGES)}')
            coverage = tuple(COVERAGES)[int(choice)-1]
        title, bounds = COVERAGES[coverage]
        print(f'{title}: rectangular bounds {bounds}; not exact county boundaries.')
        manifest_url = args.pack_manifest
        if args.github_release:
            if coverage != 'metro-detroit':
                raise ValueError('Published GitHub releases currently support metro-detroit only')
            manifest_url = github_release_descriptor(args.github_release)
            print(f'Published release descriptor: {manifest_url}')
        artifact = read_descriptor(manifest_url, coverage) if manifest_url else None
        if args.pack_file:
            artifact = read_local_archive(args.pack_file, coverage)
        if artifact:
            print(f"Prebuilt imagery: {artifact[0]['title']} · {artifact[0]['bytes']/1048576:.2f} MiB archive")
            print('Local file: no download needed.' if args.pack_file else 'Download supports resume.')
            print('Archive SHA256 and image checksum are checked before activation.')
        else:
            print('Source-build mode: USGS custom exports may fail. For device installs, use --pack-manifest with a published artifact.')
            print('Layer: public-domain NAIP imagery; 20 MiB maximum image payload plus source metadata.')
        if not artifact:
            if coverage != 'metro-detroit':
                print('Detail quality: 4096×4096 final pixels over selected coverage; more GPU memory than the overview.')
            print('16 smaller exports, combined locally. Completed tiles resume after interruption.')
            print('Transfer cap: 20 MiB across tiles; cache and final image temporarily use up to 40 MiB plus metadata.')
        print('Overview is coarse, not street-level detail. Inspect coverage for source gaps after installation.')
        print('No internet needed for local installation.' if args.pack_file else 'Internet required to download; viewing is offline.')
        print('Updates retain the previous revision (extra disk space).')
        print('Base map, search, routing and buildings continue through existing map-builder tools; this installs imagery only.')
        question = 'Install this local imagery pack now? [y/N] ' if args.pack_file else 'Download this imagery pack now? [y/N] '
        if not args.yes and input(question).strip().lower() != 'y':
            print('Cancelled')
            return 0
        if args.build_only:
            download_overview(args.build_only, bounds=bounds, title=title,
                              cache_directory=args.build_only.with_name(args.build_only.name+'.download'),
                              image_size=(4096,4096) if coverage != 'metro-detroit' else (2048,1536))
            LocalImageryPack.load(args.build_only)
            print(f'Validated build output: {args.build_only}. Ready for imagery_artifact packaging.')
        else:
            install(coverage, update=args.update, artifact=artifact)
        return 0
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled; active pack unchanged unless installation already completed.')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, IncompleteRead, BadZipFile) as error:
        print(f'Region imagery install failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
