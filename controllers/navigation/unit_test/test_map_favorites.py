# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math

from controllers.cache import PersistentCache
from controllers.navigation.map_favorites import MapFavorites
from ui.navigation import GeoPoint


def test_shortcuts_refresh_when_navigation_changes_saved_destinations(tmp_path):
    storage = PersistentCache(tmp_path, suffix='.json')
    navigation, waze = MapFavorites(storage), MapFavorites(storage)
    first, second = GeoPoint(.7, -1.4), GeoPoint(.8, -1.5)
    assert waze.shortcut_position('work') is None
    navigation.set_home(first)
    assert waze.shortcut_position('home') == first
    navigation.set_home(second)
    refreshed = waze.shortcut_position('home')
    assert math.isclose(refreshed.latitude_rad, second.latitude_rad)
    assert math.isclose(refreshed.longitude_rad, second.longitude_rad)
    assert waze.shortcut_position('unknown') is None


def test_home_and_work_survive_across_instances(tmp_path):
    storage = PersistentCache(tmp_path, suffix=".json")
    first = MapFavorites(storage)
    first.set_home(GeoPoint(math.radians(42.8), math.radians(-83.0)))
    first.set_work(GeoPoint(math.radians(42.3), math.radians(-83.1)))

    second = MapFavorites(storage)

    assert second.home is not None
    assert second.work is not None
    assert math.isclose(math.degrees(second.home.position.latitude_rad), 42.8)
    assert math.isclose(math.degrees(second.work.position.longitude_rad), -83.1)


def test_arbitrary_favorite_can_be_added_and_removed(tmp_path):
    storage = PersistentCache(tmp_path, suffix=".json")
    favorites = MapFavorites(storage)
    favorite = favorites.add(
        "Coffee",
        GeoPoint(math.radians(42.81), math.radians(-83.02)),
    )

    assert [item.name for item in favorites.favorites] == ["Coffee"]
    assert favorites.remove(favorite.favorite_id)
    assert favorites.favorites == ()
