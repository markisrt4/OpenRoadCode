# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for the localhost OpenRoadCode Android sensor bridge."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from hardware_io.imu import Vector3


@dataclass(frozen=True, slots=True)
class AndroidImuSample:
    acceleration_mps2: Vector3
    linear_acceleration_mps2: Vector3
    angular_velocity_rad_s: Vector3
    magnetic_field_ut: Vector3
    pressure_hpa: float
    accelerometer_timestamp_ns: int
    linear_acceleration_timestamp_ns: int
    gyroscope_timestamp_ns: int
    magnetometer_timestamp_ns: int
    pressure_timestamp_ns: int
    linear_acceleration_available: bool
    magnetometer_available: bool
    pressure_available: bool


class AndroidSensorBridgeClient:
    """Read Android hardware samples exposed on the local bridge HTTP API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8766", timeout_seconds: float = 2.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def is_available(self) -> bool:
        try:
            health = self._get_json("/health")
        except RuntimeError:
            return False
        return health.get("status") == "ready"

    def read_imu(self) -> AndroidImuSample:
        """Read one diagnostic IMU snapshot."""
        return _imu_sample(self._get_json("/imu"))

    def stream_imu(self) -> Iterator[AndroidImuSample]:
        """Yield IMU samples from the bridge's persistent NDJSON stream."""
        try:
            with urlopen(
                self._base_url + "/stream/imu",
                timeout=self._timeout_seconds,
            ) as response:
                for raw_line in response:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            f"Android sensor bridge returned invalid stream JSON: {exc}"
                        ) from exc
                    if not isinstance(payload, dict):
                        raise RuntimeError(
                            "Android sensor bridge stream returned a non-object JSON value"
                        )
                    yield _imu_sample(payload)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Android sensor bridge stream failed: {exc}") from exc

    def _get_json(self, path: str) -> dict[str, object]:
        try:
            with urlopen(self._base_url + path, timeout=self._timeout_seconds) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Android sensor bridge request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Android sensor bridge returned a non-object JSON response")
        return payload


def _imu_sample(payload: dict[str, object]) -> AndroidImuSample:
    if payload.get("ready") is not True:
        raise RuntimeError("Android sensor bridge IMU is not ready")
    return AndroidImuSample(
        acceleration_mps2=_vector(payload, "acceleration_mps2"),
        linear_acceleration_mps2=_vector(payload, "linear_acceleration_mps2"),
        angular_velocity_rad_s=_vector(payload, "angular_velocity_rad_s"),
        magnetic_field_ut=_vector(payload, "magnetic_field_uT"),
        pressure_hpa=_number(payload, "pressure_hpa"),
        accelerometer_timestamp_ns=_integer(payload, "accelerometer_timestamp_ns"),
        linear_acceleration_timestamp_ns=_integer(payload, "linear_acceleration_timestamp_ns"),
        gyroscope_timestamp_ns=_integer(payload, "gyroscope_timestamp_ns"),
        magnetometer_timestamp_ns=_integer(payload, "magnetometer_timestamp_ns"),
        pressure_timestamp_ns=_integer(payload, "pressure_timestamp_ns"),
        linear_acceleration_available=payload.get("linear_acceleration_available") is True,
        magnetometer_available=payload.get("magnetometer_available") is True,
        pressure_available=payload.get("pressure_available") is True,
    )


def _vector(payload: dict[str, object], name: str) -> Vector3:
    value = payload.get(name)
    if not isinstance(value, dict):
        raise RuntimeError(f"Android sensor bridge response is missing {name}")
    try:
        return Vector3(float(value["x"]), float(value["y"]), float(value["z"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Android sensor bridge returned an invalid {name}") from exc


def _integer(payload: dict[str, object], name: str) -> int:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"Android sensor bridge response is missing {name}")
    return value


def _number(payload: dict[str, object], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"Android sensor bridge response is missing {name}")
    return float(value)
