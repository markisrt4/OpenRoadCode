# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integration coverage for publisher -> ZeroMQ -> dispatcher vehicle state."""

from __future__ import annotations

import socket
import threading
import time

import pytest

from controllers.automotive.obd2.obd2_manager import Obd2Manager
from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    VehicleStatePublisher,
    decode_vehicle_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from messaging.zeromq.broker import ZeroMqBroker
from protocols.obd2.simulated_obd2_adapter import SimulatedObd2Adapter


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_simulated_obd_vehicle_state_crosses_message_bus():
    ingress = f"tcp://127.0.0.1:{_free_tcp_port()}"
    egress = f"tcp://127.0.0.1:{_free_tcp_port()}"
    while egress == ingress:
        egress = f"tcp://127.0.0.1:{_free_tcp_port()}"

    broker = ZeroMqBroker(ingress, egress)
    broker_thread = threading.Thread(target=broker.run, daemon=True)
    broker_thread.start()

    received = []
    delivered = threading.Event()
    dispatcher = MessageDispatcher(ZeroMqSubscriber(egress))
    dispatcher.register(
        VEHICLE_STATE_TOPIC,
        decode_vehicle_state,
        lambda message: (received.append(message), delivered.set()),
    )
    dispatcher.start()

    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()
    publisher = ZeroMqPublisher(ingress)
    vehicle_publisher = VehicleStatePublisher(publisher, source="integration-test-obd2")

    try:
        # PUB/SUB subscription propagation is asynchronous. Publish several
        # samples rather than encoding a timing assumption into the test.
        deadline = time.monotonic() + 3.0
        while not delivered.is_set() and time.monotonic() < deadline:
            adapter.advance()
            vehicle_publisher.publish(manager.read_state())
            delivered.wait(0.05)

        assert delivered.is_set(), "vehicle state was not delivered through broker"
        message = received[-1]
        assert message.source == "integration-test-obd2"
        assert message.data.engine_speed_rad_s is not None
        assert message.data.vehicle_speed_m_s is not None
        assert message.data.throttle_position is not None
        assert message.data.boost_pressure_pa == pytest.approx(
            message.data.intake_manifold_pressure_pa
            - message.data.barometric_pressure_pa
        )
    finally:
        manager.disconnect()
        publisher.close()
        dispatcher.close()
        broker.close()
        broker_thread.join(timeout=1.0)
