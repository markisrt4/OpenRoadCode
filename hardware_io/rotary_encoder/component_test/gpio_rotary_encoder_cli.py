#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


from __future__ import annotations

import argparse
import time

from hardware_io.rotary_encoder import (
    GpioRotaryEncoder,
    GpioRotaryEncoderPins,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GPIO rotary encoder component test"
    )

    parser.add_argument(
        "--pin-a",
        type=int,
        required=True,
        help="Physical Raspberry Pi header pin for encoder channel A",
    )

    parser.add_argument(
        "--pin-b",
        type=int,
        required=True,
        help="Physical Raspberry Pi header pin for encoder channel B",
    )

    parser.add_argument(
        "--button",
        type=int,
        help="Physical Raspberry Pi header pin for the encoder button",
    )

    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse the reported rotation direction",
    )

    parser.add_argument(
        "--bounce-ms",
        type=int,
        default=200,
        help="Button debounce time in milliseconds",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    encoder = GpioRotaryEncoder(
        pins=GpioRotaryEncoderPins(
            pin_a=args.pin_a,
            pin_b=args.pin_b,
            button=args.button,
        ),
        button_bounce_ms=args.bounce_ms,
        reverse_direction=args.reverse,
    )

    def rotated(steps: int) -> None:
        direction = "clockwise" if steps > 0 else "counterclockwise"
        print(f"Rotated {direction}: {steps:+d}")

    def button_pressed() -> None:
        print("Button pressed")

    def button_released() -> None:
        print("Button released")

    print("GPIO rotary encoder component test")
    print(f"Channel A physical pin: {args.pin_a}")
    print(f"Channel B physical pin: {args.pin_b}")
    print(f"Button physical pin: {args.button or 'not configured'}")
    print("Press Ctrl+C to stop.\n")

    encoder.start(
        rotated=rotated,
        button_pressed=button_pressed,
        button_released=button_released,
    )

    try:
        while True:
            encoder.tick()
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping GPIO rotary encoder test...")

    finally:
        encoder.cleanup()


if __name__ == "__main__":
    main()
