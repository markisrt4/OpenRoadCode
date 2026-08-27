# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Print Android-origin sensor samples received over ZeroMQ."""

from __future__ import annotations

from messaging.contracts.environmental import BAROMETRIC_STATE_TOPIC, decode_barometric_state
from messaging.contracts.navigation.imu_state_codec import decode_imu_state
from messaging.contracts.navigation.magnetic_field_state_codec import decode_magnetic_field_state
from messaging.contracts.navigation.topics import IMU_STATE_TOPIC, MAGNETIC_FIELD_STATE_TOPIC
from messaging.zeromq.subscriber import ZeroMqSubscriber

from .android_sensor_service import ANDROID_SENSOR_SOURCE


def main() -> int:
    subscriber = ZeroMqSubscriber()
    subscriber.subscribe(IMU_STATE_TOPIC)
    subscriber.subscribe(MAGNETIC_FIELD_STATE_TOPIC)
    subscriber.subscribe(BAROMETRIC_STATE_TOPIC)
    print("[*] Subscribed to Android IMU, magnetic-field, and barometric topics")
    print("[*] Waiting for Android sensor messages. Press Ctrl+C to stop.")
    try:
        while True:
            topic, payload = subscriber.receive()
            if topic == IMU_STATE_TOPIC:
                message = decode_imu_state(payload)
                if message.source != ANDROID_SENSOR_SOURCE:
                    continue
                a = message.data.acceleration_m_s2
                g = message.data.angular_velocity_rad_s
                print(
                    f"IMU accel=({a.x:.3f}, {a.y:.3f}, {a.z:.3f}) "
                    f"gyro=({g.x:.3f}, {g.y:.3f}, {g.z:.3f})",
                    flush=True,
                )
            elif topic == MAGNETIC_FIELD_STATE_TOPIC:
                message = decode_magnetic_field_state(payload)
                if message.source != ANDROID_SENSOR_SOURCE:
                    continue
                m = message.magnetic_field_ut
                print(
                    f"MAG field=({m.x:.2f}, {m.y:.2f}, {m.z:.2f}) uT",
                    flush=True,
                )
            elif topic == BAROMETRIC_STATE_TOPIC:
                message = decode_barometric_state(payload)
                if message.source != ANDROID_SENSOR_SOURCE:
                    continue
                data = message.data
                print(
                    f"BARO pressure={data.pressure_pa:.1f} Pa "
                    f"alt={data.altitude_m:.2f} m "
                    f"relative={data.relative_altitude_m:.2f} m "
                    f"vertical={data.vertical_speed_m_s:.2f} m/s",
                    flush=True,
                )
    except KeyboardInterrupt:
        print("\n[*] Stopping Android sensor subscriber...")
    finally:
        subscriber.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
