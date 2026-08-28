# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component test for the SDR++ launcher."""

from __future__ import annotations

import argparse

from apps.launchers.sdrpp_launcher import SDRPPLauncher, SDRPPProfile


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch SDR++ through OpenRoadCode")
    parser.add_argument("--display", default=":1", help="X11 display to use")
    parser.add_argument("--name", default="component-test", help="Profile name")
    parser.add_argument("--mode", default="WFM", help="SDR++ mode label")
    parser.add_argument("--step-hz", type=int, default=100_000, help="Tuning step")
    parser.add_argument(
        "--frequency-hz",
        type=int,
        default=None,
        help="Optional starting frequency",
    )
    parser.add_argument(
        "--rigctl-port",
        type=int,
        default=4532,
        help="RigCTL TCP port",
    )
    parser.add_argument(
        "--rigctl-timeout",
        type=float,
        default=15.0,
        help="Seconds to wait for RigCTL",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Do not request fullscreen mode",
    )
    args = parser.parse_args()

    profile = SDRPPProfile(
        name=args.name,
        mode=args.mode,
        step_hz=args.step_hz,
        start_frequency_hz=args.frequency_hz,
    )
    launcher = SDRPPLauncher(
        profile=profile,
        fullscreen=not args.windowed,
        rigctl_port=args.rigctl_port,
        rigctl_timeout_seconds=args.rigctl_timeout,
    )

    print(f"[*] Launching SDR++ profile {args.name!r} on {args.display}")
    try:
        launcher.launch(args.display, print)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[!] SDR++ launch failed: {exc}")
        return 1

    print("[*] SDR++ launched and RigCTL is ready. Press Enter to stop it.")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        launcher.stop(args.display, print)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
