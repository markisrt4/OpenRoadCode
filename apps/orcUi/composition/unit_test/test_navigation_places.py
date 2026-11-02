# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Composition owns shared stores and fresh, independently closed search sessions."""
from unittest.mock import Mock, patch
import pytest
from apps.orcUi.composition.navigation_places import NavigationPlacesFactory


def test_panera_marker_reopens_after_real_session_close_and_factory_remount():
    from controllers.poi.poi_search_controller import PoiSearchController
    from protocols.map_renderer.map_poi_source import RawMapClick
    from ui.navigation import GeoPoint
    from ui.navigation.poi_models import PointOfInterest, PoiActionKind, PoiCategory

    position = GeoPoint(0.74, -1.45)
    pois = tuple(PointOfInterest(str(index), 'Other', PoiCategory.FOOD, position)
                 for index in range(4)) + (
        PointOfInterest('osm:node:11952787417', 'Panera Bread', PoiCategory.FOOD, position),)
    sources = []
    def build_search(**kwargs):
        source = Mock(spec=['poll_selected', 'poll_click', 'close', 'clear'])
        source.poll_selected.return_value = None
        source.poll_click.return_value = None
        sources.append(source)
        database = Mock()
        database.search.return_value = pois
        return PoiSearchController(source, search_source=database,
                                   position_provider=lambda: position, **kwargs)

    with patch('apps.orcUi.composition.navigation_places.PoiSearchController', side_effect=build_search):
        factory = NavigationPlacesFactory(favorites=Mock(), actions=Mock())
        first = factory.create()
        first.search(PoiCategory.FOOD)
        assert len(first.poll_search_result().pois) == 5
        first.close()  # Exact production wrapper that previously cleared the cache.
        sources[0].close.assert_called_once()
        second = factory.create()
        click = RawMapClick(position, 20, marker_id='osm:node:11952787417', marker_index=4)
        sources[1].poll_click.return_value = click
        selected = second.poll_selected()
        assert selected is not None
        assert selected.name == 'Panera Bread'
        assert any(action.kind is PoiActionKind.ORDER for action in selected.actions)
        assert first.poll_selected() is None
        second.clear()
        assert second.poll_selected() is None
        factory.close()
        assert len(sources) == 2
        for source in sources:
            source.close.assert_called_once()


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


def test_default_local_3d_action_uses_composition_injected_embedding():
    from ui.navigation import GeoPoint
    from ui.navigation.poi_models import PoiAction, PoiActionKind
    from types import SimpleNamespace
    embedded = Mock()
    factory = NavigationPlacesFactory(favorites=Mock(),search_factory=Mock,
                                      embedded_explore=embedded)
    try:
        session = factory.create()
        poi = SimpleNamespace(position=GeoPoint(.7,-1.4),name='Place')
        action = factory._owned_3d.action_for(poi)
        assert action.kind is PoiActionKind.EXPLORE_3D
        assert 'embedded' in factory._owned_3d.execute(poi,action)
        assert embedded.call_args.args[0].label == 'Place'
    finally:
        factory.close()
