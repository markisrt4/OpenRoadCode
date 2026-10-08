# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Narrow services consumed by the rich Spotify Tk frontend."""

from __future__ import annotations

from typing import Protocol

from PIL import Image


class LyricLineIf(Protocol):
    """Timestamped lyric line rendered by the Spotify panel."""

    time_ms: int
    text: str


class LyricsResultIf(Protocol):
    """Lyrics result shape required by the Spotify panel."""

    synced_lines: tuple[LyricLineIf, ...]
    plain_lines: tuple[str, ...]


class LyricsProviderIf(Protocol):
    """Look up lyrics without exposing a concrete provider to the frontend."""

    def get_lyrics(
        self,
        *,
        track_name: str,
        artist_name: str,
        album_name: str = "",
        duration_ms: int = 0,
    ) -> LyricsResultIf | None:
        """! @brief Return synchronized or plain lyrics for one track.

        @param track_name Track title used for the lyrics lookup.
        @param artist_name Artist name used for the lyrics lookup.
        @param album_name Optional album name used to improve lookup accuracy.
        @param duration_ms Optional track duration in milliseconds used to improve matching.
        @return Matching lyrics result, or None when lyrics are unavailable.
        """
        ...


class ArtworkProviderIf(Protocol):
    """Load decoded artwork sized for a Tk presentation."""

    def get(self, url: str, *, width: int, height: int) -> Image.Image:
        """! @brief Return decoded artwork for the requested URL and dimensions.

        @param url Artwork URL to retrieve.
        @param width Requested artwork width in pixels.
        @param height Requested artwork height in pixels.
        @return Decoded and sized artwork image.
        """
        ...


class MusicVideoRequestHandlerIf(Protocol):
    """Coordinate the optional music-video transition from Spotify."""

    def current_track_has_video(self) -> bool:
        """! @brief Return whether the current track has a matching video.

        @return True when a matching video is available, otherwise False.
        """
        ...

    def watch_current_track(self) -> bool:
        """! @brief Start a video for the current track when one can be found.

        @return True when video playback was started, otherwise False.
        """
        ...

    def return_to_spotify(self) -> None:
        """Stop video playback and restore Spotify playback."""
        ...

    def is_video_active(self) -> bool:
        """! @brief Return whether the music-video presentation is active.

        @return True while the music-video presentation is active, otherwise False.
        """
        ...


class MusicVideoPresentationIf(Protocol):
    """Expose the browser process used to present a music video."""

    @property
    def browser_process_id(self) -> int | None:
        """! @brief Return the active browser PID when a video window exists.

        @return Active browser process identifier, or None when no browser is active.
        """
        ...


class BrowserMediaPlayerIf(Protocol):
    """Launch and stop browser-hosted media for a Tk panel."""

    def play(
        self,
        target: str,
        *,
        display: str,
        window_position: tuple[int, int] | None = None,
        window_size: tuple[int, int] | None = None,
    ) -> bool:
        """! @brief Open a media target on the requested display.

        @param target Media URL or target understood by the browser-backed player.
        @param display X11 display on which the browser should be launched.
        @param window_position Optional x/y position for the browser window.
        @param window_size Optional width/height for the browser window.
        @return True when the media target was opened successfully, otherwise False.
        """
        ...

    def stop(self) -> None:
        """Stop the browser instance owned by this player."""
        ...
