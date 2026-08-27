# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Diagnose navigation attitude and IMU delivery through MessageDispatcher."""

from __future__ import annotations

import argparse
import math
import time

from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=LOCAL_SUBSCRIBER_ENDPOINT)
    args = parser.parse_args()

    attitude_count = 0
    imu_count = 0

    def handle_attitude(message) -> None:
        nonlocal attitude_count
        attitude_count += 1
        data = message.data
        print(
            f"attitude #{attitude_count}: source={message.source} "
            f"heading={_degrees(data.heading_rad)} "
            f"pitch={_degrees(data.pitch_rad)} "
            f"roll={_degrees(data.roll_rad)}"
        )

    def handle_imu(message) -> None:
        nonlocal imu_count
        imu_count += 1
        data = message.data
        linear = data.linear_acceleration_m_s2
        angular = data.angular_velocity_rad_s
        print(
            f"imu #{imu_count}: source={message.source} "
            f"linear=({linear.x:+.2f}, {linear.y:+.2f}, {linear.z:+.2f}) m/s² "
            f"gyro=({angular.x:+.3f}, {angular.y:+.3f}, {angular.z:+.3f}) rad/s"
        )

    def handle_error(topic: str, error: Exception) -> None:
        print(f"ERROR [{topic}]: {type(error).__name__}: {error}")

    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(args.endpoint),
        error_handler=handle_error,
    )
    dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, handle_attitude)
    dispatcher.register(IMU_STATE_TOPIC, decode_imu_state, handle_imu)
    dispatcher.start()

    print("OpenRoadCode navigation dispatcher diagnostic")
    print(f"  endpoint: {args.endpoint}")
    print(f"  topics:   {ATTITUDE_STATE_TOPIC}, {IMU_STATE_TOPIC}")
    print("Ctrl+C to stop")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        dispatcher.close()


def _degrees(value: float | None) -> str:
    return "--" if value is None else f"{math.degrees(value):.1f}°"


if __name__ == "__main__":
    main()
