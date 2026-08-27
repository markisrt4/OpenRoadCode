# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component test for the generic browser launcher."""

from __future__ import annotations

import argparse

from apps.launchers.browser_launcher import BrowserKioskLauncher


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch a URL through BrowserKioskLauncher")
    parser.add_argument("--display", default=":1", help="X11 display to use")
    parser.add_argument("--url", default="https://openroadcode.org", help="URL to open")
    args = parser.parse_args()

    launcher = BrowserKioskLauncher(
        url=args.url,
        process_pattern=args.url,
        kiosk=False,
        app_mode=True,
        profile_path=None,
        startup_grace_seconds=1.0,
    )

    print(f"[*] Launching {args.url} on {args.display}")
    launcher.launch(args.display, print)
    print("[*] Browser launched. Press Enter to stop it.")
    try:
        input()
    finally:
        launcher.stop(args.display, print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
