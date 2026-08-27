# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""End-to-end coverage for the configured navigation solution over ZeroMQ."""

from __future__ import annotations

import socket
import threading
import time

from config.service_runtime_config import (
    GpsInputConfig,
    GpsSimulationConfig,
    ImuInputConfig,
    NavigationServiceRuntimeConfig,
    SimulationProfileConfig,
)
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    NavigationStatePublisher,
    decode_attitude_state,
    decode_imu_state,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from messaging.zeromq.broker import ZeroMqBroker
from services.navigation.navigation_service_cli import build_controller


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _simulated_config() -> NavigationServiceRuntimeConfig:
    return NavigationServiceRuntimeConfig(
        imu=ImuInputConfig(
            source="simulation",
            device="mpu6050",
            simulation=SimulationProfileConfig(profile="driving"),
        ),
        gps=GpsInputConfig(
            source="simulation",
            device="gpsd",
            simulation=GpsSimulationConfig(
                profile="driving",
                latitude_deg=42.8028,
                longitude_deg=-83.0127,
                speed_mps=13.4,
                course_deg=180.0,
            ),
        ),
    )


def test_simulated_inputs_produce_complete_navigation_solution_over_bus():
    ingress = f"tcp://127.0.0.1:{_free_tcp_port()}"
    egress = f"tcp://127.0.0.1:{_free_tcp_port()}"
    while egress == ingress:
        egress = f"tcp://127.0.0.1:{_free_tcp_port()}"

    broker = ZeroMqBroker(ingress, egress)
    broker_thread = threading.Thread(target=broker.run, daemon=True)
    broker_thread.start()
    deadline = time.monotonic() + 1.0
    while not broker.is_running and time.monotonic() < deadline:
        time.sleep(0.01)
    assert broker.is_running

    received: dict[str, object] = {}
    delivered = {topic: threading.Event() for topic in (
        POSITION_STATE_TOPIC,
        MOTION_STATE_TOPIC,
        ATTITUDE_STATE_TOPIC,
        IMU_STATE_TOPIC,
    )}
    dispatcher = MessageDispatcher(ZeroMqSubscriber(egress))

    def register(topic, decoder):
        def handler(message):
            received[topic] = message
            delivered[topic].set()
        dispatcher.register(topic, decoder, handler)

    register(POSITION_STATE_TOPIC, decode_position_state)
    register(MOTION_STATE_TOPIC, decode_motion_state)
    register(ATTITUDE_STATE_TOPIC, decode_attitude_state)
    register(IMU_STATE_TOPIC, decode_imu_state)
    dispatcher.start()

    controller = build_controller(_simulated_config())
    controller.start()
    publisher = ZeroMqPublisher(ingress)
    navigation_publisher = NavigationStatePublisher(
        publisher,
        source="integration-test-solution",
    )

    try:
        deadline = time.monotonic() + 3.0
        while not all(event.is_set() for event in delivered.values()) and time.monotonic() < deadline:
            navigation_publisher.publish(controller.read_state())
            time.sleep(0.05)

        assert all(event.is_set() for event in delivered.values())

        position = received[POSITION_STATE_TOPIC]
        motion = received[MOTION_STATE_TOPIC]
        attitude = received[ATTITUDE_STATE_TOPIC]
        imu = received[IMU_STATE_TOPIC]

        # Position retains the source of the configured GPS input, while the
        # converged solution topics carry the navigation publisher's source.
        assert position.source == "simulation"
        assert motion.source == "integration-test-solution"
        assert attitude.source == motion.source == imu.source
        assert attitude.timestamp == motion.timestamp == imu.timestamp

        assert abs(position.data.latitude_rad) > 0.1
        assert abs(position.data.longitude_rad) > 0.1

        # Ground speed belongs to the motion contract. The driving profile
        # intentionally varies around its configured base speed by +/- 1.5 m/s.
        assert 11.9 <= motion.data.ground_speed_m_s <= 14.9

        assert imu.data.acceleration_m_s2.z > 9.0
        assert imu.data.angular_velocity_rad_s.z == 0.04
        assert -1.5707963267948966 <= attitude.data.pitch_rad <= 1.5707963267948966
        assert -3.141592653589793 <= attitude.data.roll_rad <= 3.141592653589793
    finally:
        controller.stop()
        publisher.close()
        dispatcher.close()
        broker.close()
        broker_thread.join(timeout=1.0)
        assert not broker_thread.is_alive()
