#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


from __future__ import annotations

import argparse
import asyncio

from hardware_io.bluetooth import BleDeviceInfo, BleScanner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bluetooth Low Energy scanner component test"
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="BLE scan duration in seconds",
    )

    return parser.parse_args()


def print_device(device: BleDeviceInfo) -> None:
    print("=" * 60)
    print(device.address)
    print(f"Name: {device.name}")
    print(f"Local name: {device.local_name}")
    print(f"RSSI: {device.rssi}")
    print(f"Service UUIDs: {list(device.service_uuids)}")
    print(f"Manufacturer data: {device.manufacturer_data}")


async def run_scan(timeout_seconds: float) -> None:
    scanner = BleScanner(timeout_seconds=timeout_seconds)

    print(
        f"Scanning for Bluetooth Low Energy devices "
        f"for {timeout_seconds:.1f} seconds...\n"
    )

    devices = await scanner.scan()

    if not devices:
        print("No BLE devices found.")
        return

    for device in devices:
        print_device(device)

    print("=" * 60)
    print(f"Found {len(devices)} BLE device(s).")


def main() -> None:
    args = parse_args()

    if args.timeout <= 0:
        raise SystemExit("--timeout must be greater than zero")

    try:
        asyncio.run(run_scan(args.timeout))

    except KeyboardInterrupt:
        print("\nScan stopped.")

    except Exception as exc:
        print(f"BLE scan failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

