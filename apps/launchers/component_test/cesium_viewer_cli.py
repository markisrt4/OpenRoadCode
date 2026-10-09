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
from common.logging.logging_paths import logging_file_path
from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState


def run(state, sdk, display, *, imagery=None):
    with ExitStack() as resources:
        server = CesiumViewerServer(sdk, state, imagery=imagery)
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
    parser.add_argument("--distance-m", type=float, default=2500)
    parser.add_argument("--sdk", type=Path, default=sdk_directory())
    parser.add_argument("--imagery", type=Path, help="Local imagery pack; default: installed Detroit pack")
    parser.add_argument("--no-imagery", action="store_true", help="Use the reference globe only")
    args = parser.parse_args()
    try:
        state = CesiumViewerState(GeoPoint(math.radians(args.latitude), math.radians(args.longitude)),
                                  label=args.label, distance_m=args.distance_m)
        directory = args.imagery or detroit_pack_directory()
        imagery = None if args.no_imagery or (args.imagery is None and not directory.exists()) else LocalImageryPack.load(directory)
        return run(state, args.sdk, args.display, imagery=imagery)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Cesium viewer: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
