# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish vehicle state decoded from simulated raw OBD-II responses."""

from __future__ import annotations

import argparse
import time

from controllers.automotive.obd2.obd2_manager import Obd2Manager
from messaging.contracts.automotive import VehicleStatePublisher
from messaging.zeromq import ZeroMqPublisher
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT
from protocols.obd2.simulated_obd2_adapter import SimulatedObd2Adapter


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decode simulated SAE J1979 responses and publish vehicle.state"
    )
    parser.add_argument("--endpoint", default=LOCAL_PUBLISHER_ENDPOINT)
    parser.add_argument("--rate-hz", type=float, default=4.0)
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

    try:
        while True:
            state = source.read_state()
            vehicle_publisher.publish(state)
            time.sleep(period_s)
    except KeyboardInterrupt:
        pass
    finally:
        source.disconnect()
        publisher.close()


if __name__ == "__main__":
    main()
