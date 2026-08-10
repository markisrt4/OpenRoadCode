"""Tests for adapting Spotify behavior to generic media UI contracts."""

import unittest
from unittest.mock import Mock

from controllers.spotify import MockSpotifyController, SpotifyMediaPresenter
from ui.media import MediaAvailability, MediaState, MediaUiStub, PlaybackState


class RecordingMediaUi(MediaUiStub):
    def __init__(self) -> None:
        self.states: list[MediaState | None] = []

    def set_media_state(self, state: MediaState | None) -> None:
        self.states.append(state)


class SpotifyMediaPresenterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MockSpotifyController()
        self.media_ui = RecordingMediaUi()
        self.presenter = SpotifyMediaPresenter(self.backend, self.media_ui)

    def test_refresh_converts_spotify_state_to_generic_media_state(self) -> None:
        state = self.presenter.refresh()

        self.assertEqual(state.availability, MediaAvailability.AVAILABLE)
        self.assertEqual(state.playback, PlaybackState.PLAYING)
        self.assertEqual(state.title, "Tom Sawyer")
        self.assertEqual(state.artist, "Rush")
        self.assertEqual(state.duration_s, 276.0)
        self.assertIs(self.media_ui.states[-1], state)

    def test_pause_request_updates_backend_and_ui(self) -> None:
        self.presenter.request_pause()

        self.assertEqual(
            self.media_ui.states[-1].playback,  # type: ignore[union-attr]
            PlaybackState.PAUSED,
        )

    def test_track_volume_and_seek_requests_are_forwarded(self) -> None:
        self.presenter.request_next_track()
        self.presenter.request_volume(150)
        self.presenter.request_seek(12.5)

        state = self.presenter.refresh()
        self.assertEqual(state.title, "Go For Soda")
        self.assertEqual(state.volume_percent, 100)
        self.assertGreaterEqual(state.position_s or 0.0, 12.5)

    def test_disallowed_spotify_volume_uses_system_fallback(self) -> None:
        fallback = Mock()
        presenter = SpotifyMediaPresenter(
            self.backend,
            self.media_ui,
            fallback_volume_handler=fallback,
        )
        self.backend.set_volume_percent = Mock(
            side_effect=RuntimeError(
                "Spotify HTTP 403: VOLUME_CONTROL_DISALLOW"
            )
        )

        presenter.request_volume(65)

        fallback.request_volume.assert_called_once_with(65)


if __name__ == "__main__":
    unittest.main()
