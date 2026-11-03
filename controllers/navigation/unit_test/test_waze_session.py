# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Persistent navigation lifetime is separate from the visible screen."""
from unittest.mock import Mock, patch

from controllers.navigation.waze_app_controller import WazeAppController


def setup():
    launcher, view, sharing, closed, status = Mock(), Mock(), Mock(), Mock(), Mock()
    online = Mock(return_value=True)
    queue = []
    controller = WazeAppController(launcher, view, dispatch_ui=queue.append, online=online,
        fallback=Mock(), status=status, session_changed=sharing, session_closed=closed)
    launcher.launch_installed_app.return_value = 'Waze'
    return controller, launcher, view, sharing, closed, status, online, queue


def run(thread):
    thread.call_args.kwargs['target'](*thread.call_args.kwargs['args'])


def test_return_uses_existing_session_even_offline_without_resending_destination():
    controller, launcher, view, sharing, _, _, online, queue = setup()
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        controller.request_open_waze()
        run(thread)
        queue.pop()()
        assert controller.state.active
        online.return_value = False
        controller.cancel()
        controller.request_open_waze()
        run(thread)
        queue.pop()()
    launcher.launch_installed_app.assert_called_once_with('com.waze')
    launcher.resume_installed_app.assert_called_once_with('com.waze')
    launcher.stop_installed_app.assert_not_called()
    assert view.request_show_android_app.call_count == 2
    assert sharing.call_args.args[0].active


def test_explicit_close_stops_app_releases_surface_and_location_then_allows_fresh_launch():
    controller, launcher, view, sharing, closed, _, _, queue = setup()
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        controller.request_open_waze()
        run(thread)
        queue.pop()()
        controller.request_close_waze()
        assert controller.state.closing
        # Stop work is not performed by the UI callback.
        launcher.stop_installed_app.assert_not_called()
        run(thread)
        queue.pop()()
        assert not controller.state.active
        view.request_close_android_app.assert_called_once_with()
        launcher.stop_installed_app.assert_called_once_with('com.waze')
        assert not sharing.call_args.args[0].active
        closed.assert_called_once_with()
        controller.request_open_waze()
        run(thread)
        queue.pop()()
    assert launcher.launch_installed_app.call_count == 2


def test_failed_close_keeps_session_and_gps_available_for_retry():
    controller, launcher, view, sharing, closed, status, _, queue = setup()
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        controller.request_open_waze()
        run(thread)
        queue.pop()()
        launcher.stop_installed_app.side_effect = RuntimeError('ADB disconnected')
        controller.request_close_waze()
        run(thread)
        queue.pop()()
    assert controller.state.active and not controller.state.closing
    view.request_close_android_app.assert_not_called()
    assert sharing.call_args.args[0].active
    closed.assert_not_called()
    assert 'Could not close Waze' in status.call_args.args[0]


def test_explicit_close_invalidates_queued_launch_completion():
    controller, launcher, view, sharing, closed, _, _, queue = setup()
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        controller.request_open_waze()
        run(thread)
        late_launch = queue.pop()
        controller.request_close_waze()
        run(thread)
        queue.pop()()
        late_launch()
    view.request_show_android_app.assert_not_called()
    assert not controller.state.active
    assert not sharing.call_args.args[0].active


def test_shutdown_revokes_background_sharing_without_closing_unowned_android_session():
    controller, launcher, _, sharing, _, _, _, queue = setup()
    with patch('controllers.navigation.waze_app_controller.Thread') as thread:
        controller.request_open_waze()
        run(thread)
        queue.pop()()
    controller.close()
    assert not sharing.call_args.args[0].active
    launcher.stop_installed_app.assert_not_called()
