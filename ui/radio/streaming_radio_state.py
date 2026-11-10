# SPDX-License-Identifier: MIT

"""Immutable streaming-radio values shared by browser and Home presentation."""

from dataclasses import dataclass
from enum import Enum

from .streaming_radio_types import StreamingRadioStation


class StreamingRadioBrowseMode(str, Enum):
    LOCAL = "local"
    REGIONAL = "regional"
    FAVORITES = "favorites"


@dataclass(frozen=True, slots=True)
class StreamingRadioPlaybackState:
    station: StreamingRadioStation | None = None
    is_playing: bool = False


@dataclass(frozen=True, slots=True)
class StreamingRadioBrowserState:
    mode: StreamingRadioBrowseMode = StreamingRadioBrowseMode.LOCAL
    stations: tuple[StreamingRadioStation, ...] = ()
    favorite_station_ids: frozenset[str] = frozenset()
    playback: StreamingRadioPlaybackState = StreamingRadioPlaybackState()
    playback_busy: bool = False
    loading: bool = False
    message: str = ""
    error: bool = False
