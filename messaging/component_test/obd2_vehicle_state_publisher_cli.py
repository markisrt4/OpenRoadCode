# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish vehicle state decoded from simulated raw OBD-II responses."""

from __future__ import annotations

import argparse
import math
import time

from controllers.automotive.obd2.obd2_manager import Obd2Manager
from messaging.contracts.automotive import VehicleStatePublisher
from messaging.zeromq import ZeroMqPublisher
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT
from protocols.obd2.simulated_obd2_adapter import SimulatedObd2Adapter

RPM_PER_RAD_S = 60.0 / (2.0 * math.pi)
MPH_PER_MPS = 2.2369362920544


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decode simulated SAE J1979 responses and publish vehicle.state"
    )
    parser.add_argument("--endpoint", default=LOCAL_PUBLISHER_ENDPOINT)
    parser.add_argument("--rate-hz", type=float, default=4.0)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.rate_hz <= 0.0:
        parser.error("--rate-hz must be greater than zero")

    adapter = SimulatedObd2Adapter()
    source = Obd2Manager(adapter)
    publisher = ZeroMqPublisher(args.endpoint)
    vehicle_publisher = VehicleStatePublisher(publisher, source="simulated-obd2")

    source.connect()
    period_s = 1.0 / args.rate_hz

    print("OpenRoadCode simulated OBD-II vehicle publisher")
    print(f"  broker ingress: {args.endpoint}")
    print(f"  publish rate:   {args.rate_hz:g} Hz")
    print("  source:         simulated-obd2")
    print("Ctrl+C to stop")

    sample_count = 0
    try:
        while True:
            state = source.read_state()
            vehicle_publisher.publish(state)
            sample_count += 1

            if not args.quiet and sample_count % max(1, round(args.rate_hz)) == 0:
                rpm = (
                    None
                    if state.engine_speed_rad_s is None
                    else state.engine_speed_rad_s * RPM_PER_RAD_S
                )
                mph = (
                    None
                    if state.vehicle_speed_m_s is None
                    else state.vehicle_speed_m_s * MPH_PER_MPS
                )
                rpm_text = "--" if rpm is None else f"{rpm:.0f}"
                speed_text = "--" if mph is None else f"{mph:.1f}"
                throttle_text = (
                    "--"
                    if state.throttle_position is None
                    else f"{state.throttle_position * 100.0:.1f}%"
                )
                print(
                    f"published #{sample_count}: "
                    f"rpm={rpm_text} speed={speed_text} mph "
                    f"throttle={throttle_text}"
                )

            time.sleep(period_s)
    except KeyboardInterrupt:
        pass
    finally:
        source.disconnect()
        publisher.close()


if __name__ == "__main__":
    main()
