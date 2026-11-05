from dataclasses import replace
from unittest.mock import Mock

from controllers.navigation.navigation_experience_controller import NavigationExperienceController
from ui.navigation.navigation_experience_if import NavigationExperience
from ui.navigation.navigation_view_if import NavigationViewState
from ui.navigation.map_platform_if import MapPlatform, MapPlatformState
from ui.navigation.waze_request_handler_if import WazeSessionState
from ui.navigation.poi_models import PoiCategory, TransitMode


def controller(selected='map', *, terrain=True, session=None, gestures=None):
    actions = {name: Mock() for name in ('open_map', 'open_waze', 'saved_map', 'saved_waze',
        'show_places', 'search_places', 'select_place', 'clear_places', 'close_waze', 'select_platform')}
    platform = Mock(state=MapPlatformState(available_platforms=(MapPlatform.MAPLIBRE, MapPlatform.CESIUM)
                                           if terrain else (MapPlatform.MAPLIBRE,)))
    view = NavigationExperienceController(platform=platform,
        navigation_state=lambda: NavigationViewState(selected),
        waze_state=lambda: session or WazeSessionState(active=True), waze_available=lambda: True, gestures=gestures, **actions)
    return view, actions, platform


def test_waze_resume_and_places_never_close_the_running_session():
    view, actions, _ = controller('waze')
    view.request_places()
    actions['open_map'].assert_called_once_with()
    actions['show_places'].assert_called_once_with()
    actions['close_waze'].assert_not_called()
    assert view.state.waze_running
    view.request_experience(NavigationExperience.WAZE)
    actions['open_waze'].assert_called_once_with()


def test_launching_waze_has_its_own_loading_state_not_just_generic_busy():
    view, _, _ = controller(session=WazeSessionState(launching=True))
    assert view.state.waze_loading and view.state.busy
    view, _, platform = controller()
    platform.state = replace(platform.state, busy=True)
    assert view.state.busy and not view.state.waze_loading


def test_gesture_requests_are_scoped_to_active_waze_not_the_orc_camera():
    from ui.navigation.waze_gesture_if import WazeGesture, WazeGestureState
    gestures = Mock(state=WazeGestureState(available=True))
    view, actions, platform = controller(gestures=gestures)
    view.request_waze_gesture(WazeGesture.ZOOM_IN)
    gestures.request_gesture.assert_not_called()
    view, actions, platform = controller('waze', gestures=gestures)
    view.request_waze_gesture(WazeGesture.ZOOM_IN)
    gestures.request_gesture.assert_called_once_with(WazeGesture.ZOOM_IN)
    platform.request_platform.assert_not_called()
    actions['open_waze'].assert_not_called()


def test_terrain_from_waze_opens_map_before_selecting_platform():
    view, actions, _ = controller('waze')
    order = Mock()
    order.attach_mock(actions['open_map'], 'map')
    order.attach_mock(actions['select_platform'], 'terrain')
    view.request_experience(NavigationExperience.TERRAIN)
    assert [call[0] for call in order.mock_calls] == ['map', 'terrain']
    actions['select_platform'].assert_called_once_with(MapPlatform.CESIUM)


def test_busy_and_unavailable_experiences_do_not_launch():
    view, actions, platform = controller(terrain=False)
    view.request_experience(NavigationExperience.TERRAIN)
    actions['select_platform'].assert_not_called()
    platform.state = replace(platform.state, busy=True)
    view.request_experience(NavigationExperience.WAZE)
    actions['open_waze'].assert_not_called()


def test_saved_destinations_use_active_experience_and_filters_are_preserved():
    view, actions, _ = controller('waze')
    view.request_saved_destination('home')
    actions['saved_waze'].assert_called_once_with('home')
    actions['saved_map'].assert_not_called()
    view.request_search_places(PoiCategory.TRANSIT, TransitMode.RAIL)
    actions['search_places'].assert_called_once_with(PoiCategory.TRANSIT, TransitMode.RAIL)
    view.request_saved_destination('invalid')
    assert actions['saved_waze'].call_count == 1


def test_road_selection_changes_terrain_without_reopening_map_or_stopping_waze():
    view, actions, platform = controller()
    platform.state = replace(platform.state, active=MapPlatform.CESIUM, requested=MapPlatform.CESIUM)
    assert view.state.selected is NavigationExperience.TERRAIN
    view.request_experience(NavigationExperience.ROAD)
    actions['select_platform'].assert_called_once_with(MapPlatform.MAPLIBRE)
    actions['open_map'].assert_not_called()
    actions['close_waze'].assert_not_called()
