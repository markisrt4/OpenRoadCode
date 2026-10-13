# SPDX-License-Identifier: MIT

import socket
import threading
import time
from unittest.mock import Mock, patch

from protocols.oauth.oauth_redirect_server import OAuthRedirectServer


def test_cancelled_listener_releases_local_port_promptly():
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    cancelled = threading.Event()
    listening = threading.Event()
    results = []
    def current():
        listening.set()
        return not cancelled.is_set()
    server = OAuthRedirectServer(f"http://127.0.0.1:{port}/callback", timeout_seconds=120)
    worker = threading.Thread(target=lambda: results.append(server.wait_for_callback(is_current=current)), daemon=True)
    worker.start()
    try:
        assert listening.wait(2)
        cancelled.set()
        worker.join(2)
        assert not worker.is_alive()
        assert results[0].code is None
        with socket.socket() as replacement:
            replacement.bind(("127.0.0.1", port))
    finally:
        cancelled.set()
        worker.join(2)


def test_timeout_closes_listener_without_callback():
    fake_server = Mock()
    with patch("protocols.oauth.oauth_redirect_server.HTTPServer", return_value=fake_server), patch(
        "protocols.oauth.oauth_redirect_server.time.monotonic", side_effect=[0, 0, 0, 2]):
        result = OAuthRedirectServer("http://localhost:12345/callback", timeout_seconds=1).wait_for_callback()
    fake_server.handle_request.assert_called_once()
    fake_server.server_close.assert_called_once()
    assert result.code is None


def test_ready_callback_runs_after_listener_is_created_and_listener_closes_on_failure():
    fake_server = Mock()
    ready = Mock(side_effect=RuntimeError("browser failed"))
    with patch(
        "protocols.oauth.oauth_redirect_server.HTTPServer",
        return_value=fake_server,
    ) as server_factory:
        try:
            OAuthRedirectServer(
                "http://127.0.0.1:12345/callback"
            ).wait_for_callback(on_ready=ready)
        except RuntimeError as exc:
            assert str(exc) == "browser failed"
        else:
            raise AssertionError("ready callback failure was not propagated")

    server_factory.assert_called_once()
    ready.assert_called_once_with()
    fake_server.server_close.assert_called_once_with()


def test_live_callback_preserves_fields():
    from urllib.request import urlopen
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    results = []
    cancelled = threading.Event()
    server = OAuthRedirectServer(f"http://127.0.0.1:{port}/callback", timeout_seconds=3)
    worker = threading.Thread(target=lambda: results.append(server.wait_for_callback(is_current=lambda: not cancelled.is_set())), daemon=True)
    worker.start()
    try:
        deadline = time.monotonic() + 2
        while True:
            try:
                with urlopen(f"http://127.0.0.1:{port}/callback?code=code&state=state", timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
        worker.join(2)
        assert not worker.is_alive()
        assert results[0].code == "code" and results[0].state == "state"
    finally:
        cancelled.set()
        worker.join(2)
