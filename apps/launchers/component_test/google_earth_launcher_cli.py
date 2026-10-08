# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component test for the Google Earth browser launcher."""

from __future__ import annotations

import argparse
import re
from tempfile import TemporaryDirectory

from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from common.logging.logging_paths import logging_file_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Google Earth through OpenRoadCode")
    parser.add_argument("--display", default=":1", help="X11 display to use")
    parser.add_argument("--latitude", type=float, default=42.3314)
    parser.add_argument("--longitude", type=float, default=-83.0458)
    args = parser.parse_args()

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
            log_file=logging_file_path("openroadcode", "earth-standalone.log"),
        )
        print(f"[*] Standalone Earth on {args.display}; log: {browser.log_file}")
        try:
            browser.launch(args.display, print)
            print("[*] Inspect Earth in its own window. Press Enter to stop it.")
            input()
        finally:
            browser.stop(args.display, print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
