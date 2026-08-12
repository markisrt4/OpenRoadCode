#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


import argparse
import time

from hardware_io.keyboard import KeyboardReader


def key_pressed(key: str) -> None:
    print(f"Key pressed: {key}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="KeyboardReader CLI test application"
    )
    parser.add_argument(
        "--device",
        help="Linux input device path, e.g. /dev/input/event3",
    )

    args = parser.parse_args()

    reader = KeyboardReader(
        device_path=args.device,
        callback=key_pressed,
    )

    try:
        reader.start()

        print(f"Reading keyboard: {reader.device_name}")
        print(f"Device: {reader.device_path}")
        print("Press Ctrl+C to exit.\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping keyboard reader...")

    finally:
        reader.stop()


if __name__ == "__main__":
    main()
