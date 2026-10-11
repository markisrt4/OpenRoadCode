# SPDX-License-Identifier: MIT

"""Shared-screen construction transfers cleanup only after successful startup."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from apps.carUi.composition.spotify import create_spotify_screen


@pytest.mark.parametrize("startup_fails", [False, True])
def test_cleanup_is_owned_or_rolled_back(startup_fails):
    dependencies = SimpleNamespace(
        spotify_controller=Mock(), audio_controller=Mock(), spotify_image_cache=Mock(),
        spotify_lyrics_client=Mock(), spotify_music_video_controller=Mock(), presentation_cleanup=[],
    )
    with patch("apps.carUi.composition.spotify.SpotifyStateService") as services, \
         patch("apps.carUi.composition.spotify.ThreadPoolExecutor") as pools, \
         patch("apps.carUi.composition.spotify.create_spotify_presentation") as sessions, \
         patch("apps.carUi.composition.spotify.SpotifyScreen") as screens, \
         patch("apps.carUi.composition.spotify.X11WindowEmbedder"):
        if startup_fails:
            services.return_value.start.side_effect = RuntimeError("startup")
            with pytest.raises(RuntimeError, match="startup"):
                create_spotify_screen(Mock(), dependencies, Mock())
            assert not dependencies.presentation_cleanup
        else:
            screen = create_spotify_screen(Mock(), dependencies, Mock())
            assert screen is screens.return_value
            sessions.return_value.close.assert_not_called()
            assert len(dependencies.presentation_cleanup) == 1
            dependencies.presentation_cleanup[0]()
        screens.return_value.hide.assert_called_once_with()
        sessions.return_value.close.assert_called_once_with()
        services.return_value.close.assert_called_once_with()
        pools.return_value.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
