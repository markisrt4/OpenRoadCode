# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Continuously publish complete simulated navigation telemetry."""

from __future__ import annotations

import argparse
import time

from controllers.navigation import SimulatedNavigationController
from messaging.contracts.navigation import NavigationStatePublisher
from messaging.zeromq import ZeroMqPublisher
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish simulated position, motion, attitude, and IMU state"
    )
    parser.add_argument("--endpoint", default=LOCAL_PUBLISHER_ENDPOINT)
    parser.add_argument("--rate-hz", type=float, default=10.0)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.rate_hz <= 0.0:
        parser.error("--rate-hz must be greater than zero")

    controller = SimulatedNavigationController()
    publisher = ZeroMqPublisher(args.endpoint)
    navigation_publisher = NavigationStatePublisher(
        publisher,
        source="simulated-navigation",
    )
    period_s = 1.0 / args.rate_hz

    controller.start()

    print("OpenRoadCode simulated navigation publisher")
    print(f"  broker ingress: {args.endpoint}")
    print(f"  publish rate:   {args.rate_hz:g} Hz")
    print("  topics:         position + motion + attitude + imu")
    print("  source:         simulated-navigation")
    print("Ctrl+C to stop")

    sample_count = 0
    try:
        while True:
            state = controller.read_state()
            navigation_publisher.publish(state)
            sample_count += 1

            if not args.quiet and sample_count % max(1, round(args.rate_hz)) == 0:
                linear = state.linear_acceleration_mps2
                gps = state.gps
                position = "no-fix" if gps is None else (
                    f"{gps.latitude_deg:.5f},{gps.longitude_deg:.5f}"
                )
                print(
                    f"published #{sample_count}: "
                    f"position={position} "
                    f"heading={state.heading_deg:6.1f}° "
                    f"pitch={state.pitch_deg:6.1f}° "
                    f"roll={state.roll_deg:6.1f}° "
                    f"linear=({linear.x:+.2f}, {linear.y:+.2f}, {linear.z:+.2f}) m/s²"
                )

            time.sleep(period_s)
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
        publisher.close()


if __name__ == "__main__":
    main()
