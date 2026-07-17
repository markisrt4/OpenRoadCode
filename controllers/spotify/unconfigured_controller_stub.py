from controllers.spotify.spotify_controller_stub import SpotifyControllerStub
from controllers.spotify.spotify_state import SpotifyState


class UnconfiguredControllerStub(SpotifyControllerStub):
    """Notify consumers that Spotify setup is required."""

    def __init__(self, status_message: str = "Spotify is not configured") -> None:
        self._state = SpotifyState(
            is_available=False,
            configuration_required=True,
            status_message=status_message,
        )

    def current_state(self) -> SpotifyState:
        return self._state
