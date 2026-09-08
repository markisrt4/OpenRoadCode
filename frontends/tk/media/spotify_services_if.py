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
        """Return synchronized or plain lyrics for one track.

        @param track_name Track title used for the lookup.
        @param artist_name Primary artist name used for the lookup.
        @param album_name Optional album name used to disambiguate the track.
        @param duration_ms Optional track duration in milliseconds.
        @return Lyrics result when found, otherwise None.
        """
        ...


class ArtworkProviderIf(Protocol):
    """Load decoded artwork sized for a Tk presentation."""

    def get(self, url: str, *, width: int, height: int) -> Image.Image:
        """Return decoded artwork for the requested URL and dimensions.

        @param url Remote artwork URL.
        @param width Requested output width in pixels.
        @param height Requested output height in pixels.
        @return Decoded and sized artwork image.
        """
        ...


class MusicVideoRequestHandlerIf(Protocol):
    """Coordinate the optional music-video transition from Spotify."""

    def current_track_has_video(self) -> bool:
        """Return whether the current track has a matching video.

        @return True when a matching music video is available.
        """
        ...

    def watch_current_track(self) -> bool:
        """Start a video for the current track when one can be found.

        @return True when video playback was started.
        """
        ...

    def return_to_spotify(self) -> None:
        """Stop video playback and restore Spotify playback."""
        ...

    def is_video_active(self) -> bool:
        """Return whether the music-video presentation is active.

        @return True when the music-video presentation is active.
        """
        ...


class MusicVideoPresentationIf(Protocol):
    """Expose the browser process used to present a music video."""

    @property
    def browser_process_id(self) -> int | None:
        """Return the active browser PID when a video window exists.

        @return Browser process identifier, or None when no browser is active.
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
        """Open a media target on the requested display.

        @param target Media URL or browser target to open.
        @param display X11 display target used for presentation.
        @param window_position Optional window position as an x/y pair.
        @param window_size Optional window size as a width/height pair.
        @return True when the media target was launched successfully.
        """
        ...

    def stop(self) -> None:
        """Stop the browser instance owned by this player."""
        ...
