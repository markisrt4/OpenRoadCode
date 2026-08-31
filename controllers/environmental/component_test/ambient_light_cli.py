# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Command-line component test for the Android ambient-light controller."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from controllers.environmental import AmbientLightController, AmbientLightControllerIf
from hardware_io.android import AndroidAmbientLight, AndroidSensorBridgeClient


def positive_float(value: str) -> float:
    """Parse a positive floating-point argument."""
    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid positive number: {value}") from exc
    if result <= 0.0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Read ambient illuminance through the Android sensor bridge."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8766",
        help="Android sensor bridge base URL. Default: http://127.0.0.1:8766",
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=0.5,
        help="Delay between samples in seconds. Default: 0.5",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Read one state and exit.",
    )
    return parser.parse_args(argv)


def run(
    controller: AmbientLightControllerIf,
    *,
    interval_s: float,
    once: bool,
) -> None:
    """Run the live ambient-light controller component test."""
    if interval_s <= 0.0:
        raise ValueError("interval must be greater than zero")

    controller.start()
    try:
        print("Ambient light controller started")
        if not once:
            print("Cover and uncover the phone light sensor to change the reading")
            print("Press Ctrl+C to stop")
        print()

        while True:
            state = controller.read_state()
            print(
                f"{state.timestamp.isoformat()}  "
                f"Illuminance: {state.illuminance_lux:9.2f} lux"
            )
            if once:
                return
            time.sleep(interval_s)
    finally:
        controller.stop()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Android-backed ambient-light controller test."""
    args = parse_args(argv)
    client = AndroidSensorBridgeClient(base_url=args.url)
    controller = AmbientLightController(AndroidAmbientLight(client))

    try:
        run(controller, interval_s=args.interval, once=args.once)
    except KeyboardInterrupt:
        print("\nStopped")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
