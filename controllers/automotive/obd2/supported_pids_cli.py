# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Inspect Mode 01 OBD-II PID support using the configured automotive device."""

from __future__ import annotations

import argparse
from pathlib import Path

from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from services.automotive.automotive_service_cli import DEFAULT_RUNTIME_CONFIG, build_source

PID_NAMES = {
    0x04: "Calculated engine load",
    0x05: "Engine coolant temperature",
    0x0B: "Intake manifold absolute pressure",
    0x0C: "Engine RPM",
    0x0D: "Vehicle speed",
    0x0F: "Intake air temperature",
    0x10: "Mass air flow",
    0x11: "Throttle position",
    0x2F: "Fuel tank level input",
    0x33: "Absolute barometric pressure",
    0x42: "Control module voltage",
    0x49: "Accelerator pedal position D",
    0x5E: "Engine fuel rate",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report supported SAE J1979 Mode 01 PIDs for the configured vehicle"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_RUNTIME_CONFIG,
        help="runtime TOML containing the automotive device configuration",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="show every discovered PID, including ones without a friendly name",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()
    source = build_source(system.automotive)

    if not isinstance(source, Obd2Manager):
        raise RuntimeError(
            "configured automotive source is not a real OBD-II device; "
            "set services.automotive.input.source = \"device\""
        )

    print("OpenRoadCode OBD-II supported PID scan")
    print(f"  config: {args.config}")

    source.connect()
    try:
        supported = source.supported_pids
        if supported is None:
            print("  result: ECU did not return supported-PID bitmaps")
            return 2

        print(f"  supported Mode 01 PIDs: {len(supported)}")
        print()

        shown = sorted(supported if args.all else (pid for pid in supported if pid in PID_NAMES))
        for pid in shown:
            name = PID_NAMES.get(pid, "Unknown / not catalogued")
            print(f"  0x{pid:02X}  {name}")

        print()
        print(
            "  Engine fuel rate (0x5E): "
            + ("SUPPORTED" if 0x5E in supported else "NOT SUPPORTED")
        )
        print(
            "  Mass air flow (0x10):   "
            + ("SUPPORTED" if 0x10 in supported else "NOT SUPPORTED")
        )
        print(
            "  Fuel level (0x2F):      "
            + ("SUPPORTED" if 0x2F in supported else "NOT SUPPORTED")
        )
        return 0
    finally:
        source.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
