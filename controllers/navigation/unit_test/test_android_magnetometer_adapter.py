# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from hardware_io.android.magnetometer import MagnetometerSample as AndroidMagnetometerSample
from hardware_io.imu import Vector3

from controllers.navigation.android_magnetometer_adapter import AndroidMagnetometerAdapter


class _MagnetometerStub:
    def __init__(self) -> None:
        self.connected = False

    @property
    def is_connected(self) -> bool:
        return self.connected

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def read_magnetometer(self) -> AndroidMagnetometerSample:
        return AndroidMagnetometerSample(
            magnetic_field_ut=Vector3(x=1.0, y=2.0, z=3.0),
            timestamp_ns=123,
        )


def test_lifecycle_is_delegated() -> None:
    magnetometer = _MagnetometerStub()
    adapter = AndroidMagnetometerAdapter(magnetometer)  # type: ignore[arg-type]

    assert not adapter.is_connected
    adapter.connect()
    assert adapter.is_connected
    adapter.disconnect()
    assert not adapter.is_connected


def test_device_frame_is_transformed_to_vehicle_frame() -> None:
    adapter = AndroidMagnetometerAdapter(_MagnetometerStub())  # type: ignore[arg-type]

    sample = adapter.read_magnetometer()

    assert sample.magnetic_field_ut == Vector3(x=2.0, y=-1.0, z=3.0)
    assert sample.timestamp_ns == 123
