# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component test for the weather dashboard launcher."""

from __future__ import annotations

import argparse
from pathlib import Path

from apps.launchers.weather_dash_launcher import WeatherDashLauncher


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch the OpenRoadCode weather dashboard"
    )
    parser.add_argument("--display", default=":1", help="X11 display to use")
    parser.add_argument("--port", type=int, default=8501, help="Streamlit port")
    parser.add_argument(
        "--cache-directory",
        type=Path,
        default=Path("~/.cache/openroadcode/weather").expanduser(),
        help="Weather cache directory",
    )
    parser.add_argument(
        "--refresh-seconds",
        type=int,
        default=120,
        help="Weather refresh interval",
    )
    args = parser.parse_args()

    launcher = WeatherDashLauncher(
        port=args.port,
        cache_directory=args.cache_directory,
        refresh_seconds=args.refresh_seconds,
    )

    print(
        f"[*] Launching weather dashboard on {args.display} "
        f"using port {args.port}"
    )
    try:
        launcher.launch(args.display, print)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[!] Weather dashboard launch failed: {exc}")
        return 1

    print("[*] Weather dashboard launched. Press Enter to stop it.")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        launcher.stop(args.display, print)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
