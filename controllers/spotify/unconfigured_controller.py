# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify controller used when runtime credentials are unavailable."""

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_library import SpotifyLibraryTrack
from controllers.spotify.spotify_state import SpotifyState


class UnconfiguredController(SpotifyControllerIf):
    """Notify consumers that Spotify setup is required."""

    def __init__(self, status_message: str = "Spotify is not configured") -> None:
        self._state = SpotifyState(is_available=False, configuration_required=True, status_message=status_message)

    def current_state(self) -> SpotifyState:
        """Return the configuration-required state."""
        return self._state

    def play(self) -> None: pass
    def pause(self) -> None: pass
    def play_pause(self) -> None: pass
    def next_track(self) -> None: pass
    def previous_track(self) -> None: pass
    def set_volume_percent(self, volume_percent: int) -> None: pass
    def seek_to_position_ms(self, position_ms: int) -> None: pass
    def transfer_playback(self, device_id: str, *, play: bool = True) -> None: pass

    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return no saved tracks while Spotify is unconfigured."""
        return ()

    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return no history while Spotify is unconfigured."""
        return ()

    def play_track(self, track_uri: str) -> None:
        """Ignore playback requests while Spotify is unconfigured."""
