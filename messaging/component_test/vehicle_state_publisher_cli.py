# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish simulated vehicle state over the public ZeroMQ contract."""

import time

from controllers.automotive import SimulatedVehicleStateSource
from messaging.contracts.automotive import VehicleStatePublisher
from messaging.zeromq import ZeroMqPublisher


def main() -> None:
    source = SimulatedVehicleStateSource()
    publisher = ZeroMqPublisher()
    vehicle_publisher = VehicleStatePublisher(publisher, source="simulator")

    source.connect()
    try:
        while True:
            vehicle_publisher.publish(source.read_state())
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        source.disconnect()
        publisher.close()


if __name__ == "__main__":
    main()
