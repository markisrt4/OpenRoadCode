# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe generic OBD-II diagnostic services against a live vehicle."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable

from controllers.automotive.obd2 import (
    Elm327ObdAdapter,
    Obd2DiagnosticStatus,
    Obd2DiagnosticsScanner,
    Obd2DiagnosticsSnapshot,
)
from hardware_io.automotive.elm327 import Elm327ConnectionError, Elm327TcpDevice
from protocols.obd2 import Obd2Error, Obd2Request, Obd2Response


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read generic OBD-II MIL state and diagnostic trouble codes."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=35000)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument(
        "--request-rate-hz",
        type=float,
        default=6.0,
        help="maximum physical OBD request rate (default: 6)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="print the raw ELM327 response for each diagnostic request",
    )
    return parser.parse_args()


def _hex(data: bytes) -> str:
    return data.hex(" ").upper() or "<empty>"


def _print_responses(label: str, responses: tuple[Obd2Response, ...]) -> None:
    print(f"\n{label}")
    if not responses:
        print("  No data")
        return
    for response in responses:
        ecu = "--" if response.ecu_id is None else f"0x{response.ecu_id:X}"
        print(
            f"  ECU {ecu}: mode=0x{response.mode:02X}"
            + ("" if response.pid is None else f" pid=0x{response.pid:02X}")
            + f" data={_hex(response.data)}"
        )


def _request(
    device: Elm327TcpDevice,
    adapter: Elm327ObdAdapter,
    request: Obd2Request,
    *,
    raw: bool,
) -> tuple[Obd2Response, ...]:
    if not raw:
        return adapter.request(request)

    command = f"{request.mode:02X}"
    if request.pid is not None:
        command += f"{request.pid:02X}"
    elm_response = device.send_command(command)
    print(f"  ELM327 raw {command}: {elm_response.raw!r}")
    if elm_response.lines:
        print(f"  ELM327 lines: {elm_response.lines!r}")
    return adapter._parse_response(request, elm_response)


def run_scheduled_scan(
    request: Callable[[Obd2Request], tuple[Obd2Response, ...]],
    *,
    request_rate_hz: float,
    sleep: Callable[[float], None] = time.sleep,
) -> Obd2DiagnosticsSnapshot:
    """Run one semantic scan without exceeding the physical request budget."""
    if request_rate_hz <= 0:
        raise ValueError("request_rate_hz must be positive")
    session = Obd2DiagnosticsScanner.create_session()
    interval_s = 1.0 / request_rate_hz
    first = True
    while (next_request := session.next_request) is not None:
        if not first:
            sleep(interval_s)
        first = False
        try:
            responses = request(next_request)
        except Obd2Error as exc:
            print(
                f"  Mode {next_request.mode:02X} unsupported/error: {exc}",
                file=sys.stderr,
            )
            responses = ()
        session.accept(responses)
    return session.snapshot()


def _state(value: bool | None, true: str, false: str) -> str:
    if value is None:
        return "UNKNOWN"
    return true if value else false


def _print_snapshot(snapshot: Obd2DiagnosticsSnapshot) -> None:
    print("\nSemantic diagnostic snapshot")
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
    if args.request_rate_hz <= 0:
        print("ERROR: --request-rate-hz must be positive", file=sys.stderr)
        return 2
    device = Elm327TcpDevice(host=args.host, port=args.port, timeout=args.timeout)
    adapter = Elm327ObdAdapter(device)

    try:
        adapter.connect()
    except (Elm327ConnectionError, Obd2Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        snapshot = run_scheduled_scan(
            lambda request: _request(
                device,
                adapter,
                request,
                raw=args.raw,
            ),
            request_rate_hz=args.request_rate_hz,
        )
        _print_snapshot(snapshot)
    finally:
        adapter.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
