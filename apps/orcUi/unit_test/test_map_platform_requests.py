"""Renderer-neutral POI requests update native and optional secondary maps."""

from unittest.mock import Mock

from apps.orcUi.map_platform_requests import MapPlatformRequests
from ui.navigation import GeoPoint, MapMarker, MapMarkerKind, MapRequestHandlerIf


def test_poi_results_are_forwarded_as_complete_immutable_overlay():
    native = Mock(spec=MapRequestHandlerIf)
    native.camera_initialized = True
    secondary = Mock()
    requests = MapPlatformRequests(native, Mock(), secondary)
    marker = MapMarker("one", GeoPoint(0.7, -1.4), MapMarkerKind.SEARCH_RESULT, "Cafe")
    requests.request_poi_results((marker,), "food")

    native.request_poi_results.assert_called_once_with((marker,), "food")
    state = secondary.call_args.args[0]
    assert state.markers == (marker,) and state.category == "food"
    assert requests.camera_initialized


def test_clearing_focus_and_results_replaces_secondary_state():
    native, secondary = Mock(spec=MapRequestHandlerIf), Mock()
    requests = MapPlatformRequests(native, Mock(), secondary)
    requests.request_poi_focus("fuel")
    requests.request_poi_results((), "")
    requests.request_poi_focus(None)
    state = secondary.call_args.args[0]
    assert state.markers == () and state.category == '' and state.focused_category is None


def test_secondary_overlay_requests_preserve_native_camera_state_on_remount():
    from types import SimpleNamespace
    native = SimpleNamespace(camera_initialized=True, zoom_level=18.0, pitch_rad=.4, follow_enabled=False)
    requests = MapPlatformRequests(native, Mock())
    assert requests.camera_initialized
    assert requests.zoom_level == 18.0
    assert requests.pitch_rad == .4
    assert requests.follow_enabled is False
    native.zoom_level = 19.0
    assert requests.zoom_level == 19.0


def test_native_camera_refresh_reaches_original_handler_after_platform_wrapping():
    native, secondary = Mock(), Mock()
    requests = MapPlatformRequests(native, secondary)
    requests.refresh_renderer_state()
    native.refresh_renderer_state.assert_called_once_with()
    secondary.assert_not_called()


def test_native_zoom_and_pan_reach_original_handler():
    native, secondary = Mock(spec=MapRequestHandlerIf), Mock()
    requests = MapPlatformRequests(native, secondary)
    requests.request_zoom(5.5)
    requests.request_pan_screen(right_px=120, up_px=-60)
    native.request_zoom.assert_called_once_with(5.5)
    native.request_pan_screen.assert_called_once_with(120, -60)
