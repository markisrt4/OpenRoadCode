# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_state import SpotifyState
from protocols.spotify import SpotifyWebApiClient


class SpotifyWebApiController(SpotifyControllerIf):
    """
    Controls Spotify playback through the Spotify Web API.
    """

    def __init__(
        self,
        client: SpotifyWebApiClient,
    ) -> None:
        self._client = client
        self._last_state = SpotifyState(
            is_available=False,
            status_message="Spotify not loaded",
        )

    def current_state(self) -> SpotifyState:
        """
        Return the current Spotify playback state.
        """
        try:
            response = self._client.request_json(
                "GET",
                "/me/player",
            )

            if response is None:
                self._last_state = SpotifyState(
                    is_available=False,
                    status_message="No active Spotify playback",
                )
                return self._last_state

            self._last_state = self._create_state(response)
            return self._last_state

        except Exception as exc:
            self._last_state = SpotifyState(
                is_available=False,
                status_message=f"Spotify error: {exc}",
            )
            return self._last_state

    def play(self) -> None:
        """Start or resume playback."""
        self._client.request(
            "PUT",
            "/me/player/play",
        )

    def pause(self) -> None:
        """Pause playback."""
        self._client.request(
            "PUT",
            "/me/player/pause",
        )

    def play_pause(self) -> None:
        """Toggle between playing and paused."""
        state = self.current_state()

        if state.is_playing:
            self.pause()
        else:
            self.play()

    def next_track(self) -> None:
        """
        Skip to the next track.
        """
        self._client.request(
            "POST",
            "/me/player/next",
        )

    def previous_track(self) -> None:
        """
        Return to the previous track.
        """
        self._client.request(
            "POST",
            "/me/player/previous",
        )

    def set_volume_percent(
        self,
        volume_percent: int,
    ) -> None:
        """
        Set the active Spotify device volume.
        """
        clamped = max(
            0,
            min(100, volume_percent),
        )

        self._client.request(
            "PUT",
            (
                "/me/player/volume"
                f"?volume_percent={clamped}"
            ),
        )

    def seek_to_position_ms(
        self,
        position_ms: int,
    ) -> None:
        """
        Seek to a playback position in milliseconds.
        """
        position = max(0, position_ms)

        self._client.request(
            "PUT",
            (
                "/me/player/seek"
                f"?position_ms={position}"
            ),
        )

    def _create_state(
        self,
        response: dict[str, Any],
    ) -> SpotifyState:
        item = response.get("item") or {}
        album = item.get("album") or {}
        artists = item.get("artists") or []
        device = response.get("device") or {}

        artist_name = self._extract_artist_name(
            artists
        )

        album_art_url = self._extract_album_art_url(
            album
        )

        external_urls = item.get(
            "external_urls"
        ) or {}

        is_playing = bool(
            response.get("is_playing")
        )

        return SpotifyState(
            is_available=True,
            is_playing=is_playing,
            track_name=item.get("name"),
            artist_name=artist_name,
            album_name=album.get("name"),
            track_uri=item.get("uri"),
            album_art_url=album_art_url,
            spotify_url=external_urls.get("spotify"),
            release_date=album.get("release_date"),
            device_name=device.get("name"),
            volume_percent=device.get(
                "volume_percent"
            ),
            progress_ms=response.get(
                "progress_ms"
            ),
            duration_ms=item.get(
                "duration_ms"
            ),
            status_message=(
                "Playing"
                if is_playing
                else "Paused"
            ),
        )

    @staticmethod
    def _extract_artist_name(
        artists: list[dict[str, Any]],
    ) -> str | None:
        names = [
            str(artist["name"])
            for artist in artists
            if artist.get("name") is not None
        ]

        if not names:
            return None

        return ", ".join(names)

    @staticmethod
    def _extract_album_art_url(
        album: dict[str, Any],
    ) -> str | None:
        images = album.get("images") or []

        if not images:
            return None

        for image in images:
            url = image.get("url")

            if isinstance(url, str) and url:
                return url

        return None
