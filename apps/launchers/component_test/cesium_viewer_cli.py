"""Composition root for an isolated Cesium rendering experiment on Termux/X11."""

import argparse
from contextlib import ExitStack
import math
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.cesium_sdk import sdk_directory
from apps.launchers.local_imagery_pack import LocalImageryPack, detroit_pack_directory
from apps.launchers.cesium_viewer_server import CesiumViewerServer
from apps.launchers.local_terrain_pack import load_terrain, detroit_terrain_directory
from apps.launchers.local_building_pack import load_buildings, detroit_building_directory
from apps.launchers.local_map_tiles_pack import LocalMapTilesPack, detroit_tiles_directory
from common.logging.logging_paths import logging_file_path
from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState


def run(state, sdk, display, *, imagery=None, terrain=None, buildings=None, tiles=None):
    with ExitStack() as resources:
        server = CesiumViewerServer(sdk, state, imagery=imagery, terrain=terrain, buildings=buildings, tiles=tiles)
        resources.callback(server.close)
        profile = resources.enter_context(TemporaryDirectory(prefix="orc-cesium-"))
        browser = BrowserKioskLauncher(
            url=server.url, profile_path=profile, process_pattern=re.escape(profile),
            kiosk=False, app_mode=True, startup_grace_seconds=.5,
            extra_arguments=("--start-maximized",),
            log_file=logging_file_path("openroadcode", "cesium-viewer.log"))
        resources.callback(browser.stop, display, print)
        try:
            server.start()
            print(f"Viewer: {server.url} | Log: {browser.log_file}")
            browser.launch(display, print)
            while browser.is_running() and not server.close_requested.wait(.2):
                pass
        except KeyboardInterrupt:
            pass

    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--display", default=":1")
    parser.add_argument("--latitude", type=float, default=42.3314)
    parser.add_argument("--longitude", type=float, default=-83.0458)
    parser.add_argument("--label", default="Detroit")
    parser.add_argument("--distance-m", type=float, default=1500)
    parser.add_argument("--sdk", type=Path, default=sdk_directory())
    parser.add_argument("--imagery", type=Path, help="Local imagery pack; default: installed Detroit pack")
    parser.add_argument("--no-imagery", action="store_true", help="Use the reference globe only")
    parser.add_argument("--terrain", type=Path, help="Local sampled terrain pack")
    parser.add_argument("--no-terrain", action="store_true", help="Use the flat ellipsoid")
    parser.add_argument("--buildings", type=Path, help="Local building pack")
    parser.add_argument("--no-buildings", action="store_true", help="Hide building outlines")
    parser.add_argument("--tiles", type=Path, help="Local tiled imagery/building pack")
    parser.add_argument("--no-tiles", action="store_true", help="Use the original downtown packs")
    args = parser.parse_args()
    try:
        state = CesiumViewerState(GeoPoint(math.radians(args.latitude), math.radians(args.longitude)),
                                  label=args.label, distance_m=args.distance_m)
        tile_dir = args.tiles or detroit_tiles_directory()
        legacy_requested = args.no_imagery or args.no_buildings or args.imagery is not None or args.buildings is not None
        tiles = None if args.no_tiles or (args.tiles is None and (legacy_requested or not tile_dir.exists())) else LocalMapTilesPack.load(tile_dir)
        directory = args.imagery or detroit_pack_directory()
        imagery = None if tiles is not None or args.no_imagery or (args.imagery is None and not directory.exists()) else LocalImageryPack.load(directory)
        terrain_dir = args.terrain or detroit_terrain_directory()
        terrain = None if args.no_terrain or (args.terrain is None and not terrain_dir.exists()) else load_terrain(terrain_dir)
        building_dir = args.buildings or detroit_building_directory()
        buildings = None if tiles is not None or args.no_buildings or (args.buildings is None and not building_dir.exists()) else load_buildings(building_dir)
        return run(state, args.sdk, args.display, imagery=imagery, terrain=terrain, buildings=buildings, tiles=tiles)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Cesium viewer: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
