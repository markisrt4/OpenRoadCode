# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Print Android IMU samples received from the OpenRoadCode ZeroMQ bus."""

from __future__ import annotations

from messaging.zeromq.subscriber import ZeroMqSubscriber

from .android_sensor_service import ANDROID_IMU_TOPIC


def main() -> int:
    subscriber = ZeroMqSubscriber()
    subscriber.subscribe(ANDROID_IMU_TOPIC)

    print(f"[*] Subscribed to {ANDROID_IMU_TOPIC}")
    print("[*] Waiting for Android IMU messages. Press Ctrl+C to stop.")

    try:
        while True:
            topic, payload = subscriber.receive()
            acceleration = payload.get("acceleration_mps2", {})
            angular_velocity = payload.get("angular_velocity_rad_s", {})
            print(
                f"{topic} "
                f"accel=({acceleration.get('x')}, {acceleration.get('y')}, {acceleration.get('z')}) "
                f"gyro=({angular_velocity.get('x')}, {angular_velocity.get('y')}, {angular_velocity.get('z')}) "
                f"accel_t={payload.get('accelerometer_timestamp_ns')} "
                f"gyro_t={payload.get('gyroscope_timestamp_ns')}",
                flush=True,
            )
    except KeyboardInterrupt:
        print("\n[*] Stopping Android IMU subscriber...")
    finally:
        subscriber.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
