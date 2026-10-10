# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Install optional offline terrain directly on the viewer device; no Docker."""

import argparse
from pathlib import Path

from apps.launchers.local_terrain_pack import detroit_terrain_directory, midtown_terrain_directory, pine_knob_terrain_directory, load_terrain
from tools.map_builder.builder.map_3d import PRESETS
from tools.map_builder.builder.map_3d_menu import choose_coverage
from tools.map_builder.builder.terrain import download


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage', choices=PRESETS)
    parser.add_argument('--output', type=Path, help='Override the device-owned pack directory')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation; requires --coverage')
    args = parser.parse_args()
    if args.yes and not args.coverage:
        parser.error('--yes requires --coverage')
    try:
        coverage = args.coverage or choose_coverage(layer='terrain')
        if coverage is None:
            print('Cancelled')
            return 0
        title, bounds = PRESETS[coverage]
        directories = {'detroit-downtown': detroit_terrain_directory,
                       'detroit-midtown': midtown_terrain_directory,
                       'pine-knob': pine_knob_terrain_directory}
        destination = args.output or directories[coverage]()
        print(f'Coverage: {title} · {bounds}')
        print('USGS 3DEP: 65×65 ground samples; 33×33 public EPQS fallback if the image service requires a token.')
        print('Internet needed for downloading; viewing works offline.')
        print('Source elevations in metres; scene displays relative relief, not converted ellipsoid heights.')
        print(f'Install directory: {destination}')
        if not args.yes and input('Download this optional terrain pack now? [y/N] ').strip().lower() != 'y':
            print('Cancelled')
            return 0
        download(destination, coverage)
        state = load_terrain(destination)
        print(f'Ready: {state.width}×{state.height} samples. Close and reopen the 3D viewer.')
        return 0
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled; no incomplete pack was installed.')
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as error:
        print(f'Terrain install failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
