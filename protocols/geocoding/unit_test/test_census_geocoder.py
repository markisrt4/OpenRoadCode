# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import json
import unittest
from unittest.mock import Mock
from protocols.geocoding.census_geocoder import CensusGeocoder


class CensusGeocoderTest(unittest.TestCase):
    def provider(self, document):
        opener = Mock()
        opener.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=json.dumps(document).encode())))
        opener.return_value.__exit__ = Mock(return_value=False)
        return CensusGeocoder(opener=opener), opener

    def test_match_returns_address_and_bounded_coordinates(self):
        provider, opener = self.provider({"result": {"addressMatches": [
            {"matchedAddress": "123 MAIN ST, WARREN, MI", "coordinates": {"x": -83, "y": 42.5}}
        ]}})
        matches = provider.geocode("123 Main St, Warren, MI")
        self.assertEqual(matches[0].latitude_deg, 42.5)
        self.assertEqual(matches[0].longitude_deg, -83)
        self.assertIn("benchmark=Public_AR_Current", opener.call_args.args[0].full_url)
        self.assertEqual(opener.call_args.kwargs["timeout"], 8)

    def test_empty_and_invalid_responses(self):
        provider, _ = self.provider({"result": {"addressMatches": []}})
        self.assertEqual(provider.geocode("Unknown"), ())
        for document in ([], {"result": []}, {"result": {"addressMatches": "bad"}}):
            provider, _ = self.provider(document)
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                provider.geocode("Address")

    def test_network_error_is_recoverable(self):
        provider = CensusGeocoder(opener=Mock(side_effect=OSError("offline")))
        with self.assertRaisesRegex(RuntimeError, "internet"):
            provider.geocode("Address")
