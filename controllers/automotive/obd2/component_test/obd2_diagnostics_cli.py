# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Request a scheduled diagnostic scan from the automotive service."""

from __future__ import annotations

import argparse
import sys

from controllers.automotive.obd2 import Obd2DiagnosticStatus, Obd2DiagnosticsSnapshot
from services.automotive.automotive_diagnostics_client import (
    AutomotiveDiagnosticsClient,
    AutomotiveDiagnosticsCommandError,
    AutomotiveDiagnosticsUnavailableError,
)
from services.automotive.endpoints import DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read diagnostics through the running automotive service."
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT,
        help="automotive command endpoint",
    )
    parser.add_argument("--timeout-ms", type=int, default=10_000)
    return parser.parse_args()


def _state(value: bool | None, true: str, false: str) -> str:
    if value is None:
        return "UNKNOWN"
    return true if value else false


def print_snapshot(snapshot: Obd2DiagnosticsSnapshot) -> None:
    """Render a semantic diagnostic snapshot for a terminal operator."""
    print("Vehicle diagnostic snapshot")
    print(f"  MIL: {_state(snapshot.mil_on, 'ON', 'OFF')}")
    count = "UNKNOWN" if snapshot.stored_dtc_count is None else snapshot.stored_dtc_count
    print(f"  Stored DTC count: {count}")
    print(
        "  Emissions monitors: "
        + _state(snapshot.emissions_ready, "READY", "NOT READY")
    )
    ecus = ", ".join(f"0x{ecu:X}" for ecu in snapshot.responding_ecus)
    print(f"  Responding ECUs: {ecus or 'none'}")
    for status in Obd2DiagnosticStatus:
        codes = [item for item in snapshot.trouble_codes if item.status is status]
        rendered = ", ".join(
            f"{item.code} (ECU {'--' if item.ecu_id is None else f'0x{item.ecu_id:X}'})"
            for item in codes
        )
        print(f"  {status.name.title()} DTCs: {rendered or 'none'}")


def main() -> int:
    args = parse_args()
    if args.timeout_ms <= 0:
        print("ERROR: --timeout-ms must be positive", file=sys.stderr)
        return 2
    try:
        snapshot = AutomotiveDiagnosticsClient(
            args.endpoint,
            timeout_ms=args.timeout_ms,
        ).scan()
    except (AutomotiveDiagnosticsUnavailableError, AutomotiveDiagnosticsCommandError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print_snapshot(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
