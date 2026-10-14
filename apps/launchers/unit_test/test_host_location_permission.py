# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock, patch
from urllib.error import URLError

import pytest

from apps.launchers.host_location_permission import HostLocationPermission
from controllers.navigation.host_location_permission_if import HostLocationServiceUnavailable


def response():
    opener = Mock()
    opener.open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b'OpenRoadCode Host Location')))
    opener.open.return_value.__exit__ = Mock(return_value=False)
    return opener


def test_uses_the_default_browser_without_chromium_specific_flags():
    opener = response()
    with patch('apps.launchers.host_location_permission.build_opener', return_value=opener), \
         patch('apps.launchers.host_location_permission.shutil.which', return_value='/usr/bin/google-chrome'), \
         patch('apps.launchers.host_location_permission.subprocess.Popen') as launch:
        HostLocationPermission().open_permission_page(lambda: False)
    assert launch.call_args.args[0] == [
        '/usr/bin/google-chrome', '--new-window', 'http://127.0.0.1:8765/'
    ]
    assert 'QT_QPA_PLATFORM_PLUGIN_PATH' not in launch.call_args.kwargs['env']
    opener.open.assert_called_once_with('http://127.0.0.1:8765/', timeout=3)


def test_unavailable_service_does_not_launch_browser():
    opener = Mock()
    opener.open.side_effect = URLError('connection refused')
    with patch('apps.launchers.host_location_permission.build_opener', return_value=opener), \
         patch('apps.launchers.host_location_permission.subprocess.Popen') as launch:
        with pytest.raises(HostLocationServiceUnavailable):
            HostLocationPermission().open_permission_page(lambda: False)
    launch.assert_not_called()


def test_cancelled_service_check_does_not_open_browser():
    with patch('apps.launchers.host_location_permission.build_opener', return_value=response()), \
         patch('apps.launchers.host_location_permission.subprocess.Popen') as launch:
        HostLocationPermission().open_permission_page(Mock(side_effect=[False, True]))
    launch.assert_not_called()


def test_missing_default_browser_shows_the_manual_url():
    with patch('apps.launchers.host_location_permission.build_opener', return_value=response()), \
         patch('apps.launchers.host_location_permission.shutil.which', return_value=None):
        with pytest.raises(RuntimeError, match='http://127.0.0.1:8765/'):
            HostLocationPermission().open_permission_page(lambda: False)


def test_restart_uses_restricted_manager_endpoint_and_waits_for_location():
    manager = response()
    location = response()
    with patch(
        'apps.launchers.host_location_permission.build_opener',
        side_effect=[manager, location],
    ), patch('apps.launchers.host_location_permission.time.sleep'):
        HostLocationPermission().restart_location_service(lambda: False)

    request = manager.open.call_args.args[0]
    assert request.full_url.endswith('/services/openroadcode-navigation/restart')
    assert request.method == 'POST'
    location.open.assert_called_once_with('http://127.0.0.1:8765/', timeout=1)
