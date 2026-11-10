# SPDX-License-Identifier: MIT

"""Immutable Spotify presentation and semantic video requests."""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol

from ui.media.media_ui_if import MediaState
from ui.media import PlaybackRequestHandlerIf, TrackRequestHandlerIf, SeekRequestHandlerIf, VolumeRequestHandlerIf


@dataclass(frozen=True, slots=True)
class SpotifyPresentationState:
    media: MediaState = MediaState()
    online: bool = True
    artwork: bytes | None = None
    artwork_loading: bool = False
    lyric_current: str = ""
    lyric_next: str = ""
    video_available: bool | None = False
    video_process_id: int | None = None
    video_active: bool = False
    video_busy: bool = False
    message: str = ""


class SpotifyVideoRequests(Protocol):
    def request_watch_video(self) -> None:
        """Request a video for the displayed track."""
        ...

    def request_return_to_spotify(self) -> None:
        """Restore Spotify playback after a video."""
        ...


class SpotifyRequestHandler(PlaybackRequestHandlerIf, TrackRequestHandlerIf, SeekRequestHandlerIf, VolumeRequestHandlerIf):
    """Semantic controls bound only for the active presentation."""

    @abstractmethod
    def request_watch_video(self) -> None:
        """Request a video for the displayed track."""
        ...

    @abstractmethod
    def request_return_to_spotify(self) -> None:
        """Restore Spotify playback after a video."""
        ...


class SpotifyPresentationUi(Protocol):
    def set_spotify_request_handler(self, handler: SpotifyRequestHandler | None) -> None:
        """! @brief Bind or retire all semantic playback requests.

        @param handler Active request handler or None.
        """
        ...

    def set_spotify_state(self, state: SpotifyPresentationState) -> None:
        """! @brief Render an immutable presentation snapshot.

        @param state Snapshot owned by the presentation session.
        """
        ...

    def set_video_request_handler(self, handler: SpotifyVideoRequests | None) -> None:
        """! @brief Bind or retire semantic video requests.

        @param handler Request handler, or None to disconnect.
        """
        ...


class SpotifyPresentationSession(Protocol):
    def activate(self, view: SpotifyPresentationUi) -> None:
        """! @brief Bind one visible presentation.

        @param view Presentation receiving state.
        """
        ...

    def deactivate(self) -> None:
        """Retire deliveries while preserving shared playback."""
        ...

    def close(self) -> None:
        """Permanently retire the session."""
        ...


class SpotifyNativeSurface(Protocol):
    @property
    def window_id(self) -> int | None:
        """Return the attached native window, if any.

        @return Attached native window identifier or None.
        """
        ...

    def supported(self) -> bool:
        """Return whether native embedding is available.

        @return True when platform embedding is supported.
        """
        ...

    def embed(self, process_id: int, host_window_id: int, width: int, height: int, *, window_name: str | None = None, window_class: str | None = None, relax_size_hints: bool = False) -> int:
        """! @brief Attach a native process window.

        @param process_id Browser process to attach.
        @param host_window_id Native presentation host.
        @param width Host width in pixels.
        @param height Host height in pixels.
        @param window_name Optional window selector.
        @param window_class Optional class selector.
        @param relax_size_hints Whether to relax native size hints.
        @return Attached window identifier.
        """
        ...

    def detach(self, parent_window_id: int) -> None:
        """! @brief Detach before destroying the host.

        @param parent_window_id Surviving native parent.
        """
        ...

    def clear(self) -> None:
        """Forget native ownership after a detach failure."""
        ...

    def resize(self, width: int, height: int) -> None:
        """! @brief Resize the attached window.

        @param width Host width in pixels.
        @param height Host height in pixels.
        """
        ...
