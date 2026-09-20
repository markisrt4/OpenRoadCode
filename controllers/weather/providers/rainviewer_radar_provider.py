# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""RainViewer implementation of the weather-radar provider contract."""

from __future__ import annotations

import requests

from controllers.weather.radar_provider_if import RadarFrame, RadarProviderIf


class RainViewerRadarProvider(RadarProviderIf):
    """Discover recent RainViewer radar frames for MapLibre XYZ rendering."""

    URL = "https://api.rainviewer.com/public/weather-maps.json"

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
        tile_size: int = 256,
    ) -> None:
        if tile_size not in (256, 512):
            raise ValueError("RainViewer tile size must be 256 or 512")
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()
        self._tile_size = tile_size

    @property
    def provider_id(self) -> str:
        return "rainviewer"

    def get_frames(self) -> tuple[RadarFrame, ...]:
        response = self._session.get(self.URL, timeout=self._timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("RainViewer returned invalid radar metadata")

        host = payload.get("host")
        radar = payload.get("radar")
        past = radar.get("past") if isinstance(radar, dict) else None
        if not isinstance(host, str) or not host or not isinstance(past, list):
            raise ValueError("RainViewer returned incomplete radar metadata")

        frames: list[RadarFrame] = []
        for item in past:
            if not isinstance(item, dict):
                continue
            timestamp = item.get("time")
            path = item.get("path")
            if not isinstance(timestamp, int) or not isinstance(path, str) or not path:
                continue
            frames.append(
                RadarFrame(
                    timestamp=timestamp,
                    tile_url=(
                        f"{host.rstrip('/')}/{path.lstrip('/')}/{self._tile_size}"
                        "/{z}/{x}/{y}/2/1_1.png"
                    ),
                )
            )

        frames.sort(key=lambda frame: frame.timestamp)
        if not frames:
            raise ValueError("RainViewer returned no usable radar frames")
        return tuple(frames)
