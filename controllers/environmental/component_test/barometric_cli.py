"""Command-line component test for the BMP3XX barometric controller."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from controllers.environmental import (
    BarometricController,
    BarometricControllerIf,
    BarometricState,
    Bmp3xxBarometricAdapter,
)
from hardware_io.environmental import Bmp3xx

PASCALS_PER_INCH_OF_MERCURY = 3386.389
METERS_PER_FOOT = 0.3048


def parse_i2c_address(value: str) -> int:
    """Parse a decimal or hexadecimal seven-bit I2C address."""
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


def positive_float(value: str) -> float:
    """Parse a positive floating-point argument."""
    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid positive number: {value}"
        ) from exc

    if result <= 0.0:
        raise argparse.ArgumentTypeError(
            "value must be greater than zero"
        )
    return result


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Read processed barometric state from a BMP388 or BMP390."
        )
    )
    parser.add_argument(
        "--address",
        type=parse_i2c_address,
        default=Bmp3xx.DEFAULT_ADDRESS,
        help="I2C address. Default: 0x77",
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=1.0,
        help="Delay between samples in seconds. Default: 1.0",
    )
    parser.add_argument(
        "--sea-level-pressure",
        type=positive_float,
        default=BarometricController.STANDARD_SEA_LEVEL_PRESSURE_PA,
        metavar="PA",
        help="Altitude reference pressure in Pa. Default: 101325",
    )
    parser.add_argument(
        "--imperial",
        action="store_true",
        help="Display inHg, °F, feet, and feet per minute.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Read one state and exit.",
    )
    return parser.parse_args(argv)


def format_state(
    state: BarometricState,
    *,
    imperial: bool = False,
) -> str:
    """Format one environmental state for terminal output."""
    if imperial:
        pressure_inhg = (
            state.pressure_pa / PASCALS_PER_INCH_OF_MERCURY
        )
        temperature_f = state.temperature_c * 9.0 / 5.0 + 32.0
        altitude_ft = state.altitude_m / METERS_PER_FOOT
        relative_altitude_ft = (
            state.relative_altitude_m / METERS_PER_FOOT
        )
        vertical_speed_ft_min = (
            state.vertical_speed_mps / METERS_PER_FOOT * 60.0
        )
        return (
            f"Pressure: {pressure_inhg:7.3f} inHg  "
            f"Temperature: {temperature_f:6.2f} °F  "
            f"Altitude: {altitude_ft:8.1f} ft  "
            f"Relative: {relative_altitude_ft:8.1f} ft  "
            f"Vertical speed: {vertical_speed_ft_min:8.1f} ft/min"
        )

    return (
        f"Pressure: {state.pressure_pa:10.1f} Pa  "
        f"Temperature: {state.temperature_c:6.2f} °C  "
        f"Altitude: {state.altitude_m:8.1f} m  "
        f"Relative: {state.relative_altitude_m:8.1f} m  "
        f"Vertical speed: {state.vertical_speed_mps:7.2f} m/s"
    )


def run(
    controller: BarometricControllerIf,
    *,
    interval_s: float,
    once: bool,
    imperial: bool,
) -> None:
    """Run the live controller component test."""
    if interval_s <= 0.0:
        raise ValueError("interval must be greater than zero")

    controller.start()
    try:
        print("Barometric controller started")
        if not once:
            print("Press Ctrl+C to stop")
        print()

        while True:
            print(format_state(controller.read_state(), imperial=imperial))
            if once:
                return
            time.sleep(interval_s)
    finally:
        controller.stop()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the BMP3XX-backed environmental controller test."""
    args = parse_args(argv)
    controller = BarometricController(
        Bmp3xxBarometricAdapter(
            Bmp3xx(address=args.address)
        ),
        sea_level_pressure_pa=args.sea_level_pressure,
    )

    try:
        run(
            controller,
            interval_s=args.interval,
            once=args.once,
            imperial=args.imperial,
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
