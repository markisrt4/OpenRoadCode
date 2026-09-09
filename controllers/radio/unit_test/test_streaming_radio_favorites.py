# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers.cache import PersistentCache
from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites


class StreamingRadioFavoritesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "data"
        self.storage = PersistentCache(self.directory, suffix=".json")
        self.legacy_path = Path(self.temp.name) / "config" / "streaming_radio.toml"

    def _store(self) -> StreamingRadioFavorites:
        return StreamingRadioFavorites(
            self.storage,
            legacy_path=self.legacy_path,
        )

    def test_missing_storage_starts_empty(self):
        self.assertEqual(self._store().ordered_station_ids, ())

    def test_round_trip_stores_only_station_ids(self):
        store = self._store()
        self.assertTrue(store.toggle("station-uuid-1"))
        self.assertTrue(store.toggle("station-uuid-2"))

        restored = self._store()
        self.assertEqual(
            restored.ordered_station_ids,
            ("station-uuid-1", "station-uuid-2"),
        )

        payload = self.storage.get(StreamingRadioFavorites.CACHE_KEY)
        self.assertIsNotNone(payload)
        assert payload is not None
        text = payload.decode("utf-8")
        self.assertIn('"station_ids"', text)
        self.assertNotIn("stream_url", text)
        self.assertNotIn("artwork", text)

    def test_toggle_remove_preserves_other_favorite_order(self):
        store = self._store()
        store.toggle("one")
        store.toggle("two")
        store.toggle("three")
        self.assertFalse(store.toggle("two"))
        self.assertEqual(store.ordered_station_ids, ("one", "three"))

    def test_failed_write_does_not_change_memory_or_existing_data(self):
        store = self._store()
        store.toggle("station-uuid-1")
        before = self.storage.get(StreamingRadioFavorites.CACHE_KEY)
        with patch.object(self.storage, "put", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                store.toggle("station-uuid-1")
        self.assertEqual(store.station_ids, {"station-uuid-1"})
        self.assertEqual(
            self.storage.get(StreamingRadioFavorites.CACHE_KEY),
            before,
        )

    def test_invalid_persisted_data_is_not_silently_replaced(self):
        self.storage.put(StreamingRadioFavorites.CACHE_KEY, b"not-json")
        with self.assertRaises(ValueError):
            self._store()
        self.assertEqual(
            self.storage.get(StreamingRadioFavorites.CACHE_KEY),
            b"not-json",
        )

    def test_migrates_station_ids_from_previous_toml_format(self):
        self.legacy_path.parent.mkdir(parents=True)
        self.legacy_path.write_text(
            """version = 1

[[favorites]]
station_id = \"legacy-one\"
name = \"Old metadata is deliberately ignored\"
stream_url = \"https://old.example/live\"

[[favorites]]
station_id = \"legacy-two\"
name = \"Another old station\"
stream_url = \"https://old.example/two\"
""",
            encoding="utf-8",
        )

        store = self._store()
        self.assertEqual(
            store.ordered_station_ids,
            ("legacy-one", "legacy-two"),
        )
        self.assertTrue(self.legacy_path.exists())
        self.assertIsNotNone(
            self.storage.get(StreamingRadioFavorites.CACHE_KEY)
        )


if __name__ == "__main__":
    unittest.main()
