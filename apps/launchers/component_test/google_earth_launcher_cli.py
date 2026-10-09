# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component test for the Google Earth browser launcher."""

from __future__ import annotations

import argparse
import re
import time
from tempfile import TemporaryDirectory

from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from common.logging.logging_paths import logging_file_path
from protocols.chromium.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_geolocation_bridge import EarthGeolocationBridge
from controllers.navigation.earth_input_camera_controller import EarthInputCameraController
from controllers.navigation.earth_navigation_controller import EarthNavigationController


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Google Earth through OpenRoadCode")
    parser.add_argument("--display", default=":1", help="X11 display to use")
    parser.add_argument("--latitude", type=float, default=42.3314)
    parser.add_argument("--longitude", type=float, default=-83.0458)
    parser.add_argument("--orc-gps", action="store_true", help="Follow ORC navigation bus positions; Ctrl+C stops")
    parser.add_argument("--devtools-port", type=int, default=9224, help="Dedicated GPS-test DevTools port")
    args = parser.parse_args()
    if not 1 <= args.devtools_port <= 65535:
        parser.error("--devtools-port must be between 1 and 65535")

    # A unique profile/process selector keeps an existing ORC Earth instance
    # from being mistaken for this test and prevents cleanup from stopping it.
    with TemporaryDirectory(prefix="orc-earth-standalone-") as profile:
        browser = BrowserKioskLauncher(
            url=(f"{GoogleEarthLauncher.BASE_URL}/{args.latitude},{args.longitude}"),
            process_pattern=re.escape(profile),
            profile_path=profile,
            window_class="openroadcode-earth-standalone-" + profile.rsplit("-", 1)[-1],
            kiosk=False,
            app_mode=True,
            window_position=(0, 0),
            window_size=(1024, 600),
            startup_grace_seconds=0.5,
            extra_arguments=((f"--remote-debugging-port={args.devtools_port}",
                              "--remote-debugging-address=127.0.0.1") if args.orc_gps else ()) ,
            log_file=logging_file_path("openroadcode", "earth-standalone.log"),
        )
        print(f"[*] Standalone Earth on {args.display}; log: {browser.log_file}")
        controller = None
        if args.orc_gps:
            client = ChromiumDevToolsClient(port=args.devtools_port)
            controller = EarthNavigationController(
                bridge=EarthGeolocationBridge(client), camera=EarthInputCameraController(client))
        try:
            if controller is not None:
                controller.start()
            browser.launch(args.display, print)
            if controller is None:
                print("[*] Inspect Earth in its own window. Press Enter to stop it.")
                input()
            else:
                print("[*] Following ORC GPS. Keep broker/navigation services running. Ctrl+C stops.")
                previous_status = None
                while browser.is_running():
                    controller.tick()
                    if controller.status != previous_status:
                        print("[earth-gps] " + controller.status, flush=True)
                        previous_status = controller.status
                    time.sleep(0.5)
        except KeyboardInterrupt:
            if controller is None:
                raise
        finally:
            try:
                if controller is not None:
                    controller.close()
            finally:
                browser.stop(args.display, print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
