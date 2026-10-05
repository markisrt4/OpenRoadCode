# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic radar provider used by the Android environmental injector."""

from __future__ import annotations

from time import time

from controllers.weather.radar_provider_if import RadarFrame, RadarProviderIf


class InjectedRadarProvider(RadarProviderIf):
    """Expose deterministic synthetic radar history for a named test scenario."""

    def __init__(self, scenario: str, *, frame_count: int = 6) -> None:
        self._scenario = scenario.lower()
        self._frame_count = frame_count
        self._epoch = int(time() // 300 * 300)

    @property
    def provider_id(self) -> str:
        return "injected"

    def get_frames(self) -> tuple[RadarFrame, ...]:
        if self._scenario not in {"clear", "storm", "severe"}:
            raise ValueError(f"unsupported injected radar scenario: {self._scenario}")
        first = self._epoch - (self._frame_count - 1) * 300
        return tuple(
            RadarFrame(
                timestamp=first + index * 300,
                tile_url=(
                    f"orc-injected://{self._scenario}/{index}"
                    "/{z}/{x}/{y}.png"
                ),
                max_zoom=7,
            )
            for index in range(self._frame_count)
        )
