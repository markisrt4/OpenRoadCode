# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Places sessions obey semantic requests and reject late results after close."""
from unittest.mock import Mock
import pytest

from controllers.poi.navigation_places_controller import NavigationPlacesController
from ui.navigation.navigation_places_request_handler_if import MapFavorite, NavigationPlacesRequestHandlerIf
from ui.navigation.poi_models import PoiAction, PoiActionKind, PoiCategory, TransitMode, PointOfInterest
from ui.navigation import GeoPoint


def session():
    search, favorites, actions = Mock(), Mock(), Mock()
    controller = NavigationPlacesController(search, favorites, actions)
    return controller, search, favorites, actions


def test_contract_search_and_favorites_preserve_semantics():
    controller, search, favorites, _ = session()
    assert isinstance(controller, NavigationPlacesRequestHandlerIf)
    favorites.home = MapFavorite('home', 'Home', GeoPoint(0.5, -1.0))
    assert controller.favorite('home') is favorites.home
    assert controller.favorite('work') is favorites.work
    controller.search(PoiCategory.TRANSIT, TransitMode.BUS)
    search.search.assert_called_once_with(PoiCategory.TRANSIT, TransitMode.BUS)
    assert controller.poll_search_result() is search.poll_search_result.return_value
    assert controller.poll_selected() is search.poll_selected.return_value
    assert controller.poll_camera_interaction() is search.poll_camera_interaction.return_value
    with pytest.raises(ValueError, match='Unknown'):
        controller.favorite('unexpected')


def test_closed_session_does_not_emit_late_results_or_requests():
    controller, search, _, _ = session()
    controller.close()
    controller.close()
    search.clear.assert_called_once_with()
    search.close.assert_called_once_with()
    search.reset_mock()
    controller.search(PoiCategory.FOOD)
    controller.clear()
    assert controller.poll_search_result() is None
    assert controller.poll_selected() is None
    assert controller.poll_camera_interaction() is False
    assert controller.favorite('home') is None
    assert search.mock_calls == []


def test_close_releases_source_even_if_clear_fails():
    controller, search, _, _ = session()
    search.clear.side_effect = RuntimeError('failed to clear')
    with pytest.raises(RuntimeError, match='failed to clear'):
        controller.close()
    search.close.assert_called_once_with()
    assert controller.poll_selected() is None


def test_actions_return_status_and_wrap_platform_errors():
    controller, _, _, actions = session()
    poi = PointOfInterest('place', 'Place', PoiCategory.FOOD, GeoPoint(0.5, -1.0))
    action = PoiAction(PoiActionKind.OPEN_WEBSITE, 'Website', uri='https://example.com')
    actions.execute.return_value = 'Opening website'
    assert controller.execute(poi, action) == 'Opening website'
    actions.execute.assert_called_once_with(poi, action)
    actions.execute.side_effect = OSError('platform failed')
    with pytest.raises(RuntimeError, match='platform failed') as error:
        controller.execute(poi, action)
    assert isinstance(error.value.__cause__, OSError)
    controller.close()
    actions.reset_mock()
    with pytest.raises(RuntimeError, match='closed'):
        controller.execute(poi, action)
    actions.execute.assert_not_called()
