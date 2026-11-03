# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import Mock
import pytest

from controllers.navigation.location_sharing_controller import LocationSharingController
from ui.navigation import GeoPoint
from ui.navigation.location_sharing_if import LocationSnapshot


def test_host_sharing_state_tracks_fresh_browser_fixes_and_expiry():
    changed = Mock()
    now = [100]
    controller = LocationSharingController(None, status=Mock(), clock=lambda: now[0], sharing_changed=changed)
    controller.update_snapshot(LocationSnapshot(GeoPoint(.7, -1.4), 99, source='browser'))
    controller._tick()
    controller._tick()
    changed.assert_called_once_with(True)
    now[0] = 120
    controller._tick()
    assert [call.args[0] for call in changed.call_args_list] == [True, False]


def test_retained_navigation_keeps_fresh_gps_when_the_panel_is_hidden_until_explicit_close():
    provider = Mock()
    controller = LocationSharingController(provider, status=Mock(), clock=lambda: 100)
    point = GeoPoint(.7, -1.4)
    controller.update_snapshot(LocationSnapshot(point, 99, 25, 'browser'))
    controller.set_navigation_active(True)
    controller.set_active(False)
    controller._tick()
    provider.send_location.assert_called_once_with(point, 25)
    provider.clear_location.assert_not_called()
    controller.set_navigation_active(False)
    controller._tick()
    provider.clear_location.assert_called_once_with()


def test_only_fresh_visible_location_is_forwarded_and_hide_removes_provider():
    provider, status = Mock(), Mock()
    controller = LocationSharingController(provider, status=status, clock=lambda: 100)
    point = GeoPoint(.7, -1.4)
    controller.update_snapshot(LocationSnapshot(point, 99, 25, 'browser'))
    controller._tick()
    provider.send_location.assert_not_called()
    controller.set_active(True)
    controller._tick()
    provider.send_location.assert_called_once_with(point, 25)
    assert status.call_args.args == ('Live location · Browser', 'Sharing live location with Android.')
    provider.clear_location.reset_mock()
    controller.set_active(False)
    controller._tick()
    provider.clear_location.assert_called_once()


@pytest.mark.parametrize('snapshot', [
    LocationSnapshot(GeoPoint(.7, -1.4), 99, source='gps', is_cached=True),
    LocationSnapshot(GeoPoint(.7, -1.4), 80, source='gps'),
    LocationSnapshot(GeoPoint(.7, -1.4), 120, source='gps'),
    LocationSnapshot(GeoPoint(.7, -1.4), 99, source='route-simulation'),
    LocationSnapshot(),
])
def test_cached_expired_future_simulated_and_missing_fixes_are_never_forwarded(snapshot):
    provider = Mock()
    controller = LocationSharingController(provider, status=Mock(), clock=lambda: 100)
    controller.set_active(True)
    controller.update_snapshot(snapshot)
    controller._tick()
    provider.send_location.assert_not_called()
    provider.clear_location.assert_called_once()


def test_repeated_old_bus_messages_cannot_keep_a_fix_alive():
    provider = Mock()
    now = [100]
    controller = LocationSharingController(provider, status=Mock(), clock=lambda: now[0])
    controller.set_active(True)
    snapshot = LocationSnapshot(GeoPoint(.7, -1.4), 99, source='android-gps')
    controller.update_snapshot(snapshot)
    controller._tick()
    now[0] = 111
    controller.update_snapshot(snapshot)
    controller._tick()
    assert provider.send_location.call_count == 1
    provider.clear_location.assert_called_once()


def test_hide_racing_delivery_clears_the_late_write():
    provider = Mock()
    controller = LocationSharingController(provider, status=Mock(), clock=lambda: 100)
    controller.update_snapshot(LocationSnapshot(GeoPoint(.7, -1.4), 99))
    controller.set_active(True)
    provider.send_location.side_effect = lambda *args: controller.set_active(False)
    controller._tick()
    provider.clear_location.assert_called_once()


def test_shutdown_releases_provider_on_its_worker():
    provider = Mock()
    controller = LocationSharingController(provider, status=Mock())
    controller.close()
    controller.start()
    controller._thread.join(timeout=2)
    assert not controller._thread.is_alive()
    provider.clear_location.assert_called_once()
