# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Explicit UI contract and display values for media playback."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from ui.media.playback_request_handler_if import PlaybackRequestHandlerIf
from ui.media.seek_request_handler_if import SeekRequestHandlerIf
from ui.media.track_request_handler_if import TrackRequestHandlerIf
from ui.media.volume_request_handler_if import VolumeRequestHandlerIf


class PlaybackState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


class MediaAvailability(Enum):
    AVAILABLE = auto()
    UNAVAILABLE = auto()
    CONFIGURATION_REQUIRED = auto()
    ERROR = auto()


@dataclass(frozen=True, slots=True)
class MediaState:
    """Toolkit-independent media playback snapshot."""

    availability: MediaAvailability = MediaAvailability.UNAVAILABLE
    playback: PlaybackState = PlaybackState.STOPPED
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    artwork_uri: str | None = None
    media_uri: str | None = None
    position_s: float | None = None
    duration_s: float | None = None
    volume_percent: int | None = None
    supports_volume: bool | None = None
    device_name: str | None = None
    status_message: str | None = None


class MediaUiIf(ABC):
    @abstractmethod
    def set_media_state(self, state: MediaState | None) -> None:
        """! @brief Display the latest media playback state."""
        ...

    @abstractmethod
    def set_playback_request_handler(self, handler: PlaybackRequestHandlerIf | None) -> None:
        """! @brief Set the handler for playback control requests."""
        ...

    @abstractmethod
    def set_track_request_handler(self, handler: TrackRequestHandlerIf | None) -> None:
        """! @brief Set the handler for track navigation requests."""
        ...

    @abstractmethod
    def set_seek_request_handler(self, handler: SeekRequestHandlerIf | None) -> None:
        """! @brief Set the handler for playback seek requests."""
        ...

    @abstractmethod
    def set_volume_request_handler(self, handler: VolumeRequestHandlerIf | None) -> None:
        """! @brief Set the handler for media volume requests."""
        ...
