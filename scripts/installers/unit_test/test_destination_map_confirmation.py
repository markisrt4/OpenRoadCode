# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import json
import math
import unittest
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from frontends.common.destination_map_confirmation import validate_position
from scripts.installers.destination_map_runtime import confirm_on_map
from ui.navigation.destination_setup_request_handler_if import SavedDestination
from ui.navigation.map_ui_if import GeoPoint


class DestinationMapTest(unittest.TestCase):
    def confirm(self, destination, **kwargs):
        try:
            return confirm_on_map(destination, **kwargs)
        except PermissionError:
            self.skipTest("Loopback sockets are blocked by this test environment")

    def destination(self):
        return SavedDestination("work", "Work", "123 Main St", GeoPoint(0.7, -1.4))

    def test_adjusted_pin_returns_without_saving(self):
        def browser(url):
            with urlopen(url) as response:
                self.assertIn(b"OpenStreetMap", response.read())
            parts = urlsplit(url)
            request = Request(f"http://{parts.netloc}/confirm?{parts.query}",
                data=json.dumps({"lat": 42.5, "lon": -83}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request) as response:
                self.assertEqual(response.status, 200)
        result = self.confirm(self.destination(), open_url=browser, timeout=1)
        self.assertAlmostEqual(result.position.latitude_rad, math.radians(42.5))

    def test_cancel_returns_none(self):
        def browser(url):
            parts = urlsplit(url)
            request = Request(f"http://{parts.netloc}/confirm?{parts.query}",
                              data=b'{"cancel":true}', method="POST")
            with urlopen(request):
                pass
        self.assertIsNone(self.confirm(self.destination(), open_url=browser, timeout=1))

    def test_invalid_coordinates_are_rejected(self):
        for latitude in (91, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                validate_position({"lat": latitude, "lon": -83})
