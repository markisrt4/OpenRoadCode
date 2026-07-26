#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from controllers.lighting import RgbColor
from controllers.lighting.adapters.leddmx_controller import (
    LedDmxController,
)
from controllers.lighting.parsers.leddmx_config_parser import (
    load_leddmx_config,
)
from hardware_io.bluetooth.bleak_gatt_transport import BleakGattTransport


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _rgb(value: str) -> RgbColor:
    normalized = value.strip().removeprefix("#")
    if len(normalized) != 6:
        raise argparse.ArgumentTypeError(
            "color must contain six hexadecimal digits"
        )
    try:
        channels = tuple(
            int(normalized[index:index + 2], 16)
            for index in (0, 2, 4)
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "color must contain six hexadecimal digits"
        ) from exc
    return RgbColor(*channels)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Connect to and exercise an LEDDMX BLE controller",
    )
    parser.add_argument(
        "--address",
        help="BLE address or platform identifier; overrides leddmx.toml",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="maximum seconds to wait for each operation",
    )
    command = parser.add_mutually_exclusive_group()
    command.add_argument(
        "--power",
        choices=("on", "off"),
        help="send a power command after connecting",
    )
    command.add_argument(
        "--color",
        type=_rgb,
        metavar="RRGGBB",
        help="send an RGB color after connecting",
    )
    command.add_argument(
        "--interactive",
        action="store_true",
        help="keep one connection open and accept multiple commands",
    )
    return parser.parse_args()


def _interactive(controller: LedDmxController, timeout: float) -> None:
    print("Commands: on, off, color RRGGBB, state, quit")
    while True:
        try:
            command = input("leddmx> ").strip()
        except EOFError:
            print()
            return
        if not command:
            continue
        if command in {"quit", "exit"}:
            return
        if command == "state":
            print(controller.current_state())
            continue
        if command in {"on", "off"}:
            try:
                controller.set_power(command == "on").result(timeout=timeout)
            except Exception as exc:
                print(f"Power command failed: {exc}")
            else:
                print(f"Power command sent: {command}")
            continue
        if command.lower().startswith("color "):
            try:
                color = _rgb(command.split(maxsplit=1)[1])
                controller.set_color(color).result(timeout=timeout)
            except Exception as exc:
                print(f"Color command failed: {exc}")
            else:
                print(
                    f"Color command sent: "
                    f"#{color.red:02X}{color.green:02X}{color.blue:02X}"
                )
            continue
        print("Unknown command. Use: on, off, color RRGGBB, state, quit")


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        raise SystemExit("--timeout must be greater than zero")

    config = load_leddmx_config(project_root=PROJECT_ROOT)
    target = args.address or config.address or "automatic discovery"
    print(f"Connecting to LEDDMX controller via {target}...")

    transport = BleakGattTransport(
        address=args.address or config.address,
        characteristic_uuid=config.characteristic_uuid,
        excluded_service_uuids=config.excluded_service_uuids,
        excluded_name_fragments=config.excluded_name_fragments,
        write_with_response=config.write_with_response,
        command_delay_seconds=config.command_delay_seconds,
        reconnect_delay_seconds=config.reconnect_delay_seconds,
        scan_timeout_seconds=config.scan_timeout_seconds,
        connect_timeout_seconds=config.candidate_connect_timeout_seconds,
    )
    controller = LedDmxController(transport=transport)
    try:
        controller.connect().result(timeout=args.timeout)
        print("Connected.")

        if args.interactive:
            _interactive(controller, args.timeout)
        elif args.power is not None:
            enabled = args.power == "on"
            controller.set_power(enabled).result(timeout=args.timeout)
            print(f"Power command sent: {args.power}")
        elif args.color is not None:
            controller.set_color(args.color).result(timeout=args.timeout)
            print(
                "Color command sent: "
                f"#{args.color.red:02X}{args.color.green:02X}"
                f"{args.color.blue:02X}"
            )

        print(f"State: {controller.current_state()}")
        return 0
    except Exception as exc:
        print(f"LEDDMX test failed: {exc}")
        return 1
    finally:
        controller.close()


if __name__ == "__main__":
    raise SystemExit(main())
