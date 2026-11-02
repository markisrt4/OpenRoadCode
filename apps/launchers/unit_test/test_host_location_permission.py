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
        with pytest.raises(RuntimeError, match="Location sharing couldn't connect"):
            HostLocationPermission().open_permission_page(lambda: False)
    launch.assert_not_called()


def test_cancelled_service_check_does_not_open_browser():
    with patch('apps.launchers.host_location_permission.build_opener', return_value=response()), \
         patch('apps.launchers.host_location_permission.webbrowser.open') as launch:
        HostLocationPermission().open_permission_page(Mock(side_effect=[False, True]))
    launch.assert_not_called()


def test_missing_default_browser_has_a_user_action():
    with patch('apps.launchers.host_location_permission.build_opener', return_value=response()), \
         patch('apps.launchers.host_location_permission.webbrowser.open', return_value=False):
        with pytest.raises(RuntimeError, match='Set a default browser'):
            HostLocationPermission().open_permission_page(lambda: False)


def test_unavailable_service_recovers_before_opening_browser():
    opener = response()
    available = opener.open.return_value
    opener.open.side_effect = [URLError('refused'), available]
    recover = Mock()
    with patch('apps.launchers.host_location_permission.build_opener', return_value=opener), \
         patch('apps.launchers.host_location_permission.webbrowser.open', return_value=True) as launch:
        HostLocationPermission(recover=recover).open_permission_page(lambda: False)
    recover.assert_called_once()
    launch.assert_called_once()


def test_recovery_failure_does_not_expose_supervisor_errors():
    opener = Mock()
    opener.open.side_effect = URLError('refused')
    recover = Mock(side_effect=RuntimeError('sudo: password required'))
    with patch('apps.launchers.host_location_permission.build_opener', return_value=opener), \
         patch('apps.launchers.host_location_permission.webbrowser.open') as launch:
        with pytest.raises(RuntimeError, match='Ask your ORC installer') as error:
            HostLocationPermission(recover=recover).open_permission_page(lambda: False)
    assert 'sudo' not in str(error.value)
    launch.assert_not_called()


def test_cancel_during_recovery_does_not_open_permission_browser():
    opener = Mock()
    opener.open.side_effect = URLError('refused')
    cancelled = Mock(side_effect=[False, False, True, True])
    with patch('apps.launchers.host_location_permission.build_opener', return_value=opener), \
         patch('apps.launchers.host_location_permission.webbrowser.open') as launch:
        HostLocationPermission(recover=Mock()).open_permission_page(cancelled)
    launch.assert_not_called()


def test_ready_service_does_not_start_or_restart_navigation():
    recover = Mock()
    with patch('apps.launchers.host_location_permission.build_opener', return_value=response()), \
         patch('apps.launchers.host_location_permission.webbrowser.open', return_value=True):
        HostLocationPermission(recover=recover).open_permission_page(lambda: False)
    recover.assert_not_called()
