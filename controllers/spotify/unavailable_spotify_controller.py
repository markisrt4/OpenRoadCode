from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_state import SpotifyState


class UnavailableSpotifyController(SpotifyControllerIf):
    """Represent an optional Spotify integration that is not configured."""

    def __init__(self, status_message: str = "Spotify is not configured") -> None:
        self._state = SpotifyState(
            is_available=False,
            status_message=status_message,
        )

    def current_state(self) -> SpotifyState:
        return self._state

    def play_pause(self) -> None:
        pass

    def next_track(self) -> None:
        pass

    def previous_track(self) -> None:
        pass

    def set_volume_percent(self, volume_percent: int) -> None:
        pass

    def seek_to_position_ms(self, position_ms: int) -> None:
        pass
