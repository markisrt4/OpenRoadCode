"""Command-line component test for BMP388 and BMP390 sensors."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from hardware_io.environmental import (
    BarometricSensorIf,
    Bmp388,
    Bmp390,
)


def parse_i2c_address(value: str) -> int:
    """Parse and validate a decimal or hexadecimal I2C address."""
    try:
        address = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid I2C address: {value}"
        ) from exc

    if not 0 <= address <= 0x7F:
        raise argparse.ArgumentTypeError(
            "I2C address must be between 0x00 and 0x7F"
        )

    return address


def positive_interval(value: str) -> float:
    """Parse a positive sampling interval."""
    try:
        interval = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid sampling interval: {value}"
        ) from exc

    if interval <= 0.0:
        raise argparse.ArgumentTypeError(
            "sampling interval must be greater than zero"
        )

    return interval


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Read pressure and temperature from a BMP388 or BMP390."
    )
    parser.add_argument(
        "--sensor",
        choices=("bmp388", "bmp390"),
        default="bmp388",
        help="Sensor model to test. Default: bmp388",
    )
    parser.add_argument(
        "--address",
        type=parse_i2c_address,
        default=Bmp388.DEFAULT_ADDRESS,
        help=(
            "I2C address in decimal or hexadecimal. Default: 0x77; "
            "many boards use 0x76 when SDO is low."
        ),
    )
    parser.add_argument(
        "--interval",
        type=positive_interval,
        default=1.0,
        help="Delay between samples in seconds. Default: 1.0",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Read one sample and exit.",
    )
    return parser.parse_args(argv)


def create_sensor(model: str, address: int) -> BarometricSensorIf:
    """Create the requested barometric sensor implementation."""
    sensor_types = {
        "bmp388": Bmp388,
        "bmp390": Bmp390,
    }
    return sensor_types[model](address=address)


def print_sample(sensor: BarometricSensorIf) -> None:
    """Read and display one pressure and temperature sample."""
    pressure_pa = sensor.get_pressure_pa()
    temperature_c = sensor.get_temperature_c()

    print(
        f"Pressure: {pressure_pa:10.1f} Pa  "
        f"Temperature: {temperature_c:6.2f} °C"
    )


def run(
    sensor: BarometricSensorIf,
    model: str,
    address: int,
    interval_s: float,
    once: bool,
) -> None:
    """Run the live component test."""
    sensor.start()

    try:
        if not sensor.is_started:
            raise RuntimeError("sensor did not report a started state")

        print(f"{model.upper()} connected at {address:#04x}")
        if not once:
            print("Press Ctrl+C to stop")
        print()

        while True:
            print_sample(sensor)

            if once:
                return

            time.sleep(interval_s)
    finally:
        sensor.stop()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the barometric sensor component test."""
    args = parse_args(argv)
    sensor = create_sensor(args.sensor, args.address)

    try:
        run(
            sensor=sensor,
            model=args.sensor,
            address=args.address,
            interval_s=args.interval,
            once=args.once,
        )
    except KeyboardInterrupt:
        print("\nStopped")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
