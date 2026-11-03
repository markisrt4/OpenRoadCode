# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Real local HTTP handoff, navigation encoding and Android sharing policy."""
import json
import math
from urllib.request import ProxyHandler, Request, build_opener
from unittest.mock import Mock, patch

from controllers.navigation.browser_position_source import BrowserPositionSource
from controllers.navigation.location_sharing_controller import LocationSharingController
from controllers.navigation.navigation_controller import NavigationController
from controllers.navigation.simulated_navigation_sensor import SimulatedNavigationSensor
from controllers.map_renderer.map_camera_runtime import MapCameraRuntime
from services.navigation.navigation_runtime import NavigationRuntime
from messaging.contracts.navigation.position_state_codec import encode_position_state, decode_position_state


def test_browser_fix_reaches_navigation_and_only_then_android_sharing():
    controller = NavigationController(SimulatedNavigationSensor('stationary'))
    controller.start()
    source = BrowserPositionSource(port=0)
    service = NavigationRuntime(controller, Mock(), source='test', host_location_source=source)
    provider = Mock()
    sharing = LocationSharingController(provider, status=Mock())
    with patch('controllers.map_renderer.map_camera_runtime.MapRendererClient'), \
            patch('controllers.map_renderer.map_camera_runtime.ZeroMqSubscriber'), \
            patch.object(MapCameraRuntime, '_load_cached_center', return_value=None):
        camera = MapCameraRuntime()
    camera.observe_location(sharing.update_snapshot)
    try:
        url = service._prepare_host_location()
        request = Request(url + 'position', data=json.dumps({
            'latitude': 42.5, 'longitude': -83.0, 'accuracy': 30}).encode(),
            headers={'Content-Type': 'application/json', 'Origin': url.rstrip('/')})
        with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
            assert response.status == 204
        state = controller.read_state().position
        assert state.source == 'browser'
        message = decode_position_state(encode_position_state(state))
        camera._on_position_message(message)
        sharing._tick()
        provider.send_location.assert_not_called()
        sharing.set_active(True)
        sharing._tick()
        point, accuracy = provider.send_location.call_args.args
        assert math.degrees(point.latitude_rad) == 42.5
        assert math.degrees(point.longitude_rad) == -83.0
        assert accuracy == 30
    finally:
        sharing.close()
        camera.close()
        service.close()
