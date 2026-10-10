# SPDX-License-Identifier: MIT

from unittest.mock import ANY, Mock, patch

import pytest

from protocols.spotify.spotify_auth import SpotifyAuth, SpotifyAuthError
from protocols.spotify.spotify_config import SpotifyConfig


def test_cancelled_login_does_not_open_browser_or_exchange_tokens():
    store = Mock()
    auth = SpotifyAuth(SpotifyConfig("public-client"), store)
    with patch("protocols.spotify.spotify_auth.webbrowser.open") as browser:
        with pytest.raises(SpotifyAuthError, match="cancelled"):
            auth.login(is_current=lambda: False)
    browser.assert_not_called()
    store.save.assert_not_called()


def test_cancellation_after_callback_prevents_exchange():
    store = Mock()
    auth = SpotifyAuth(SpotifyConfig("public-client"), store, open_browser=False)
    current = Mock(side_effect=[True, False])
    with patch("protocols.spotify.spotify_auth.OAuthRedirectServer") as server, patch.object(auth, "complete_authorization") as complete:
        with pytest.raises(SpotifyAuthError, match="cancelled"):
            auth.login(is_current=current)
        server.return_value.wait_for_callback.assert_called_once_with(is_current=current)
    complete.assert_not_called()
    store.save.assert_not_called()


def test_default_login_still_completes_authorization():
    auth = SpotifyAuth(SpotifyConfig("public-client"), Mock(), open_browser=False)
    with patch("protocols.spotify.spotify_auth.OAuthRedirectServer") as server, patch.object(auth, "complete_authorization") as complete:
        callback = server.return_value.wait_for_callback.return_value
        assert auth.login() is complete.return_value
        complete.assert_called_once_with(ANY,
            code=callback.code, state=callback.state, error=callback.error, error_description=callback.error_description)
