"""Command-line component test for the navigation controller."""

from __future__ import annotations

import argparse
import sys
import time

from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
    NavigationState,
)
from hardware_io.imu import Mpu6050Imu


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Monitor orientation and motion using an MPU-6050-backed "
            "navigation controller."
        )
    )
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        default=Mpu6050Imu.DEFAULT_ADDRESS,
        help=(
            "MPU-6050 I2C address. Accepts decimal or hexadecimal values. "
            "Default: 0x68"
        ),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Delay between samples in seconds. Default: 0.1",
    )
    parser.add_argument(
        "--filter-time-constant",
        type=float,
        default=0.5,
        help=(
            "Complementary-filter time constant in seconds. Default: 0.5"
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Read one navigation state and exit.",
    )
    parser.add_argument(
        "--gps",
        action="store_true",
        help="Include GPS state from gpsd.",
    )
    parser.add_argument(
        "--gps-host",
        default="127.0.0.1",
        help="gpsd host used with --gps. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--gps-port",
        default="2947",
        help="gpsd port used with --gps. Default: 2947",
    )
    return parser.parse_args()


def format_state(state: NavigationState) -> str:
    """Format one navigation state for terminal output."""

    acceleration = state.acceleration_mps2
    linear_acceleration = state.linear_acceleration_mps2
    angular_velocity = state.angular_velocity_rad_s

    lines = [
        (
            "Orientation:      "
            f"heading={state.heading_deg:8.2f}°  "
            f"pitch={state.pitch_deg:8.2f}°  "
            f"roll={state.roll_deg:8.2f}°"
        ),
        (
            "Acceleration:     "
            f"x={acceleration.x:8.3f}  "
            f"y={acceleration.y:8.3f}  "
            f"z={acceleration.z:8.3f}  m/s²"
        ),
        (
            "Linear accel:     "
            f"x={linear_acceleration.x:8.3f}  "
            f"y={linear_acceleration.y:8.3f}  "
            f"z={linear_acceleration.z:8.3f}  m/s²"
        ),
        (
            "Angular velocity: "
            f"x={angular_velocity.x:8.4f}  "
            f"y={angular_velocity.y:8.4f}  "
            f"z={angular_velocity.z:8.4f}  rad/s"
        ),
    ]

    if state.gps is not None:
        gps = state.gps
        fix = (
            f"{gps.fix_mode}D" if gps.has_fix else "no fix"
        )
        lines.append(
            "GPS:              "
            f"fix={fix}  "
            f"lat={gps.latitude_deg}  "
            f"lon={gps.longitude_deg}  "
            f"alt={gps.altitude_m} m  "
            f"speed={gps.speed_mps} m/s  "
            f"course={gps.course_deg}°"
        )

    return "\n".join(lines)


def run(
    controller: NavigationController,
    interval_s: float,
    once: bool,
) -> None:
    """Run the live navigation component test."""

    if interval_s <= 0.0:
        raise ValueError("interval must be greater than zero")

    controller.start()

    try:
        print("Navigation controller started")
        print("Heading is relative and may drift with the default estimator")
        print("Press Ctrl+C to stop")
        print()

        while True:
            print(format_state(controller.read_state()))

            if once:
                return

            print()
            time.sleep(interval_s)
    finally:
        controller.stop()


def main() -> int:
    """Run the navigation controller component test."""

    args = parse_args()
    gps_source = None
    if args.gps:
        from hardware_io.gps import GpsReader

        gps_source = GpsdNavigationAdapter(
            GpsReader(host=args.gps_host, port=args.gps_port)
        )

    controller = NavigationController(
        sensor=Mpu6050NavigationAdapter(
            Mpu6050Imu(address=args.address)
        ),
        filter_time_constant_s=args.filter_time_constant,
        gps_source=gps_source,
    )

    try:
        run(
            controller=controller,
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
