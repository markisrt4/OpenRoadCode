"""Renderer-neutral POI requests update native and optional secondary maps."""

from unittest.mock import Mock

from apps.orcUi.map_platform_requests import MapPlatformRequests
from ui.navigation import GeoPoint, MapMarker, MapMarkerKind, MapRequestHandlerIf


def test_poi_results_are_forwarded_as_complete_immutable_overlay():
    native = Mock(spec=MapRequestHandlerIf)
    native.camera_initialized = True
    secondary = Mock()
    requests = MapPlatformRequests(native, Mock(), secondary)
    marker = MapMarker('one', GeoPoint(.7,-1.4), MapMarkerKind.SEARCH_RESULT, 'Cafe')
    requests.request_poi_results((marker,), 'food')

    native.request_poi_results.assert_called_once_with((marker,), 'food')
    state = secondary.call_args.args[0]
    assert state.markers == (marker,) and state.category == 'food'
    assert requests.camera_initialized


def test_clearing_focus_and_results_replaces_secondary_state():
    native, secondary = Mock(spec=MapRequestHandlerIf), Mock()
    requests = MapPlatformRequests(native, Mock(), secondary)
    requests.request_poi_focus('fuel')
    requests.request_poi_results((), '')
    requests.request_poi_focus(None)
    state = secondary.call_args.args[0]
    assert state.markers == () and state.category == '' and state.focused_category is None
