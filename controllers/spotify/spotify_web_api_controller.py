# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_state import SpotifyState
from protocols.spotify import SpotifyWebApiClient


class SpotifyWebApiController(SpotifyControllerIf):
    """Controls Spotify playback through the Spotify Web API."""

    def __init__(self, client: SpotifyWebApiClient) -> None:
        self._client = client
        self._last_state = SpotifyState(is_available=False, status_message="Spotify not loaded")

    def current_state(self) -> SpotifyState:
        try:
            response = self._client.request_json("GET", "/me/player")
            if response is None:
                self._last_state = SpotifyState(is_available=False, status_message="No active Spotify playback")
                return self._last_state
            self._last_state = self._create_state(response)
            return self._last_state
        except Exception as exc:
            self._last_state = SpotifyState(is_available=False, status_message=f"Spotify error: {exc}")
            return self._last_state

    def play(self) -> None:
        self._client.request("PUT", "/me/player/play")

    def pause(self) -> None:
        self._client.request("PUT", "/me/player/pause")

    def play_pause(self) -> None:
        state = self.current_state()
        self.pause() if state.is_playing else self.play()

    def next_track(self) -> None:
        self._client.request("POST", "/me/player/next")

    def previous_track(self) -> None:
        self._client.request("POST", "/me/player/previous")

    def set_volume_percent(self, volume_percent: int) -> None:
        clamped = max(0, min(100, volume_percent))
        self._client.request("PUT", f"/me/player/volume?volume_percent={clamped}")

    def seek_to_position_ms(self, position_ms: int) -> None:
        position = max(0, position_ms)
        self._client.request("PUT", f"/me/player/seek?position_ms={position}")

    def _create_state(self, response: dict[str, Any]) -> SpotifyState:
        item = response.get("item") or {}
        album = item.get("album") or {}
        artists = item.get("artists") or []
        device = response.get("device") or {}
        external_urls = item.get("external_urls") or {}
        is_playing = bool(response.get("is_playing"))
        supports_volume_value = device.get("supports_volume")
        supports_volume = supports_volume_value if isinstance(supports_volume_value, bool) else None

        return SpotifyState(
            is_available=True,
            is_playing=is_playing,
            track_name=item.get("name"),
            artist_name=self._extract_artist_name(artists),
            album_name=album.get("name"),
            track_uri=item.get("uri"),
            album_art_url=self._extract_album_art_url(album),
            spotify_url=external_urls.get("spotify"),
            release_date=album.get("release_date"),
            device_name=device.get("name"),
            volume_percent=device.get("volume_percent"),
            supports_volume=supports_volume,
            progress_ms=response.get("progress_ms"),
            duration_ms=item.get("duration_ms"),
            status_message="Playing" if is_playing else "Paused",
        )

    @staticmethod
    def _extract_artist_name(artists: list[dict[str, Any]]) -> str | None:
        names = [str(artist["name"]) for artist in artists if artist.get("name") is not None]
        return ", ".join(names) if names else None

    @staticmethod
    def _extract_album_art_url(album: dict[str, Any]) -> str | None:
        for image in album.get("images") or []:
            url = image.get("url")
            if isinstance(url, str) and url:
                return url
        return None
