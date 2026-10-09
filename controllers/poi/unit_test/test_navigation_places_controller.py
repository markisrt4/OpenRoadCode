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


def test_camera_feedback_is_normalized_and_shared_with_backend_observer():
    import math
    from protocols.map_renderer.map_poi_source import RawMapCamera
    search, observer = Mock(), Mock()
    search.poll_camera_state.return_value = RawMapCamera(42, -83, 18, 25, 40)
    controller = NavigationPlacesController(search, Mock(), Mock(), camera_observer=observer)
    camera = controller.poll_camera_state()
    assert camera.center == GeoPoint(math.radians(42), math.radians(-83))
    assert camera.pitch_rad == math.radians(40)
    observer.assert_called_once_with(camera.center, 18, math.radians(25), math.radians(40))
    controller.close()
    search.reset_mock()
    assert controller.poll_camera_state() is None
    search.poll_camera_state.assert_not_called()


def test_async_handoff_rejects_duplicate_and_discards_completion_after_close():
    from threading import Event
    started, release, finished = Event(), Event(), Event()
    actions = Mock()
    def launch(*args):
        started.set()
        assert release.wait(2)
        finished.set()
        return 'Opened'
    actions.execute.side_effect = launch
    controller = NavigationPlacesController(Mock(), Mock(), actions)
    poi = PointOfInterest('place', 'Place', PoiCategory.FOOD, GeoPoint(0, 0))
    action = PoiAction(PoiActionKind.ORDER, 'ORDER')
    assert controller.request_action(poi, action) == 1
    assert started.wait(2)
    assert controller.request_action(poi, action) is None
    controller.close()
    release.set()
    assert finished.wait(2)
    assert controller.poll_action_result() is None
    assert controller.request_action(poi, action) is None
    actions.execute.assert_called_once_with(poi, action)


def test_async_offline_handoff_does_not_call_platform():
    from threading import Event
    checked = Event()
    def offline():
        checked.set()
        return False
    actions = Mock()
    controller = NavigationPlacesController(Mock(), Mock(), actions, online_allowed=offline)
    poi = PointOfInterest('place', 'Place', PoiCategory.FOOD, GeoPoint(0, 0))
    action = PoiAction(PoiActionKind.OPEN_WEBSITE, 'WEBSITE', uri='https://example.com')
    assert controller.request_action(poi, action) == 1
    assert checked.wait(2)
    # Wait on the controller lock to let completion publication finish.
    import time
    result = None
    deadline = time.monotonic() + 2
    while result is None and time.monotonic() < deadline:
        result = controller.poll_action_result()
    assert result is not None and not result.success and 'Offline' in result.status
    actions.execute.assert_not_called()
    controller.close()


def test_selected_place_gets_one_earth_link_in_degrees_preserving_actions():
    import math
    controller, search, _, _ = session()
    website = PoiAction(PoiActionKind.OPEN_WEBSITE, 'Website', uri='https://example.com')
    poi = PointOfInterest('place', 'Place', PoiCategory.OTHER,
                          GeoPoint(math.radians(42), math.radians(-83)), actions=(website,))
    search.poll_selected.return_value = poi
    selected = controller.poll_selected()
    assert selected.actions[0] is website
    earth = selected.actions[-1]
    assert earth.label == 'Explore in Google Earth'
    assert earth.uri == 'https://earth.google.com/web/@42.0000000,-83.0000000,0a,1000d,35y,0h,45t,0r'
    search.poll_selected.return_value = selected
    assert len(controller.poll_selected().actions) == 2
    assert poi.actions == (website,)


def test_local_3d_action_is_selected_and_allowed_offline():
    selected = PointOfInterest('poi','Offline place',PoiCategory.OTHER,GeoPoint(.7,-1.4))
    search, executor = Mock(), Mock()
    search.poll_selected.return_value = selected
    action = PoiAction(PoiActionKind.EXPLORE_3D,'Offline 3D',provider_id='local-3d')
    controller = NavigationPlacesController(search,Mock(),executor,online_allowed=lambda:False,
                                            local_3d_action=lambda poi:action)
    assert action in controller.poll_selected().actions
    assert controller.execute(selected,action) is executor.execute.return_value
    with pytest.raises(ValueError,match='Offline mode'):
        controller.execute(selected,PoiAction(PoiActionKind.OPEN_WEBSITE,'Website'))
