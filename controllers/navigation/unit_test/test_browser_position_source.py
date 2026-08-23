# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the browser geolocation relay."""

import http.client
import json
import unittest

from apps.carUi.runtime.browser_position_source import BrowserPositionSource
from controllers.navigation import PositionState


class BrowserPositionSourceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = BrowserPositionSource(port=0)
        self.states: list[PositionState] = []
        self.source.start(self.states.append)

    def tearDown(self) -> None:
        self.source.stop()

    def test_serves_location_page(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.source.port)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read()
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertIn(b"navigator.geolocation.watchPosition", body)

    def test_accepts_and_normalizes_browser_position(self) -> None:
        payload = json.dumps(
            {
                "latitude": 42.3314,
                "longitude": -83.0458,
                "altitude": 190.0,
                "speed": 12.5,
                "heading": 270.0,
                "accuracy": 8.0,
            }
        )
        connection = http.client.HTTPConnection("127.0.0.1", self.source.port)
        connection.request(
            "POST",
            "/position",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response.read()
        connection.close()

        self.assertEqual(response.status, 204)
        self.assertEqual(len(self.states), 1)
        state = self.states[0]
        self.assertEqual(state.latitude_deg, 42.3314)
        self.assertEqual(state.longitude_deg, -83.0458)
        self.assertEqual(state.accuracy_m, 8.0)
        self.assertEqual(state.fix_mode, 3)
        self.assertEqual(state.source, "browser")

    def test_rejects_invalid_coordinates(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.source.port)
        connection.request(
            "POST",
            "/position",
            body=json.dumps({"latitude": 100, "longitude": 0}),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response.read()
        connection.close()

        self.assertEqual(response.status, 400)
        self.assertEqual(self.states, [])


if __name__ == "__main__":
    unittest.main()
