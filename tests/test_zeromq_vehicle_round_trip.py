# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""End-to-end ZeroMQ round-trip test for the public vehicle-state contract."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import socket
import threading
import time

import pytest

pytest.importorskip("zmq")

from controllers.automotive.vehicle_state import VehicleState
from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    VehicleStatePublisher,
    decode_vehicle_state,
)
from messaging.zeromq import ZeroMqBroker, ZeroMqPublisher, ZeroMqSubscriber


def _free_tcp_endpoint() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"tcp://127.0.0.1:{port}"


def test_vehicle_state_round_trip_over_zeromq() -> None:
    publisher_endpoint = _free_tcp_endpoint()
    subscriber_endpoint = _free_tcp_endpoint()
    broker = ZeroMqBroker(publisher_endpoint, subscriber_endpoint)
    broker_thread = threading.Thread(target=broker.run, daemon=True)
    broker_thread.start()

    deadline = time.monotonic() + 2.0
    while not broker.is_running and time.monotonic() < deadline:
        time.sleep(0.01)
    assert broker.is_running

    publisher = ZeroMqPublisher(publisher_endpoint)
    subscriber = ZeroMqSubscriber(subscriber_endpoint)
    subscriber.subscribe(VEHICLE_STATE_TOPIC)

    state = VehicleState(
        timestamp=datetime(2026, 8, 21, 12, 34, 56, 123456, tzinfo=timezone.utc),
        engine_speed_rad_s=314.1592653589793,
        vehicle_speed_m_s=26.8224,
        throttle_position=0.25,
        boost_pressure_pa=34_473.78646584,
        coolant_temperature_k=363.15,
    )
    vehicle_publisher = VehicleStatePublisher(publisher, source="simulator")

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            receive_future = executor.submit(subscriber.receive)
            time.sleep(0.2)
            vehicle_publisher.publish(state)
            topic, payload = receive_future.result(timeout=2.0)

        message = decode_vehicle_state(payload)

        assert topic == VEHICLE_STATE_TOPIC
        assert message.version == 1
        assert message.source == "simulator"
        assert message.timestamp.seconds > 0
        assert message.timestamp.nanoseconds == 123_456_000
        assert message.data.engine_speed_rad_s == pytest.approx(314.1592653589793)
        assert message.data.vehicle_speed_m_s == pytest.approx(26.8224)
        assert message.data.throttle_position == pytest.approx(0.25)
        assert message.data.boost_pressure_pa == pytest.approx(34_473.78646584)
        assert message.data.coolant_temperature_k == pytest.approx(363.15)
        assert message.data.fuel_level is None
    finally:
        subscriber.close()
        publisher.close()
        broker.close()
        broker_thread.join(timeout=2.0)
        assert not broker_thread.is_alive()
