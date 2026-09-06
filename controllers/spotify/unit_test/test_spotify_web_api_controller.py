# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from typing import Any

from controllers.spotify.spotify_web_api_controller import SpotifyWebApiController


class _RecordingClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def request(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> None:
        self.requests.append((method, path, body))

    def request_json(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return None


class SpotifyWebApiControllerTest(unittest.TestCase):
    def test_transfer_playback_selects_device_and_resumes(self) -> None:
        client = _RecordingClient()
        controller = SpotifyWebApiController(client)  # type: ignore[arg-type]

        controller.transfer_playback("orc-device")

        self.assertEqual(
            client.requests,
            [("PUT", "/me/player", {"device_ids": ["orc-device"], "play": True})],
        )

    def test_transfer_playback_can_preserve_paused_state(self) -> None:
        client = _RecordingClient()
        controller = SpotifyWebApiController(client)  # type: ignore[arg-type]

        controller.transfer_playback("orc-device", play=False)

        self.assertEqual(
            client.requests,
            [("PUT", "/me/player", {"device_ids": ["orc-device"], "play": False})],
        )

    def test_transfer_playback_rejects_empty_device_id(self) -> None:
        controller = SpotifyWebApiController(_RecordingClient())  # type: ignore[arg-type]

        with self.assertRaises(ValueError):
            controller.transfer_playback("   ")


if __name__ == "__main__":
    unittest.main()
