# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic in-memory Spotify controller for development."""

import time

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_library import SpotifyLibraryTrack
from controllers.spotify.spotify_state import SpotifyState


class MockSpotifyController(SpotifyControllerIf):
    """Deterministic in-memory Spotify controller for demos and development."""

    def __init__(self) -> None:
        self._tracks = [
            ("Tom Sawyer", "Rush", "Moving Pictures", 276_000),
            ("Go For Soda", "Kim Mitchell", "Akimbo Alogo", 202_000),
            ("Carry On Wayward Son", "Kansas", "Leftoverture", 323_000),
            ("Subdivisions", "Rush", "Signals", 334_000),
        ]
        self._track_index = 0
        self._is_playing = True
        self._volume_percent = 70
        self._device_name = "Mock Phone"
        self._track_started_at = time.monotonic()
        self._paused_progress_ms = 0

    def current_state(self) -> SpotifyState:
        """Return the current deterministic playback state."""
        track_name, artist_name, album_name, duration_ms = self._tracks[self._track_index]
        return SpotifyState(is_available=True,is_playing=self._is_playing,track_name=track_name,artist_name=artist_name,album_name=album_name,track_uri=f"spotify:track:mock-{self._track_index}",device_name=self._device_name,volume_percent=self._volume_percent,progress_ms=self._current_progress_ms(duration_ms),duration_ms=duration_ms,status_message="Playing" if self._is_playing else "Paused")

    def play(self) -> None:
        if self._is_playing:return
        self._track_started_at=time.monotonic()-(self._paused_progress_ms/1000.0); self._is_playing=True
    def pause(self) -> None:
        if not self._is_playing:return
        _,_,_,duration_ms=self._tracks[self._track_index]; self._paused_progress_ms=self._current_progress_ms(duration_ms); self._is_playing=False
    def play_pause(self) -> None:self.pause() if self._is_playing else self.play()
    def next_track(self) -> None:self._set_track((self._track_index+1)%len(self._tracks))
    def previous_track(self) -> None:self._set_track((self._track_index-1)%len(self._tracks))
    def set_volume_percent(self,volume_percent:int)->None:self._volume_percent=max(0,min(100,volume_percent))
    def seek_to_position_ms(self,position_ms:int)->None:
        _,_,_,duration_ms=self._tracks[self._track_index]; position_ms=max(0,min(duration_ms,position_ms)); self._paused_progress_ms=position_ms
        if self._is_playing:self._track_started_at=time.monotonic()-(position_ms/1000.0)
    def transfer_playback(self,device_id:str,*,play:bool=True)->None:
        normalized=device_id.strip()
        if not normalized:raise ValueError("device_id cannot be empty")
        self._device_name=normalized; self.play() if play else self.pause()

    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return deterministic mock saved tracks."""
        return self._library_tracks(limit)

    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return deterministic mock playback history."""
        return self._library_tracks(limit)

    def play_track(self, track_uri: str) -> None:
        """Select a mock track from its generated Spotify URI."""
        prefix="spotify:track:mock-"
        if not track_uri.startswith(prefix):raise ValueError("unknown mock Spotify track URI")
        index=int(track_uri[len(prefix):])
        if index < 0 or index >= len(self._tracks):raise ValueError("unknown mock Spotify track URI")
        self._set_track(index); self.play()

    def _library_tracks(self,limit:int)->tuple[SpotifyLibraryTrack,...]:
        count=max(1,min(len(self._tracks),int(limit)))
        return tuple(SpotifyLibraryTrack(name=name,artist_name=artist,album_name=album,uri=f"spotify:track:mock-{index}") for index,(name,artist,album,_duration) in enumerate(self._tracks[:count]))
    def _set_track(self,index:int)->None:self._track_index=index; self._reset_progress()
    def _reset_progress(self)->None:self._track_started_at=time.monotonic(); self._paused_progress_ms=0
    def _current_progress_ms(self,duration_ms:int)->int:
        if not self._is_playing:return self._paused_progress_ms
        elapsed_ms=int((time.monotonic()-self._track_started_at)*1000)
        if elapsed_ms>=duration_ms:self.next_track(); return 0
        return elapsed_ms
