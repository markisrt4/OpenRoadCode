# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""GPSD-backed weather location selection with a bounded wait for a fix."""
from __future__ import annotations

import json
import math
import socket
import time

from controllers.weather.weather_state import WeatherLocation


class GpsdWeatherLocationProvider:
    """Read a current weather fix without waiting indefinitely for GPSD."""

    def __init__(self, host: str = "127.0.0.1", port: int = 2947,
                 *, timeout_seconds: float = 2.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("GPS timeout must be positive")
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds

    def get_location(self) -> WeatherLocation:
        deadline = time.monotonic() + self._timeout_seconds
        with socket.create_connection((self._host, self._port),
                                      timeout=self._timeout_seconds) as connection:
            connection.sendall(b'?WATCH={"enable":true,"json":true};\n')
            with connection.makefile("rb") as stream:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("Weather GPS lookup timed out")
                    connection.settimeout(remaining)
                    line = stream.readline(65536)
                    if not line:
                        raise RuntimeError("GPSD closed before providing a fix")
                    if not line.endswith(b"\n"):
                        raise RuntimeError("GPSD message exceeds size limit")
                    try:
                        packet = json.loads(line)
                        if packet.get("class") != "TPV" or packet.get("mode", 0) < 2:
                            continue
                        lat, lon = float(packet["lat"]), float(packet["lon"])
                    except (ValueError, TypeError, KeyError, AttributeError):
                        continue
                    if not (math.isfinite(lat) and math.isfinite(lon)
                            and -90 <= lat <= 90 and -180 <= lon <= 180):
                        continue
                    return WeatherLocation(latitude=lat, longitude=lon,
                                           name=f"{lat:.5f}, {lon:.5f}", source="GPSD")
