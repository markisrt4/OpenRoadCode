# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from apps.orcUi.spotify_local_player import SpotifyLocalPlayer, SpotifyPlaybackMode


class _SpotifyService:
    def __init__(self) -> None:
        self.transfers: list[tuple[str, bool]] = []

    def request_transfer_playback(self, device_id: str, *, play: bool = True) -> None:
        self.transfers.append((device_id, play))


class _Host:
    url = "http://127.0.0.1:8771/"

    def __init__(self) -> None:
        self.device_id: str | None = None
        self.error: str | None = None
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True
        self.device_id = "orc-device"

    def close(self) -> None:
        self.closed = True


class _Browser:
    def __init__(self) -> None:
        self.launched = False
        self.hidden = False
        self.stopped = False

    def launch(self, _display: str) -> None:
        self.launched = True

    def hide(self, _display: str) -> bool:
        self.hidden = True
        return True

    def stop(self, _display: str) -> None:
        self.stopped = True


class SpotifyLocalPlayerTest(unittest.TestCase):
    def _wait_until_idle(self, player: SpotifyLocalPlayer) -> None:
        deadline = time.monotonic() + 1.0
        while player.state().busy and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(player.state().busy)

    @patch("apps.orcUi.spotify_local_player.shutil.which", return_value="/usr/bin/google-chrome-stable")
    def test_player_mode_registers_transfers_and_hides_browser(self, _which) -> None:
        service = _SpotifyService()
        host = _Host()
        browser = _Browser()
        player = SpotifyLocalPlayer(
            spotify_service=service,  # type: ignore[arg-type]
            host_factory=lambda: host,  # type: ignore[arg-type]
            browser_factory=lambda _url: browser,  # type: ignore[arg-type]
            registration_timeout_seconds=0.5,
        )

        player.request_player()
        self._wait_until_idle(player)

        self.assertEqual(player.state().mode, SpotifyPlaybackMode.PLAYER)
        self.assertEqual(service.transfers, [("orc-device", True)])
        self.assertTrue(host.started)
        self.assertTrue(browser.launched)
        self.assertTrue(browser.hidden)
        player.close()

    @patch("apps.orcUi.spotify_local_player.shutil.which", return_value=None)
    def test_player_mode_is_unavailable_without_supported_chrome(self, _which) -> None:
        service = _SpotifyService()
        player = SpotifyLocalPlayer(spotify_service=service)  # type: ignore[arg-type]

        player.request_player()

        self.assertEqual(player.state().mode, SpotifyPlaybackMode.REMOTE)
        self.assertFalse(player.state().available)
        self.assertEqual(service.transfers, [])


if __name__ == "__main__":
    unittest.main()
