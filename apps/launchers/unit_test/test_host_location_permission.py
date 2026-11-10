# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock, patch
from urllib.error import URLError

import pytest

from apps.launchers.host_location_permission import HostLocationPermission


def response():
    opener = Mock()
    opener.open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b'OpenRoadCode Host Location')))
    opener.open.return_value.__exit__ = Mock(return_value=False)
    return opener


def test_uses_the_default_browser_without_chromium_specific_flags():
    opener = response()
    with patch('apps.launchers.host_location_permission.build_opener', return_value=opener), \
         patch('apps.launchers.host_location_permission.webbrowser.open', return_value=True) as launch:
        HostLocationPermission().open_permission_page(lambda: False)
    launch.assert_called_once_with('http://127.0.0.1:8765/', new=2)
    opener.open.assert_called_once_with('http://127.0.0.1:8765/', timeout=3)


def test_unavailable_service_does_not_launch_browser():
    opener = Mock()
    opener.open.side_effect = URLError('connection refused')
    with patch('apps.launchers.host_location_permission.build_opener', return_value=opener), \
         patch('apps.launchers.host_location_permission.webbrowser.open') as launch:
        with pytest.raises(RuntimeError, match='Restart the navigation service'):
            HostLocationPermission().open_permission_page(lambda: False)
    launch.assert_not_called()


def test_cancelled_service_check_does_not_open_browser():
    with patch('apps.launchers.host_location_permission.build_opener', return_value=response()), \
         patch('apps.launchers.host_location_permission.webbrowser.open') as launch:
        HostLocationPermission().open_permission_page(Mock(side_effect=[False, True]))
    launch.assert_not_called()


def test_missing_default_browser_shows_the_manual_url():
    with patch('apps.launchers.host_location_permission.build_opener', return_value=response()), \
         patch('apps.launchers.host_location_permission.webbrowser.open', return_value=False):
        with pytest.raises(RuntimeError, match='http://127.0.0.1:8765/'):
            HostLocationPermission().open_permission_page(lambda: False)
