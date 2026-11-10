# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.saved_destinations import SavedDestinationsConfig
from controllers.cache import PersistentCache
from controllers.navigation.map_favorites import MapFavorites
from ui.navigation.destination_setup_request_handler_if import SavedDestination
from ui.navigation.map_ui_if import GeoPoint


class SavedDestinationFavoritesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.storage = PersistentCache(self.directory / "legacy", suffix=".json")
        self.config = SavedDestinationsConfig(self.directory / "destinations.toml")

    def test_toml_overlays_home_without_losing_legacy_work_or_other_favorites(self):
        legacy = MapFavorites(self.storage)
        legacy.set_home(GeoPoint(0.5, -1))
        legacy.set_work(GeoPoint(0.6, -1))
        coffee = legacy.add("Coffee", GeoPoint(0.7, -1))
        self.config.save(SavedDestination("home", "Home", "123 Main St", GeoPoint(0.8, -1.2)))
        favorites = MapFavorites(self.storage, destinations=self.config)
        self.assertEqual(favorites.home.position, GeoPoint(0.8, -1.2))
        self.assertEqual(favorites.home.address, "123 Main St")
        self.assertEqual(favorites.work, legacy.work)
        self.assertEqual(favorites.favorites, (coffee,))
        self.config.save(SavedDestination("home", "Home", "New address", GeoPoint(0.9, -1.3)))
        favorites.load()
        self.assertEqual(favorites.home.address, "New address")

    def test_invalid_toml_falls_back_to_legacy_without_modifying_it(self):
        legacy = MapFavorites(self.storage)
        legacy.set_home(GeoPoint(0.5, -1))
        self.config.path.write_text("version = 2")
        with self.assertLogs("controllers.navigation.map_favorites", level="WARNING"):
            favorites = MapFavorites(self.storage, destinations=self.config)
        self.assertEqual(favorites.home, legacy.home)
        self.assertEqual(self.config.path.read_text(), "version = 2")

    def test_default_favorites_use_user_config(self):
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(self.directory / "config"),
                                        "XDG_DATA_HOME": str(self.directory / "data")}):
            config = SavedDestinationsConfig()
            config.save(SavedDestination("work", "Work", "456 Main St", GeoPoint(0.6, -1.1)))
            favorites = MapFavorites()
            self.assertEqual(favorites.work.address, "456 Main St")
            favorites.set_home(GeoPoint(0.7, -1.2))
            self.assertEqual([item.key for item in config.load()], ["home", "work"])

    def test_failed_save_keeps_observed_home_unchanged(self):
        self.config.save(SavedDestination("home", "Home", "123 Main St", GeoPoint(0.7, -1)))
        favorites = MapFavorites(self.storage, destinations=self.config)
        before = favorites.home
        with patch.object(self.config, "save", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                favorites.set_home(GeoPoint(0.8, -1))
        self.assertEqual(favorites.home, before)
