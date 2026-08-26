# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Print Android-origin IMU samples received from the navigation ZeroMQ topic."""

from __future__ import annotations

from messaging.contracts.navigation.imu_state_codec import decode_imu_state
from messaging.contracts.navigation.topics import IMU_STATE_TOPIC
from messaging.zeromq.subscriber import ZeroMqSubscriber

from .android_sensor_service import ANDROID_IMU_SOURCE


def main() -> int:
    subscriber = ZeroMqSubscriber()
    subscriber.subscribe(IMU_STATE_TOPIC)

    print(f"[*] Subscribed to {IMU_STATE_TOPIC}")
    print("[*] Waiting for Android IMU messages. Press Ctrl+C to stop.")

    try:
        while True:
            topic, payload = subscriber.receive()
            message = decode_imu_state(payload)
            if message.source != ANDROID_IMU_SOURCE:
                continue
            acceleration = message.data.acceleration_m_s2
            angular_velocity = message.data.angular_velocity_rad_s
            print(
                f"{topic} source={message.source} "
                f"accel=({acceleration.x}, {acceleration.y}, {acceleration.z}) "
                f"gyro=({angular_velocity.x}, {angular_velocity.y}, {angular_velocity.z}) "
                f"timestamp={message.timestamp.seconds}.{message.timestamp.nanoseconds:09d}",
                flush=True,
            )
    except KeyboardInterrupt:
        print("\n[*] Stopping Android IMU subscriber...")
    finally:
        subscriber.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
