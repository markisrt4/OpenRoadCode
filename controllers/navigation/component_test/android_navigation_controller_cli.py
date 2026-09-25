# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise Android IMU data through the production NavigationController."""

from __future__ import annotations

import argparse
import sys
import time

from controllers.navigation.android_navigation_sensor import AndroidNavigationSensor
from controllers.navigation.navigation_controller import NavigationController
from hardware_io.android import AndroidImu, AndroidSensorBridgeClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Monitor NavigationController attitude using an Android sensor bridge."
        )
    )
    parser.add_argument(
        "--bridge-url",
        default="http://127.0.0.1:8766",
        help="Android sensor bridge base URL. Default: http://127.0.0.1:8766",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Delay between samples in seconds. Default: 0.1",
    )
    parser.add_argument(
        "--filter-time-constant",
        type=float,
        default=0.5,
        help="Complementary-filter time constant in seconds. Default: 0.5",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.interval <= 0.0:
        print("Error: --interval must be greater than zero", file=sys.stderr)
        return 2

    client = AndroidSensorBridgeClient(base_url=args.bridge_url)
    sensor = AndroidNavigationSensor(AndroidImu(client))
    controller = NavigationController(
        sensor=sensor,
        filter_time_constant_s=args.filter_time_constant,
    )

    print(f"[*] Android bridge: {args.bridge_url}")
    print("[*] Starting NavigationController. Press Ctrl+C to stop.")

    try:
        controller.start()
        while True:
            state = controller.read_state()
            print(
                f"heading={state.heading_deg:7.2f}°  "
                f"pitch={state.pitch_deg:7.2f}°  "
                f"roll={state.roll_deg:7.2f}°"
            )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if controller.is_started:
            controller.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
