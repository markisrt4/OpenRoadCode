# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Low-level Termux:API sensor access."""

from __future__ import annotations

import json
import shutil
import subprocess

from hardware_io.imu import Vector3


class TermuxSensorClient:
    """Read Android sensors exposed by the ``termux-sensor`` command."""

    def __init__(self, *, timeout_seconds: float = 5.0) -> None:
        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than zero")
        self._timeout_seconds = timeout_seconds

    @property
    def is_available(self) -> bool:
        return shutil.which("termux-sensor") is not None

    def list_sensors(self) -> tuple[str, ...]:
        payload = self._run(["termux-sensor", "-l"])
        sensors = payload.get("sensors")
        if not isinstance(sensors, list):
            raise RuntimeError("Unexpected termux-sensor inventory payload")
        return tuple(str(sensor) for sensor in sensors)

    def read_vector(self, sensor_name: str) -> Vector3:
        return self.read_vectors((sensor_name,))[sensor_name]

    def read_vectors(self, sensor_names: tuple[str, ...]) -> dict[str, Vector3]:
        """Read one sample from each requested sensor in a single API call."""
        if not sensor_names:
            raise ValueError("sensor_names must not be empty")

        requested = ",".join(sensor_names)
        payload = self._run(["termux-sensor", "-s", requested, "-n", "1"])
        vectors: dict[str, Vector3] = {}

        for requested_name in sensor_names:
            matching_key = next(
                (key for key in payload if requested_name.lower() in key.lower()),
                None,
            )
            if matching_key is None:
                raise RuntimeError(
                    f"No Termux sensor result matched {requested_name!r}"
                )

            entry = payload[matching_key]
            if not isinstance(entry, dict):
                raise RuntimeError(
                    f"Unexpected Termux sensor payload for {requested_name!r}"
                )
            values = entry.get("values")
            if not isinstance(values, list) or len(values) < 3:
                raise RuntimeError(
                    f"Termux sensor {requested_name!r} did not return a 3-axis sample"
                )
            vectors[requested_name] = Vector3(
                float(values[0]),
                float(values[1]),
                float(values[2]),
            )

        return vectors

    def _run(self, command: list[str]) -> dict:
        if not self.is_available:
            raise RuntimeError(
                "termux-sensor is not available; install Termux:API and the termux-api package"
            )
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self._timeout_seconds,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected JSON payload from termux-sensor")
        return payload
