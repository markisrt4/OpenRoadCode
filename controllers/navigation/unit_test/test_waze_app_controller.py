# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import Mock, patch

import pytest

from controllers.navigation.waze_app_controller import WazeAppController


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
