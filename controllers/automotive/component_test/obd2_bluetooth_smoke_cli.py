#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify a Bluetooth ELM327 reader through the decoded OBD-II stack."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import fields
from pathlib import Path

from controllers.automotive.obd2 import Elm327ObdAdapter, Obd2Manager
from controllers.automotive.vehicle_state import VehicleState
from hardware_io.automotive.elm327 import (
    Elm327CommandError,
    Elm327ConnectionError,
    Elm327Device,
)
from protocols.obd2 import Obd2Error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/rfcomm0")
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--rate", type=float, default=0.5)
    args = parser.parse_args()
    if args.samples < 1 or args.samples > 100:
        parser.error("--samples must be between 1 and 100")
    if args.rate < 0 or args.rate > 60:
        parser.error("--rate must be between 0 and 60 seconds")
    return args


def _response_text(lines: tuple[str, ...]) -> str:
    return " | ".join(lines) if lines else "<empty response>"


def _telemetry_values(state: VehicleState) -> dict[str, float]:
    return {
        field.name: value
        for field in fields(state)
        if field.name != "timestamp"
        and isinstance((value := getattr(state, field.name)), (int, float))
    }


def main() -> int:
    args = parse_args()
    port = Path(args.port)
    if not port.exists():
        print(
            f"FAIL [RFCOMM]: {port} does not exist. Pair/bind the adapter first.",
            file=sys.stderr,
        )
        return 2

    device = Elm327Device(port=str(port), baud=args.baud)
    manager = Obd2Manager(Elm327ObdAdapter(device))
    try:
        print(f"Connecting to {port} at {args.baud} baud...")
        device.connect()
        print("PASS [serial]: RFCOMM port opened and ELM327 initialized")

        identity = device.send_command("ATI")
        protocol = device.send_command("ATDP")
        print(f"PASS [adapter]: {_response_text(identity.lines)}")
        print(f"PASS [protocol]: {_response_text(protocol.lines)}")

        manager.connect()
        received_values: set[str] = set()
        for index in range(args.samples):
            state = manager.read_state()
            values = _telemetry_values(state)
            received_values.update(values)
            rendered = ", ".join(
                f"{name}={value:.3f}" for name, value in sorted(values.items())
            )
            print(f"Sample {index + 1}/{args.samples}: {rendered or 'no supported PID values'}")
            if index + 1 < args.samples:
                time.sleep(args.rate)

        if not received_values:
            print(
                "FAIL [OBD-II]: adapter responded, but no decoded Mode 01 PID values were returned. "
                "Turn the ignition on and confirm the adapter is connected to the vehicle.",
                file=sys.stderr,
            )
            return 3

        print(f"PASS [OBD-II]: decoded {len(received_values)} vehicle value(s)")
        return 0
    except Elm327ConnectionError as exc:
        print(f"FAIL [serial/ELM327]: {exc}", file=sys.stderr)
        return 2
    except (Elm327CommandError, Obd2Error) as exc:
        print(f"FAIL [OBD-II]: {exc}", file=sys.stderr)
        return 3
    finally:
        manager.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
