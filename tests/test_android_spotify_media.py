# SPDX-License-Identifier: MIT
"""Tests for the local Android Spotify media transport."""

import io
import json
import unittest
from unittest.mock import patch

from apps.orcUi.adapters.android_spotify_media import AndroidSpotifyMedia


class AndroidSpotifyMediaTests(unittest.TestCase):
    def test_status_decodes_session(self):
        payload = {"permission_granted": True, "session_found": True, "title": "Lunatic Fringe"}
        with patch("apps.orcUi.adapters.android_spotify_media.urlopen") as open_url:
            open_url.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
            self.assertEqual(AndroidSpotifyMedia().status(), payload)

    def test_command_uses_form_encoded_post(self):
        with patch("apps.orcUi.adapters.android_spotify_media.urlopen") as open_url:
            open_url.return_value.__enter__.return_value = io.BytesIO(b'{"status":"requested"}')
            result = AndroidSpotifyMedia().command("pause")
            request = open_url.call_args.args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.data, b"command=pause")
            self.assertEqual(result["status"], "requested")

    def test_rejects_unknown_command(self):
        with self.assertRaises(ValueError):
            AndroidSpotifyMedia().command("play-track")


if __name__ == "__main__":
    unittest.main()
