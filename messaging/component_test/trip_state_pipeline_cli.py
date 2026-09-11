# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""End-to-end component test for trip derivation over an isolated ZeroMQ bus."""

from __future__ import annotations

import argparse
import threading
import time

from controllers.automotive import SimulatedVehicleStateSource
from messaging.contracts.automotive import (
    TRIP_STATE_TOPIC,
    VehicleStatePublisher,
    decode_trip_state,
)
from messaging.zeromq import ZeroMqBroker, ZeroMqPublisher, ZeroMqSubscriber
from services.trip import TripRuntime

TEST_BROKER_PUBLISHER_ENDPOINT = "tcp://127.0.0.1:15556"
TEST_BROKER_SUBSCRIBER_ENDPOINT = "tcp://127.0.0.1:15557"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exercise vehicle -> trip -> bus end to end on an isolated test broker"
    )
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument(
        "--publisher-endpoint",
        default=TEST_BROKER_PUBLISHER_ENDPOINT,
        help="isolated broker ingress endpoint",
    )
    parser.add_argument(
        "--subscriber-endpoint",
        default=TEST_BROKER_SUBSCRIBER_ENDPOINT,
        help="isolated broker egress endpoint",
    )
    args = parser.parse_args()
    if args.seconds <= 0.0:
        parser.error("--seconds must be greater than zero")

    broker = ZeroMqBroker(
        publisher_endpoint=args.publisher_endpoint,
        subscriber_endpoint=args.subscriber_endpoint,
    )
    broker_thread = threading.Thread(target=broker.run, daemon=True)
    broker_thread.start()
    deadline = time.monotonic() + 2.0
    while not broker.is_running and time.monotonic() < deadline:
        time.sleep(0.01)
    if not broker.is_running:
        raise RuntimeError(
            "isolated ZeroMQ test broker did not start "
            f"on {args.publisher_endpoint} / {args.subscriber_endpoint}"
        )

    source = SimulatedVehicleStateSource()
    source.connect()
    vehicle_wire = ZeroMqPublisher(args.publisher_endpoint)
    trip_wire = ZeroMqPublisher(args.publisher_endpoint)
    vehicle_publisher = VehicleStatePublisher(vehicle_wire, source="trip-component-test")
    trip_runtime = TripRuntime(
        ZeroMqSubscriber(args.subscriber_endpoint),
        trip_wire,
        publish_source="trip-component-test",
    )
    observer = ZeroMqSubscriber(args.subscriber_endpoint)
    observer.subscribe(TRIP_STATE_TOPIC)

    trip_runtime.start()
    time.sleep(0.2)

    started = time.monotonic()
    samples = 0
    last = None
    try:
        while time.monotonic() - started < args.seconds:
            vehicle_publisher.publish(source.read_state())
            samples += 1
            time.sleep(0.1)

        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            topic, payload = observer.receive()
            if topic == TRIP_STATE_TOPIC:
                last = decode_trip_state(payload)
                if last.data.elapsed_s > 0.0:
                    break

        if last is None:
            raise RuntimeError("no trip.state message observed")

        print("OpenRoadCode trip component test PASS")
        print(f"  broker ingress:  {args.publisher_endpoint}")
        print(f"  broker egress:   {args.subscriber_endpoint}")
        print(f"  vehicle samples: {samples}")
        print(f"  status:          {last.data.status}")
        print(f"  elapsed:         {last.data.elapsed_s:.2f} s")
        print(f"  distance:        {last.data.distance_m:.1f} m")
        print(
            "  average speed:   "
            + (
                "--"
                if last.data.average_speed_m_s is None
                else f"{last.data.average_speed_m_s:.2f} m/s"
            )
        )
        print(
            "  maximum speed:   "
            + (
                "--"
                if last.data.maximum_speed_m_s is None
                else f"{last.data.maximum_speed_m_s:.2f} m/s"
            )
        )
    finally:
        observer.close()
        trip_runtime.close()
        trip_wire.close()
        vehicle_wire.close()
        source.disconnect()
        broker.close()
        broker_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
