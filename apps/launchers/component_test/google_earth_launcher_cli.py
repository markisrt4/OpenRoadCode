# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component test for the Google Earth browser launcher."""

from __future__ import annotations

import argparse

from apps.launchers.google_earth_launcher import GoogleEarthLauncher


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Google Earth through OpenRoadCode")
    parser.add_argument("--display", default=":1", help="X11 display to use")
    parser.add_argument("--latitude", type=float, default=42.3314)
    parser.add_argument("--longitude", type=float, default=-83.0458)
    args = parser.parse_args()

    earth = GoogleEarthLauncher()
    earth.set_location(latitude=args.latitude, longitude=args.longitude)

    print(
        f"[*] Launching Google Earth on {args.display} at "
        f"{args.latitude:.6f}, {args.longitude:.6f}"
    )
    earth.launch(args.display, print)
    print("[*] Google Earth launched. Press Enter to stop it.")
    try:
        input()
    finally:
        earth.stop(args.display, print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
