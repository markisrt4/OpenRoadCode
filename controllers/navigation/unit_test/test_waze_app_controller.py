# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import Mock, patch
import math

import pytest

from controllers.navigation.waze_app_controller import WazeAppController
from ui.navigation import GeoPoint


def controller():
    launcher, view, fallback, status = Mock(), Mock(), Mock(), Mock()
    queued = []
    online = Mock(return_value=True)
    instance = WazeAppController(launcher, view, dispatch_ui=queued.append,
                                 online=online, fallback=fallback, status=status)
    return instance, launcher, view, fallback, status, queued, online


def run_worker(thread):
    options = thread.call_args.kwargs
    options['target'](*options['args'])


def test_native_launch_is_off_ui_thread_and_duplicate_requests_coalesce():
    instance, launcher, view, fallback, _, queued, _ = controller()
    launcher.launch_installed_app.return_value = 'Waze'
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        instance.request_open_waze()
        instance.request_open_waze()
        assert thread.call_count == 1
        launcher.launch_installed_app.assert_not_called()
        run_worker(thread)
    launcher.launch_installed_app.assert_called_once_with('com.waze')
    view.request_show_android_app.assert_not_called()
    queued.pop()()
    view.request_show_android_app.assert_called_once_with('Waze', 'com.waze')
    fallback.assert_not_called()


@pytest.mark.parametrize('failure', [None, RuntimeError('launch failed')])
def test_missing_or_failed_native_app_falls_back_on_ui_thread(failure):
    instance, launcher, view, fallback, _, queued, _ = controller()
    launcher.launch_installed_app.return_value = None
    launcher.launch_installed_app.side_effect = failure
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        instance.request_open_waze()
        run_worker(thread)
    fallback.assert_not_called()
    queued.pop()()
    fallback.assert_called_once_with()
    view.request_show_android_app.assert_not_called()


@pytest.mark.parametrize('action', ['close', 'cancel'])
def test_late_completion_cannot_reopen_after_close_or_offline_cancel(action):
    instance, launcher, view, fallback, status, queued, online = controller()
    launcher.launch_installed_app.return_value = 'Waze'
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        instance.request_open_waze()
        run_worker(thread)
        getattr(instance, action)()
        queued.pop()()
        if action == 'close':
            online.return_value = False
            instance.request_open_waze()
            assert status.call_count == 1
    view.request_show_android_app.assert_not_called()
    fallback.assert_not_called()


def test_offline_request_does_not_start_worker():
    instance, launcher, _, _, status, _, online = controller()
    online.return_value = False
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        instance.request_open_waze()
    thread.assert_not_called()
    launcher.launch_installed_app.assert_not_called()
    status.assert_called_once_with('Waze requires online mode')


def test_destination_uses_degrees_and_opens_the_same_embedded_panel():
    instance, launcher, view, fallback, _, queued, _ = controller()
    launcher.launch_installed_app.return_value = 'Waze'
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        instance.request_navigate_waze(GeoPoint(math.radians(42.5), math.radians(-83.25)))
        run_worker(thread)
    launcher.launch_installed_app.assert_called_once_with('com.waze',
        uri='waze://?ll=42.5000000,-83.2500000&navigate=yes')
    queued.pop()()
    view.request_show_android_app.assert_called_once_with('Waze', 'com.waze')
    fallback.assert_not_called()


@pytest.mark.parametrize('point', [GeoPoint(float('nan'), 0), GeoPoint(0, float('inf')), GeoPoint(2, 0)])
def test_invalid_destination_never_launches(point):
    instance, launcher, _, _, status, _, _ = controller()
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        instance.request_navigate_waze(point)
    thread.assert_not_called()
    launcher.launch_installed_app.assert_not_called()
    status.assert_called_once_with('Waze destination is invalid')


def test_failed_destination_does_not_silently_drop_destination_into_browser():
    instance, launcher, view, fallback, status, queued, _ = controller()
    launcher.launch_installed_app.return_value = None
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        instance.request_navigate_waze(GeoPoint(0, 0))
        run_worker(thread)
    queued.pop()()
    view.request_show_android_app.assert_not_called()
    fallback.assert_not_called()
    assert 'Could not send destination' in status.call_args.args[0]


@pytest.mark.parametrize('action', ['close', 'cancel'])
def test_destination_completion_is_ignored_after_cancel(action):
    instance, launcher, view, fallback, _, queued, _ = controller()
    launcher.launch_installed_app.return_value = 'Waze'
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        instance.request_navigate_waze(GeoPoint(0, 0))
        run_worker(thread)
        getattr(instance, action)()
        queued.pop()()
    view.request_show_android_app.assert_not_called()
    fallback.assert_not_called()
