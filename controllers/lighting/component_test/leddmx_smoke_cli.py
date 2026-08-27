# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Safely exercise an LEDDMX controller through the generic BLE transport."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from apps.common.lighting_runtime_factory import create_lighting_controller
from common.color import hex_to_rgb


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", help="BLE address; omit to discover by characteristic")
    parser.add_argument("--color", default="#2040FF", help="test color as #RRGGBB")
    parser.add_argument("--brightness", type=int, default=10, choices=range(1, 26), metavar="1..25")
    parser.add_argument("--seconds", type=float, default=2.0, help="illumination duration")
    parser.add_argument(
        "--confirm-hardware",
        action="store_true",
        help="required acknowledgement that a physical light may turn on",
    )
    args = parser.parse_args()
    if not args.confirm_hardware:
        parser.error("--confirm-hardware is required")
    if args.seconds < 0 or args.seconds > 10:
        parser.error("--seconds must be between 0 and 10")

    controller = create_lighting_controller(
        project_root=PROJECT_ROOT,
        backend="leddmx",
        address=args.address,
    )
    try:
        controller.connect().result(timeout=30)
        state = controller.current_state()
        print(f"Connected to {state.device_address or 'discovered BLE device'}")
        controller.set_brightness(args.brightness).result(timeout=5)
        controller.set_color(hex_to_rgb(args.color)).result(timeout=5)
        controller.set_power(True).result(timeout=5)
        time.sleep(args.seconds)
        return 0
    finally:
        try:
            controller.set_power(False).result(timeout=5)
        finally:
            controller.close()


if __name__ == "__main__":
    raise SystemExit(main())
