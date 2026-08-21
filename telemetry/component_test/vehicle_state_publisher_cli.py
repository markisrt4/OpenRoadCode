# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish simulated VehicleState snapshots for telemetry smoke testing."""

import argparse
import time

from controllers.automotive.simulated_vehicle_state_source import (
    SimulatedVehicleStateSource,
)
from telemetry.vehicle_state_publisher import VehicleStatePublisher
from telemetry.zeromq_publisher import ZeroMqTelemetryPublisher


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5556")
    parser.add_argument("--interval", type=float, default=0.25)
    args = parser.parse_args()

    source = SimulatedVehicleStateSource()
    transport = ZeroMqTelemetryPublisher(args.endpoint)
    publisher = VehicleStatePublisher(transport)
    source.connect()

    try:
        while True:
            publisher.publish(source.read_state())
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        source.disconnect()
        transport.close()


if __name__ == "__main__":
    main()
