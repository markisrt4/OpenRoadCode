# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe generic OBD-II diagnostic services against a live vehicle."""

from __future__ import annotations

import argparse
import sys

from controllers.automotive.obd2 import Elm327ObdAdapter
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


def _decode_mil(responses: tuple[Obd2Response, ...]) -> None:
    for response in responses:
        if not response.data:
            continue
        status = response.data[0]
        print(
            f"  ECU 0x{response.ecu_id:X}: MIL={'ON' if status & 0x80 else 'OFF'}, "
            f"stored emissions DTC count={status & 0x7F}"
        )


def _decode_dtc_word(first: int, second: int) -> str:
    families = "PCBU"
    return (
        f"{families[(first >> 6) & 0x03]}"
        f"{(first >> 4) & 0x03:X}"
        f"{first & 0x0F:X}"
        f"{(second >> 4) & 0x0F:X}"
        f"{second & 0x0F:X}"
    )


def _decode_dtcs(responses: tuple[Obd2Response, ...]) -> tuple[str, ...]:
    codes: list[str] = []
    for response in responses:
        data = response.data
        for offset in range(0, len(data) - 1, 2):
            first, second = data[offset], data[offset + 1]
            if first == 0 and second == 0:
                continue
            codes.append(_decode_dtc_word(first, second))
    return tuple(codes)


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


def main() -> int:
    args = parse_args()
    device = Elm327TcpDevice(host=args.host, port=args.port, timeout=args.timeout)
    adapter = Elm327ObdAdapter(device)

    try:
        adapter.connect()
    except (Elm327ConnectionError, Obd2Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        mil = _request(\n            device, adapter, Obd2Request(mode=0x01, pid=0x01), raw=args.raw\n        )
        _print_responses("Mode 01 PID 01 - monitor status since DTCs cleared", mil)
        _decode_mil(mil)

        for mode, label in (
            (0x03, "Mode 03 - stored DTCs"),
            (0x07, "Mode 07 - pending DTCs"),
            (0x0A, "Mode 0A - permanent DTCs"),
        ):
            try:
                responses = _request(\n                    device, adapter, Obd2Request(mode=mode), raw=args.raw\n                )
            except Obd2Error as exc:
                print(f"\n{label}\n  Unsupported/error: {exc}")
                continue
            _print_responses(label, responses)
            codes = _decode_dtcs(responses)
            print("  DTCs: " + (", ".join(codes) if codes else "none reported"))
    finally:
        adapter.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
