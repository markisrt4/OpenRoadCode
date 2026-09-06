# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify application controller backed by the Spotify Web API."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_library import SpotifyLibraryTrack
from controllers.spotify.spotify_state import SpotifyState
from protocols.spotify import SpotifyWebApiClient


class SpotifyWebApiController(SpotifyControllerIf):
    """Control Spotify playback and read user media through the Web API."""

    def __init__(self, client: SpotifyWebApiClient) -> None:
        """Create a Spotify controller.

        @param client Authenticated Spotify Web API transport.
        """
        self._client = client
        self._last_state = SpotifyState(is_available=False, status_message="Spotify not loaded")

    def current_state(self) -> SpotifyState:
        """Return the current Spotify playback snapshot."""
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
        """Resume the active Spotify playback context."""
        self._client.request("PUT", "/me/player/play")

    def pause(self) -> None:
        """Pause active Spotify playback."""
        self._client.request("PUT", "/me/player/pause")

    def play_pause(self) -> None:
        """Toggle active Spotify playback."""
        state = self.current_state()
        self.pause() if state.is_playing else self.play()

    def next_track(self) -> None:
        """Advance to the next track."""
        self._client.request("POST", "/me/player/next")

    def previous_track(self) -> None:
        """Return to the previous track."""
        self._client.request("POST", "/me/player/previous")

    def set_volume_percent(self, volume_percent: int) -> None:
        """Set playback volume, clamped to Spotify's 0-100 range."""
        clamped = max(0, min(100, volume_percent))
        self._client.request("PUT", f"/me/player/volume?volume_percent={clamped}")

    def seek_to_position_ms(self, position_ms: int) -> None:
        """Seek to a non-negative position in the current track."""
        position = max(0, position_ms)
        self._client.request("PUT", f"/me/player/seek?position_ms={position}")

    def transfer_playback(self, device_id: str, *, play: bool = True) -> None:
        """Transfer playback to a Spotify Connect device."""
        normalized_device_id = device_id.strip()
        if not normalized_device_id:
            raise ValueError("device_id cannot be empty")
        self._client.request("PUT", "/me/player", body={"device_ids": [normalized_device_id], "play": play})

    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return the user's saved tracks.

        @param limit Maximum number of tracks, clamped to 1 through 50.
        @return Parsed saved-track metadata.
        """
        response = self._client.request_json("GET", f"/me/tracks?{urlencode({'limit': self._limit(limit)})}") or {}
        return tuple(
            track
            for item in response.get("items") or []
            if isinstance(item, dict)
            for track in [self._library_track(item.get("track"))]
            if track is not None
        )

    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return the user's recent playback history.

        @param limit Maximum number of entries, clamped to 1 through 50.
        @return Parsed recent-track metadata including playback timestamps.
        """
        response = self._client.request_json("GET", f"/me/player/recently-played?{urlencode({'limit': self._limit(limit)})}") or {}
        tracks: list[SpotifyLibraryTrack] = []
        for item in response.get("items") or []:
            if not isinstance(item, dict):
                continue
            track = self._library_track(item.get("track"), played_at=item.get("played_at"))
            if track is not None:
                tracks.append(track)
        return tuple(tracks)

    def play_track(self, track_uri: str) -> None:
        """Start playback of one Spotify track URI."""
        normalized_uri = track_uri.strip()
        if not normalized_uri.startswith("spotify:track:"):
            raise ValueError("track_uri must be a Spotify track URI")
        self._client.request("PUT", "/me/player/play", body={"uris": [normalized_uri]})

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

    @classmethod
    def _library_track(cls, track: object, *, played_at: object = None) -> SpotifyLibraryTrack | None:
        if not isinstance(track, dict):
            return None
        name = track.get("name")
        uri = track.get("uri")
        if not isinstance(name, str) or not name or not isinstance(uri, str) or not uri:
            return None
        album = track.get("album") if isinstance(track.get("album"), dict) else {}
        artists = track.get("artists") if isinstance(track.get("artists"), list) else []
        return SpotifyLibraryTrack(
            name=name,
            artist_name=cls._extract_artist_name(artists) or "Unknown artist",
            album_name=album.get("name") if isinstance(album.get("name"), str) else None,
            uri=uri,
            album_art_url=cls._extract_album_art_url(album),
            played_at=played_at if isinstance(played_at, str) else None,
        )

    @staticmethod
    def _limit(limit: int) -> int:
        return max(1, min(50, int(limit)))

    @staticmethod
    def _extract_artist_name(artists: list[dict[str, Any]]) -> str | None:
        names = [str(artist["name"]) for artist in artists if isinstance(artist, dict) and artist.get("name") is not None]
        return ", ".join(names) if names else None

    @staticmethod
    def _extract_album_art_url(album: dict[str, Any]) -> str | None:
        for image in album.get("images") or []:
            if not isinstance(image, dict):
                continue
            url = image.get("url")
            if isinstance(url, str) and url:
                return url
        return None
