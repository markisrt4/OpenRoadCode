# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-facing orchestration for internet radio."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from .streaming_station import StreamingStation


class StreamingStationProviderIf(Protocol):
    """Discover stations without coupling the controller to one directory."""

    def stations_near(self, *, state: str, country: str = "United States") -> Sequence[StreamingStation]: ...


class StreamingAudioPlayerIf(Protocol):
    """Minimal player contract so PipeWire/VLC/mpv/etc. remain replaceable."""

    def play(self, stream_url: str) -> None: ...
    def stop(self) -> None: ...


class StreamingRadioController:
    """Discover and play internet stations while keeping UI code provider-free."""

    def __init__(self, provider: StreamingStationProviderIf, player: StreamingAudioPlayerIf) -> None:
        self._provider = provider
        self._player = player
        self._stations: tuple[StreamingStation, ...] = ()
        self._current_station: StreamingStation | None = None

    @property
    def stations(self) -> tuple[StreamingStation, ...]:
        return self._stations

    @property
    def current_station(self) -> StreamingStation | None:
        return self._current_station

    def refresh_region(self, *, state: str, country: str = "United States") -> tuple[StreamingStation, ...]:
        stations = self._provider.stations_near(state=state, country=country)
        self._stations = tuple(stations)
        return self._stations

    def play(self, station: StreamingStation) -> StreamingStation:
        self._player.play(station.stream_url)
        self._current_station = station
        return station

    def stop(self) -> None:
        self._player.stop()
        self._current_station = None


def default_image_cache_dir() -> Path:
    """Return the XDG cache location reserved for station artwork."""
    root = Path.home() / ".cache" if not (xdg := __import__("os").environ.get("XDG_CACHE_HOME")) else Path(xdg)
    return root / "openroadcode" / "streaming_radio" / "images"
