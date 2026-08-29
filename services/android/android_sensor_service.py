# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish Android bridge hardware samples onto the OpenRoadCode message bus."""

from __future__ import annotations

from datetime import datetime, timezone

from controllers.environmental import (
    AmbientLightController,
    BarometricController,
    BarometricSample,
    BufferedAmbientLightSensor,
    BufferedBarometricSource,
)
from hardware_io.android import AndroidSensorBridgeClient
from messaging.contracts.common.timestamp import encode_timestamp
from messaging.contracts.environmental import (
    AMBIENT_LIGHT_STATE_TOPIC,
    BAROMETRIC_STATE_TOPIC,
    encode_ambient_light_state,
    encode_barometric_state,
)
from messaging.contracts.navigation.frames import ANDROID_DEVICE_FRAME
from messaging.contracts.navigation.imu_state_codec import encode_imu_state
from messaging.contracts.navigation.magnetic_field_state_codec import encode_magnetic_field_state
from messaging.contracts.navigation.topics import IMU_STATE_TOPIC, MAGNETIC_FIELD_STATE_TOPIC
from messaging.publisher_if import PublisherIf

ANDROID_SENSOR_SOURCE = "android"
_ZERO_VECTOR = {"x": 0.0, "y": 0.0, "z": 0.0}


class AndroidSensorService:
    """Fan one Android HTTP sensor stream out onto ORC telemetry contracts."""

    def __init__(self, client: AndroidSensorBridgeClient, publisher: PublisherIf, *, poll_hz: float | None = None) -> None:
        if poll_hz is not None and poll_hz <= 0.0:
            raise ValueError("poll_hz must be greater than zero")
        self._client = client
        self._publisher = publisher
        self._barometric_source = BufferedBarometricSource()
        self._barometric = BarometricController(self._barometric_source)
        self._ambient_light_sensor = BufferedAmbientLightSensor()
        self._ambient_light = AmbientLightController(self._ambient_light_sensor)

    def run(self) -> None:
        """Forward Android motion and environmental sensor samples."""
        barometric_started = False
        ambient_light_started = False
        try:
            for sample in self._client.stream_imu():
                timestamp = encode_timestamp(datetime.now(timezone.utc))
                linear = _vector_dict(sample.linear_acceleration_mps2) if sample.linear_acceleration_available else _ZERO_VECTOR

                self._publisher.publish(IMU_STATE_TOPIC, encode_imu_state(
                    timestamp=timestamp,
                    source=ANDROID_SENSOR_SOURCE,
                    frame_id=ANDROID_DEVICE_FRAME,
                    acceleration_m_s2=_vector_dict(sample.acceleration_mps2),
                    linear_acceleration_m_s2=linear,
                    angular_velocity_rad_s=_vector_dict(sample.angular_velocity_rad_s),
                ))

                if sample.magnetometer_available:
                    self._publisher.publish(MAGNETIC_FIELD_STATE_TOPIC, encode_magnetic_field_state(
                        timestamp=timestamp,
                        source=ANDROID_SENSOR_SOURCE,
                        magnetic_field_ut=_vector_dict(sample.magnetic_field_ut),
                    ))

                if sample.pressure_available:
                    self._barometric_source.update_sample(BarometricSample(
                        pressure_pa=float(sample.pressure_hpa) * 100.0,
                        temperature_c=None,
                    ))
                    if not barometric_started:
                        self._barometric.start()
                        barometric_started = True
                    state = self._barometric.read_state()
                    self._publisher.publish(BAROMETRIC_STATE_TOPIC, encode_barometric_state(
                        timestamp=encode_timestamp(state.timestamp),
                        source=ANDROID_SENSOR_SOURCE,
                        pressure_pa=state.pressure_pa,
                        temperature_c=state.temperature_c,
                        altitude_m=state.altitude_m,
                        relative_altitude_m=state.relative_altitude_m,
                        vertical_speed_m_s=state.vertical_speed_mps,
                    ))

                if sample.ambient_light_available:
                    self._ambient_light_sensor.update_illuminance_lux(sample.ambient_light_lux)
                    if not ambient_light_started:
                        self._ambient_light.start()
                        ambient_light_started = True
                    state = self._ambient_light.read_state()
                    self._publisher.publish(AMBIENT_LIGHT_STATE_TOPIC, encode_ambient_light_state(
                        timestamp=encode_timestamp(state.timestamp),
                        source=ANDROID_SENSOR_SOURCE,
                        illuminance_lux=state.illuminance_lux,
                    ))
        finally:
            if ambient_light_started:
                self._ambient_light.stop()
            if barometric_started:
                self._barometric.stop()


def _vector_dict(vector: object) -> dict[str, float]:
    return {axis: float(getattr(vector, axis)) for axis in ("x", "y", "z")}
