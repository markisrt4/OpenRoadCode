"""Command-line component test for an inertial measurement unit."""

from __future__ import annotations

import argparse
import sys
import time

from hardware_io.imu.imu_if import ImuIf
from hardware_io.imu.mpu6050_imu import Mpu6050Imu


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Read acceleration and angular velocity from an MPU-6050."
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
        default=0.2,
        help="Delay between samples in seconds. Default: 0.2",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Read one sample and exit.",
    )

    return parser.parse_args()


def print_sample(imu: ImuIf) -> None:
    """Read and display one IMU sample."""

    acceleration = imu.get_acceleration_mps2()
    angular_velocity = imu.get_angular_velocity_rad_s()

    print(
        "Acceleration:     "
        f"x={acceleration.x:8.3f}  "
        f"y={acceleration.y:8.3f}  "
        f"z={acceleration.z:8.3f}  "
        "m/s²"
    )

    print(
        "Angular velocity: "
        f"x={angular_velocity.x:8.4f}  "
        f"y={angular_velocity.y:8.4f}  "
        f"z={angular_velocity.z:8.4f}  "
        "rad/s"
    )


def run(imu: ImuIf, interval_s: float, once: bool) -> None:
    """Run the component test."""

    if interval_s <= 0.0:
        raise ValueError("interval must be greater than zero")

    imu.start()

    try:
        if not imu.is_connected():
            raise RuntimeError("IMU did not report a connected state")

        print("MPU-6050 connected")
        print("Press Ctrl+C to stop")
        print()

        while True:
            print_sample(imu)

            if once:
                return

            print()
            time.sleep(interval_s)

    finally:
        imu.stop()


def main() -> int:
    """Run the MPU-6050 command-line component test."""

    args = parse_args()

    imu = Mpu6050Imu(address=args.address)

    try:
        run(
            imu=imu,
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
