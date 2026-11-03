# SPDX-License-Identifier: MIT
"""Spotify Connect device selection and explicit playback routing."""
import unittest
from unittest.mock import Mock

from controllers.spotify.spotify_web_api_controller import SpotifyWebApiController


class SpotifyDeviceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.controller = SpotifyWebApiController(self.client)

    def test_active_device_is_preferred(self):
        self.client.request_json.return_value = {"devices": [
            {"id": "a", "name": "Speaker", "is_active": False},
            {"id": "b", "name": "Phone", "is_active": True},
        ]}
        self.assertEqual(self.controller.select_playback_device()["id"], "b")

    def test_single_device_is_accepted(self):
        self.client.request_json.return_value = {"devices": [
            {"id": "phone", "name": "Phone", "is_active": False}
        ]}
        self.assertEqual(self.controller.select_playback_device()["id"], "phone")

    def test_multiple_inactive_devices_raise(self):
        self.client.request_json.return_value = {"devices": [
            {"id": "a", "name": "Speaker"}, {"id": "b", "name": "Phone"}
        ]}
        with self.assertRaisesRegex(RuntimeError, "No active Spotify Connect device"):
            self.controller.select_playback_device()

    def test_no_devices_raise(self):
        self.client.request_json.return_value = {"devices": []}
        with self.assertRaisesRegex(RuntimeError, "No Spotify Connect devices"):
            self.controller.select_playback_device()

    def test_playback_targets_device_id(self):
        self.controller.play_track("spotify:track:abc", device_id="phone123")
        self.client.request.assert_called_once_with(
            "PUT", "/me/player/play?device_id=phone123",
            body={"uris": ["spotify:track:abc"]},
        )


if __name__ == "__main__":
    unittest.main()
