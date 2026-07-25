#!/usr/bin/env python3

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

import board

from hardware_io.rotary_encoder import SeesawRotaryEncoder


@dataclass(frozen=True)
class EncoderConfig:
    name: str
    address: int


def parse_i2c_address(value: str) -> int:
    try:
        address = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid I2C address: {value}"
        ) from exc

    if not 0 <= address <= 0x7F:
        raise argparse.ArgumentTypeError(
            "I2C address must be between 0x00 and 0x7F"
        )

    return address


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-or-more encoder Seesaw component test"
    )

    parser.add_argument(
        "--addresses",
        nargs="+",
        type=parse_i2c_address,
        default=[0x36, 0x37, 0x38],
        metavar="ADDRESS",
        help=(
            "I2C addresses to test, for example: "
            "--addresses 0x36 0x37 (default: 0x36 0x37 0x38)"
        ),
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.01,
        help="Polling interval in seconds",
    )

    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse rotation direction for all encoders",
    )

    return parser.parse_args()


def create_callbacks(
    name: str,
    address: int,
):
    def rotated(steps: int) -> None:
        direction = "clockwise" if steps > 0 else "counterclockwise"

        print(
            f"[{name} {address:#04x}] "
            f"rotated {direction}: {steps:+d}"
        )

    def button_pressed() -> None:
        print(f"[{name} {address:#04x}] button pressed")

    def button_released() -> None:
        print(f"[{name} {address:#04x}] button released")

    return rotated, button_pressed, button_released


def main() -> None:
    args = parse_args()

    configs = tuple(
        EncoderConfig(f"encoder-{number}", address)
        for number, address in enumerate(args.addresses, start=1)
    )

    addresses = [config.address for config in configs]

    if len(addresses) != len(set(addresses)):
        raise ValueError(
            "Each Seesaw encoder must use a unique I2C address"
        )

    print("Initializing shared I2C bus...")
    i2c = board.I2C()

    encoders: list[SeesawRotaryEncoder] = []

    try:
        for config in configs:
            encoder = SeesawRotaryEncoder(
                address=config.address,
                i2c=i2c,
                poll_interval=args.poll_interval,
                reverse_direction=args.reverse,
            )

            rotated, button_pressed, button_released = create_callbacks(
                config.name,
                config.address,
            )

            encoder.start(
                rotated=rotated,
                button_pressed=button_pressed,
                button_released=button_released,
            )

            encoders.append(encoder)

        print("\nSeesaw rotary encoder component test")
        print("Configured encoders:")

        for config in configs:
            print(f"  {config.name}: {config.address:#04x}")

        print("\nRotate or press any encoder.")
        print("Press Ctrl+C to stop.\n")

        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nStopping Seesaw rotary encoder test...")

    finally:
        for encoder in encoders:
            encoder.stop()


if __name__ == "__main__":
    main()
