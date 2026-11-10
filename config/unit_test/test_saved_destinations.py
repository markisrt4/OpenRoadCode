# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.saved_destinations import SavedDestinationsConfig
from ui.navigation.destination_setup_request_handler_if import SavedDestination
from ui.navigation.map_ui_if import GeoPoint


def destination(key="home", *, latitude=0.7, longitude=-1.4):
    return SavedDestination(key, key.title(), '  123 "Main" St\n Testville  ',
                            GeoPoint(latitude, longitude))


class SavedDestinationsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.config = SavedDestinationsConfig(self.directory / "destinations.toml")

    def test_toml_roundtrip_normalizes_and_preserves_other_destination(self):
        self.config.save(destination())
        self.config.save(destination("work"))
        self.config.save(SavedDestination("home", "  New Home  ", "Another address", GeoPoint(0.8, -1.2)))
        home, work = self.config.load()
        self.assertEqual(home.label, "New Home")
        self.assertEqual(home.position, GeoPoint(0.8, -1.2))
        self.assertEqual(work.address, '123 "Main" St Testville')
        self.assertEqual(work.position, GeoPoint(0.7, -1.4))
        self.assertEqual(self.config.path.stat().st_mode & 0o777, 0o600)
        self.assertIn('latitude_rad = 0.8', self.config.path.read_text())

    def test_invalid_coordinates_preserve_existing_bytes(self):
        self.config.save(destination())
        before = self.config.path.read_bytes()
        for latitude, longitude in [(math.nan, 0), (0, math.inf), (math.pi, 0),
                                    (0, 4), (True, 0), (10**1000, 0), ("0.7", 0)]:
            with self.subTest(latitude=latitude, longitude=longitude):
                with self.assertRaises(ValueError):
                    self.config.save(destination(latitude=latitude, longitude=longitude))
                self.assertEqual(self.config.path.read_bytes(), before)

    def test_unicode_and_control_characters_roundtrip_as_valid_toml(self):
        item = SavedDestination("home", "Home", "Café 🏠\x7f", GeoPoint(0.7, -1.4))
        self.config.save(item)
        self.assertEqual(self.config.load(), (item,))

    def test_malformed_config_is_never_overwritten(self):
        for invalid in ['version = 2', 'version = true', 'broken = [',
                'version = 1\n[home]\nlabel = "Home"\naddress = "A"\nlatitude_rad = "0.5"\nlongitude_rad = 0.5']:
            with self.subTest(invalid=invalid):
                self.config.path.write_text(invalid)
                with self.assertRaises(ValueError):
                    self.config.save(destination())
                self.assertEqual(self.config.path.read_text(), invalid)

    def test_failed_replace_preserves_file_and_cleans_temporary(self):
        self.config.save(destination())
        before = self.config.path.read_bytes()
        with patch("config.saved_destinations.os.replace", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                self.config.save(destination("work"))
        self.assertEqual(self.config.path.read_bytes(), before)
        self.assertEqual(list(self.directory.iterdir()), [self.config.path])

    def test_default_path_respects_xdg_config_home_without_side_effects(self):
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(self.directory)}):
            config = SavedDestinationsConfig()
            self.assertEqual(config.path, self.directory / "openroadcode/destinations.toml")
            self.assertEqual(config.load(), ())
            self.assertFalse(config.path.exists())
