# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
from unittest.mock import patch

from controllers.navigation.map_favorites import MapFavorite
from scripts import setup_navigation_favorites as setup
from ui.navigation import GeoPoint


class DummyGeocoder:
    pass


def test_keep_existing_returns_existing_position():
    existing = MapFavorite(
        "home",
        "Home",
        GeoPoint(math.radians(42.8), math.radians(-83.0)),
    )
    with patch("builtins.input", return_value="4"):
        position = setup._choose_position("Home", existing, DummyGeocoder())

    assert position == existing.position


def test_manual_position_can_be_selected():
    responses = iter(["3", "42.800000,-83.010000"])
    with patch("builtins.input", side_effect=lambda _prompt="": next(responses)):
        position = setup._choose_position("Home", None, DummyGeocoder())

    assert position is not None
    assert math.isclose(math.degrees(position.latitude_rad), 42.8)
    assert math.isclose(math.degrees(position.longitude_rad), -83.01)


def test_last_known_position_can_be_selected():
    expected = GeoPoint(math.radians(42.81), math.radians(-83.02))
    with (
        patch("builtins.input", return_value="2"),
        patch.object(setup, "_cached_position", return_value=expected),
    ):
        position = setup._choose_position("Home", None, DummyGeocoder())

    assert position == expected
