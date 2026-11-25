# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Translate radar imagery status and frame age into display status."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Protocol

from controllers.weather.radar_tile_status import RadarTileStatus


class RadarReplayHealthSource(Protocol):
    """Read-only radar frame metadata required by the health presentation."""

    @property
    def frame_tile_status(self) -> RadarTileStatus | None: ...

    @property
    def frame_times(self) -> Iterable[float]: ...

    @property
    def is_forecast(self) -> bool: ...


def radar_imagery_status(controller: RadarReplayHealthSource, clock: Callable[[], float]) -> str:
    tiles = controller.frame_tile_status
    if not isinstance(tiles, RadarTileStatus):
        return "Loading map imagery…"
    if tiles.failed:
        return "Some map imagery unavailable" if tiles.loaded else "Map imagery unavailable"
    if tiles.pending:
        return "Loading map imagery…"
    if not tiles.loaded:
        return "Waiting for map imagery…"
    text = (
        "Imagery loaded" if tiles.has_echoes is not False else "Loaded tiles have no visible echoes"
    )
    times = tuple(controller.frame_times)
    if times and controller.is_forecast and times[-1] < clock():
        text = "Forecast period has ended · " + text
    elif not controller.is_forecast and times and clock() - times[-1] > 1800:
        text = "Radar data is over 30 minutes old · " + text
    return text
