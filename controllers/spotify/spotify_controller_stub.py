# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""No-op Spotify controller for application composition and tests."""

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_library import SpotifyLibraryTrack
from controllers.spotify.spotify_state import SpotifyState


class SpotifyControllerStub(SpotifyControllerIf):
    """Minimal no-op implementation of the Spotify controller contract."""

    def current_state(self) -> SpotifyState:
        """Return an unavailable default state."""
        return SpotifyState()

    def play(self) -> None: pass
    def pause(self) -> None: pass
    def play_pause(self) -> None: pass
    def next_track(self) -> None: pass
    def previous_track(self) -> None: pass
    def set_volume_percent(self, volume_percent: int) -> None: pass
    def seek_to_position_ms(self, position_ms: int) -> None: pass
    def transfer_playback(self, device_id: str, *, play: bool = True) -> None: pass

    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return an empty saved-track collection."""
        return ()

    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return an empty playback-history collection."""
        return ()

    def play_track(self, track_uri: str) -> None:
        """Ignore a requested track in the no-op implementation."""
