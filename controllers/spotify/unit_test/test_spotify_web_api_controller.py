# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from typing import Any

from controllers.spotify.spotify_web_api_controller import SpotifyWebApiController


class _RecordingClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []
        self.responses: dict[str, dict[str, Any] | None] = {}

    def request(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> None:
        self.requests.append((method, path, body))

    def request_json(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> dict[str, Any] | None:
        self.requests.append((method, path, body))
        return self.responses.get(path)


class SpotifyWebApiControllerTest(unittest.TestCase):
    def test_transfer_playback_selects_device_and_resumes(self) -> None:
        client=_RecordingClient(); controller=SpotifyWebApiController(client)  # type: ignore[arg-type]
        controller.transfer_playback("orc-device")
        self.assertEqual(client.requests,[("PUT","/me/player",{"device_ids":["orc-device"],"play":True})])

    def test_transfer_playback_can_preserve_paused_state(self) -> None:
        client=_RecordingClient(); controller=SpotifyWebApiController(client)  # type: ignore[arg-type]
        controller.transfer_playback("orc-device",play=False)
        self.assertEqual(client.requests,[("PUT","/me/player",{"device_ids":["orc-device"],"play":False})])

    def test_transfer_playback_rejects_empty_device_id(self) -> None:
        controller=SpotifyWebApiController(_RecordingClient())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):controller.transfer_playback("   ")

    def test_saved_tracks_parses_library_items(self) -> None:
        client=_RecordingClient(); path="/me/tracks?limit=2"; client.responses[path]={"items":[{"track":{"name":"Song","uri":"spotify:track:123","artists":[{"name":"Artist"}],"album":{"name":"Album","images":[{"url":"art"}]}}}]}; controller=SpotifyWebApiController(client)  # type: ignore[arg-type]
        tracks=controller.saved_tracks(limit=2)
        self.assertEqual(len(tracks),1); self.assertEqual(tracks[0].name,"Song"); self.assertEqual(tracks[0].artist_name,"Artist"); self.assertEqual(tracks[0].album_art_url,"art")

    def test_recently_played_preserves_played_at(self) -> None:
        client=_RecordingClient(); path="/me/player/recently-played?limit=1"; client.responses[path]={"items":[{"played_at":"2026-09-05T12:00:00Z","track":{"name":"Song","uri":"spotify:track:123","artists":[{"name":"Artist"}],"album":{"name":"Album"}}}]}; controller=SpotifyWebApiController(client)  # type: ignore[arg-type]
        tracks=controller.recently_played(limit=1)
        self.assertEqual(tracks[0].played_at,"2026-09-05T12:00:00Z")

    def test_play_track_uses_uri_list(self) -> None:
        client=_RecordingClient(); controller=SpotifyWebApiController(client)  # type: ignore[arg-type]
        controller.play_track("spotify:track:123")
        self.assertEqual(client.requests,[("PUT","/me/player/play",{"uris":["spotify:track:123"]})])

    def test_play_track_rejects_non_track_uri(self) -> None:
        controller=SpotifyWebApiController(_RecordingClient())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):controller.play_track("https://example.com")


if __name__=="__main__":unittest.main()
