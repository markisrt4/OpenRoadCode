# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from protocols.oauth import OAuthCallbackResult
from protocols.spotify.spotify_auth import SpotifyAuth, SpotifyAuthorizationRequest


def test_login_binds_callback_before_waiting_for_browser_redirect() -> None:
    auth=SpotifyAuth.__new__(SpotifyAuth)
    auth._config=SimpleNamespace(redirect_uri="http://127.0.0.1:8888/callback")
    auth._callback_timeout_seconds=120.0;auth._open_browser=False
    request=SpotifyAuthorizationRequest("https://accounts.test/authorize","state","verifier")
    auth.begin_authorization=Mock(return_value=request)
    auth.complete_authorization=Mock(return_value="tokens")
    callback=OAuthCallbackResult(code="code",state="state")
    with patch("protocols.spotify.spotify_auth.OAuthRedirectServer") as server_type:
        server_type.return_value.wait_for_callback.return_value=callback
        assert auth.login() == "tokens"
    assert server_type.return_value.method_calls[:2] == [call.start(),call.wait_for_callback()]
