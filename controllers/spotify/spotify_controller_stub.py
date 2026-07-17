from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_state import SpotifyState


class SpotifyControllerStub(SpotifyControllerIf):
    """Minimal no-op Spotify controller."""

    def current_state(self) -> SpotifyState:
        return SpotifyState()

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
