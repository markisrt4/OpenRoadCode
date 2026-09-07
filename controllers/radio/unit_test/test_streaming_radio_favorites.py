# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from controllers.radio.streaming_radio_types import StreamingRadioStation


class StreamingRadioFavoritesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config" / "streaming_radio.toml"
        self.station = StreamingRadioStation(station_id="wmuz", name="103.5 The Light", stream_url="https://example.com/live", tags=("christian", "talk"), bitrate_kbps=128)

    def test_missing_file_starts_empty(self):
        self.assertEqual(StreamingRadioFavorites(self.path).stations, ())

    def test_round_trip_and_remove(self):
        store = StreamingRadioFavorites(self.path)
        self.assertTrue(store.toggle(self.station))
        restored = StreamingRadioFavorites(self.path)
        self.assertEqual(restored.station_ids, {"wmuz"})
        self.assertEqual(restored.stations[0].name, "103.5 The Light")
        self.assertEqual(tuple(restored.stations[0].tags), ("christian", "talk"))
        self.assertFalse(restored.toggle(self.station))
        self.assertEqual(StreamingRadioFavorites(self.path).stations, ())

    def test_failed_write_does_not_change_memory_or_existing_file(self):
        store = StreamingRadioFavorites(self.path)
        store.toggle(self.station)
        before = self.path.read_bytes()
        with patch("controllers.radio.streaming_radio_favorites.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                store.toggle(self.station)
        self.assertEqual(store.station_ids, {"wmuz"})
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_file_is_not_silently_overwritten(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("not valid = [", encoding="utf-8")
        with self.assertRaises(Exception):
            StreamingRadioFavorites(self.path)


if __name__ == "__main__":
    unittest.main()
