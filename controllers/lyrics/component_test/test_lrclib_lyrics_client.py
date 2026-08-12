# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.lyrics import LrclibLyricsClient


class LrclibLyricsClientTest(unittest.TestCase):
    def test_parses_synchronized_lyrics(self) -> None:
        lines = LrclibLyricsClient.parse_synced(
            "[00:12.50] First line\n"
            "[00:15.125] Second line\n"
        )

        self.assertEqual(2, len(lines))
        self.assertEqual(12_500, lines[0].time_ms)
        self.assertEqual("First line", lines[0].text)
        self.assertEqual(15_125, lines[1].time_ms)

    def test_fetches_and_caches_track_lyrics(self) -> None:
        requested_urls: list[str] = []

        def fetch(url: str) -> dict[str, str]:
            requested_urls.append(url)
            return {
                "syncedLyrics": "[00:01.00] Hello",
                "plainLyrics": "Hello",
            }

        client = LrclibLyricsClient(fetch_json=fetch)
        first = client.get_lyrics(
            track_name="Song",
            artist_name="Artist",
            album_name="Album",
            duration_ms=180_000,
        )
        second = client.get_lyrics(
            track_name="Song",
            artist_name="Artist",
            album_name="Album",
            duration_ms=180_000,
        )

        self.assertIs(first, second)
        self.assertEqual(1, len(requested_urls))
        self.assertIn("duration=180", requested_urls[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
