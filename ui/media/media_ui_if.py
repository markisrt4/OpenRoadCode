"""! @brief Explicit UI contract and display values for media playback."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from ui.media.playback_request_handler_if import PlaybackRequestHandlerIf
from ui.media.seek_request_handler_if import SeekRequestHandlerIf
from ui.media.track_request_handler_if import TrackRequestHandlerIf
from ui.media.volume_request_handler_if import VolumeRequestHandlerIf
from ui.ui_if import UiIf


class PlaybackState(Enum):
    """! @brief Current media playback state."""

    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


@dataclass(frozen=True, slots=True)
class MediaState:
    """! @brief Represent the currently selected media and playback state.

    Optional fields are ``None`` when the media service cannot provide them.

    @param playback Current playback state.
    @param title Media title, or None when unavailable.
    @param artist Artist or creator name, or None when unavailable.
    @param album Album or collection name, or None when unavailable.
    @param artwork_uri Artwork location, or None when unavailable.
    @param media_uri Service-specific media identifier, or None when unavailable.
    @param position_s Current zero-based playback position in seconds.
    @param duration_s Total media duration in seconds.
    @param volume_percent Media playback volume from 0 through 100.
    @param device_name Active playback device name, or None when unavailable.
    """

    playback: PlaybackState = PlaybackState.STOPPED
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    artwork_uri: str | None = None
    media_uri: str | None = None
    position_s: float | None = None
    duration_s: float | None = None
    volume_percent: int | None = None
    device_name: str | None = None


class MediaUiIf(UiIf, ABC):
    """! @brief Display media state and connect media request handlers.

    ``None`` passed to set_media_state() means no media service or state
    is currently available.
    """

    @abstractmethod
    def set_media_state(self, state: MediaState | None) -> None:
        """! @brief Set the complete media display state.

        @param state Current media state, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_playback_request_handler(
        self,
        handler: PlaybackRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the playback request handler.

        @param handler Playback request handler, or None to disconnect it.
        """
        ...

    @abstractmethod
    def set_track_request_handler(
        self,
        handler: TrackRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the track-navigation request handler.

        @param handler Track request handler, or None to disconnect it.
        """
        ...

    @abstractmethod
    def set_seek_request_handler(
        self,
        handler: SeekRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the seek request handler.

        @param handler Seek request handler, or None to disconnect it.
        """
        ...

    @abstractmethod
    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the media volume request handler.

        @param handler Volume request handler, or None to disconnect it.
        """
        ...
