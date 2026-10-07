# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Composition owns shared stores and fresh, independently closed search sessions."""
from unittest.mock import Mock
import pytest
from apps.orcUi.composition.navigation_places import NavigationPlacesFactory


def test_factory_creates_fresh_sessions_and_closes_all_remaining_sources():
    searches = [Mock(), Mock()]
    factory = NavigationPlacesFactory(favorites=Mock(), actions=Mock(),
                                      search_factory=Mock(side_effect=searches))
    first, second = factory.create(), factory.create()
    assert first is not second
    first.close()
    searches[1].close.assert_not_called()
    factory.close()
    factory.close()
    for search in searches:
        search.close.assert_called_once_with()
    with pytest.raises(RuntimeError, match='closed'):
        factory.create()


def test_factory_continues_cleanup_if_one_source_fails():
    searches = [Mock(), Mock()]
    searches[0].close.side_effect = RuntimeError('source failed')
    factory = NavigationPlacesFactory(favorites=Mock(), actions=Mock(),
                                      search_factory=Mock(side_effect=searches))
    sessions = [factory.create(), factory.create()]
    with pytest.raises(RuntimeError, match='source failed'):
        factory.close()
    for search in searches:
        search.close.assert_called_once_with()
    assert all(session.poll_search_result() is None for session in sessions)


def test_remount_reloads_saved_places_updated_by_another_store(tmp_path):
    from controllers.cache import PersistentCache
    from controllers.navigation.map_favorites import MapFavorites
    from ui.navigation import GeoPoint
    storage = PersistentCache(tmp_path, suffix='.json')
    factory = NavigationPlacesFactory(favorites=MapFavorites(storage), actions=Mock(), search_factory=Mock)
    first = factory.create()
    assert first.favorite('home') is None
    edited = MapFavorites(storage)
    edited.set_home(GeoPoint(0.7, -1.4), 'Updated home')
    first.close()
    second = factory.create()
    assert second.favorite('home').name == 'Updated home'
    assert second.favorite('home').position == GeoPoint(0.7, -1.4)
    factory.close()
