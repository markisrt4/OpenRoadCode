# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Inspect Mode 01 OBD-II PID support using the configured automotive device."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.automotive.obd2.elm327_obd_adapter import Elm327ObdAdapter
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from hardware_io.automotive.elm327.elm327_tcp_device import Elm327TcpDevice
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
    0x44: "Commanded equivalence ratio",
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



def _is_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return "com.termux" in prefix or prefix.endswith("/com.termux/files/usr")


def _build_scan_source(config):
    """Build the configured source, with the documented Termux TCP bridge fallback."""
    input_config = config.input
    if (
        _is_termux()
        and input_config.source == "device"
        and input_config.device == "elm327"
        and input_config.transport == "serial"
    ):
        device = Elm327TcpDevice(
            host="127.0.0.1",
            port=35000,
            timeout=2.0,
        )
        return Obd2Manager(
            Elm327ObdAdapter(device),
            slow_poll_interval_seconds=input_config.slow_poll_interval_s,
        ), "termux-android-bridge tcp://127.0.0.1:35000"

    return build_source(config), (
        f"{input_config.transport}"
        if input_config.source == "device"
        else input_config.source
    )

def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()
    source, transport_description = _build_scan_source(system.automotive)

    if not isinstance(source, Obd2Manager):
        raise RuntimeError(
            "configured automotive source is not a real OBD-II device; "
            "set services.automotive.input.source = \"device\""
        )

    print("OpenRoadCode OBD-II supported PID scan")
    print(f"  config: {args.config}")
    print(f"  transport: {transport_description}")

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
            "  Engine fuel rate (0x5E):       "
            + ("SUPPORTED" if 0x5E in supported else "NOT SUPPORTED")
        )
        print(
            "  Commanded equivalence (0x44):  "
            + ("SUPPORTED" if 0x44 in supported else "NOT SUPPORTED")
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
