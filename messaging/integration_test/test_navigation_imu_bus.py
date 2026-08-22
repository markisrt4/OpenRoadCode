# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integration coverage for navigation attitude and IMU bus telemetry."""

from __future__ import annotations

import socket
import threading
import time

import pytest

from controllers.navigation import SimulatedNavigationController
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    NavigationStatePublisher,
    decode_attitude_state,
    decode_imu_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from messaging.zeromq.broker import ZeroMqBroker


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_one_navigation_sample_delivers_attitude_and_imu():
    ingress = f"tcp://127.0.0.1:{_free_tcp_port()}"
    egress = f"tcp://127.0.0.1:{_free_tcp_port()}"
    while egress == ingress:
        egress = f"tcp://127.0.0.1:{_free_tcp_port()}"

    broker = ZeroMqBroker(ingress, egress)
    broker_thread = threading.Thread(target=broker.run, daemon=True)
    broker_thread.start()

    broker_deadline = time.monotonic() + 1.0
    while not broker.is_running and time.monotonic() < broker_deadline:
        time.sleep(0.01)
    assert broker.is_running, "ZeroMQ broker did not start"

    attitude_messages = []
    imu_messages = []
    attitude_delivered = threading.Event()
    imu_delivered = threading.Event()
    dispatcher = MessageDispatcher(ZeroMqSubscriber(egress))
    dispatcher.register(
        ATTITUDE_STATE_TOPIC,
        decode_attitude_state,
        lambda message: (attitude_messages.append(message), attitude_delivered.set()),
    )
    dispatcher.register(
        IMU_STATE_TOPIC,
        decode_imu_state,
        lambda message: (imu_messages.append(message), imu_delivered.set()),
    )
    dispatcher.start()

    controller = SimulatedNavigationController()
    publisher = ZeroMqPublisher(ingress)
    navigation_publisher = NavigationStatePublisher(
        publisher,
        source="integration-test-navigation",
    )

    try:
        # PUB/SUB subscription propagation is asynchronous. Each iteration reads
        # exactly one controller snapshot and fans that same snapshot to both topics.
        deadline = time.monotonic() + 3.0
        while (
            not attitude_delivered.is_set() or not imu_delivered.is_set()
        ) and time.monotonic() < deadline:
            navigation_publisher.publish(controller.read_state())
            time.sleep(0.05)

        assert attitude_delivered.is_set(), "attitude state was not delivered"
        assert imu_delivered.is_set(), "IMU state was not delivered"

        attitude = attitude_messages[-1]
        imu = imu_messages[-1]
        assert attitude.source == "integration-test-navigation"
        assert imu.source == attitude.source
        assert imu.timestamp == attitude.timestamp
        assert 0.0 <= attitude.data.heading_rad < 2.0 * 3.141592653589793
        assert imu.data.acceleration_m_s2.z == pytest.approx(
            9.80665 + imu.data.linear_acceleration_m_s2.z
        )
        assert imu.data.angular_velocity_rad_s.z == pytest.approx(0.04)
    finally:
        publisher.close()
        dispatcher.close()
        broker.close()
        broker_thread.join(timeout=1.0)
        assert not broker_thread.is_alive(), "ZeroMQ broker did not stop"
