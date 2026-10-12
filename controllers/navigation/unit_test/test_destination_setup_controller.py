# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace
import math

from config.saved_destinations import SavedDestinationsConfig
from controllers.navigation.destination_setup_controller import DestinationSetupController
from controllers.navigation.geocoding_models import GeocodeResult
from ui.navigation.map_ui_if import GeoPoint


class DestinationSetupControllerTest(unittest.TestCase):
    def test_online_results_are_normalized_without_saving(self):
        provider = Mock()
        provider.geocode.return_value = (SimpleNamespace(
            address=" 123 Main Street ", latitude_deg=42.5, longitude_deg=-83,
        ),)
        controller = DestinationSetupController(self.config, online_geocoder=provider)
        results = controller.search_online("work", " 123 Main St ")
        self.assertEqual(results[0].address, "123 Main Street")
        self.assertAlmostEqual(results[0].position.latitude_rad, math.radians(42.5))
        self.assertFalse(self.config.path.exists())

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config = SavedDestinationsConfig(Path(directory.name) / "destinations.toml")

    def test_search_returns_immutable_candidates_without_saving(self):
        geocoder = Mock()
        geocoder.geocode.return_value = (
            GeocodeResult(" 123 Main Street ", GeoPoint(0.7, -1.4), 1, "address"),
        )
        controller = DestinationSetupController(self.config, geocoder)
        candidates = controller.search("home", "  123  Main St ")
        geocoder.geocode.assert_called_once_with("123 Main St")
        self.assertEqual(candidates[0].address, "123 Main Street")
        self.assertFalse(self.config.path.exists())
        controller.save(candidates[0])
        self.assertEqual(controller.current("home"), candidates[0])
        self.assertIsNone(controller.current("work"))

    def test_missing_geocoder_allows_manual_setup(self):
        controller = DestinationSetupController(self.config)
        self.assertEqual(controller.search("work", "123 Main St"), ())
        with self.assertRaises(ValueError):
            controller.search("home", " ")
        with self.assertRaises(ValueError):
            controller.current("unknown")

    def test_street_and_place_fallbacks_cannot_be_saved_as_address_matches(self):
        geocoder = Mock()
        geocoder.geocode.return_value = (
            GeocodeResult("Eleven Mile Road", GeoPoint(0.7, -1.4), 0.6, "street"),
            GeocodeResult("Roseville", GeoPoint(0.7, -1.4), 0.5, "place"),
        )
        controller = DestinationSetupController(self.config, geocoder)
        self.assertEqual(controller.search("work", "123 E 11 Mile Rd, Warren, MI"), ())
        self.assertFalse(self.config.path.exists())

    def test_incompatible_database_reports_recoverable_error(self):
        geocoder = Mock()
        geocoder.geocode.side_effect = sqlite3.OperationalError("no such table")
        controller = DestinationSetupController(self.config, geocoder)
        with self.assertRaisesRegex(RuntimeError, "enter coordinates"):
            controller.search("home", "123 Main St")
