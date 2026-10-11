"""Interactive device-side imagery packs; base navigation stays in the map builder."""

import argparse
from pathlib import Path
import uuid

from apps.launchers.local_imagery_pack import LocalImageryPack
from common.xdg_paths import openroadcode_data_dir
from development.maps.download_detroit_imagery import download

# Rectangular planning envelopes, not county boundaries. No Canadian imagery promised.
COVERAGES = {
    'metro-detroit': ('Metro Detroit overview', (-83.75, 42.0, -82.55, 42.9)),
    'detroit-midtown': ('Detroit Downtown–Midtown detail', (-83.085, 42.315, -83.025, 42.375)),
}


def imagery_directory(coverage):
    return openroadcode_data_dir('map-packs', coverage+'-imagery-active')


def install(coverage, *, update=False):
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
    download(revision, bounds=bounds, title=title)
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
    args = parser.parse_args()
    if args.yes and not args.coverage:
        parser.error('--yes requires --coverage')
    try:
        coverage = args.coverage
        if coverage is None:
            for index, (_, (title, _)) in enumerate(COVERAGES.items(), 1):
                print(f'{index}. {title}')
            choice = input('Choose coverage [1/2, Enter cancels]: ').strip()
            if not choice:
                return 0
            if choice not in ('1', '2'):
                raise ValueError('Choose 1 or 2')
            coverage = tuple(COVERAGES)[int(choice)-1]
        title, bounds = COVERAGES[coverage]
        print(f'{title}: rectangular bounds {bounds}; not exact county boundaries.')
        print('Layer: public-domain NAIP imagery, 2048×1536 pixels; 20 MiB maximum image payload plus source metadata.')
        print('Overview is coarse, not street-level detail. Inspect coverage for source gaps after installation.')
        print('Internet required to download; viewing is offline. Updates retain the previous revision (extra disk space).')
        print('Base map, search, routing and buildings continue through existing map-builder tools; this installs imagery only.')
        if not args.yes and input('Download this imagery pack now? [y/N] ').strip().lower() != 'y':
            print('Cancelled')
            return 0
        install(coverage, update=args.update)
        return 0
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled; active pack unchanged unless installation already completed.')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(f'Region imagery install failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
