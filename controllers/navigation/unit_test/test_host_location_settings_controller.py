# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

import pytest

from controllers.navigation.host_location_settings_controller import HostLocationSettingsController


def setup_controller(monkeypatch):
    jobs, callbacks = [], []
    monkeypatch.setattr('controllers.navigation.host_location_settings_controller.threading.Thread',
                        lambda **kwargs: Mock(start=lambda: jobs.append(kwargs['target'])))
    dispatcher, ui, permission = Mock(), Mock(), Mock()
    dispatcher.schedule_ui_callback.side_effect = lambda delay, callback: callbacks.append(callback)
    controller = HostLocationSettingsController(dispatcher, ui, permission)
    controller.show()
    return controller, ui, permission, jobs, callbacks


def test_share_request_opens_permission_page_once_and_never_claims_consent(monkeypatch):
    controller, ui, permission, jobs, callbacks = setup_controller(monkeypatch)
    controller.share_host_location()
    controller.share_host_location()
    assert len(jobs) == 1
    assert ui.set_host_location_state.call_args.args[0].busy
    jobs.pop()()
    permission.open_permission_page.assert_called_once()
    callbacks.pop()()
    state = ui.set_host_location_state.call_args.args[0]
    assert not state.busy
    assert 'Click Share host location' in state.status


def test_service_failure_is_visible_and_allows_retry(monkeypatch):
    controller, ui, permission, jobs, callbacks = setup_controller(monkeypatch)
    permission.open_permission_page.side_effect = RuntimeError('Location service unavailable')
    controller.share_host_location()
    jobs.pop()()
    callbacks.pop()()
    assert ui.set_host_location_state.call_args.args[0].status == 'Location service unavailable'
    controller.share_host_location()
    assert len(jobs) == 1


@pytest.mark.parametrize('lifecycle', ['hide', 'close'])
def test_late_worker_and_ui_callbacks_cannot_update_a_hidden_or_closed_screen(monkeypatch, lifecycle):
    controller, ui, permission, jobs, callbacks = setup_controller(monkeypatch)
    controller.share_host_location()
    jobs.pop()()
    getattr(controller, lifecycle)()
    ui.reset_mock()
    callbacks.pop()()
    ui.set_host_location_state.assert_not_called()
    assert permission.open_permission_page.call_args.args[0]()
    controller.share_host_location()
    assert not jobs


def test_hide_before_service_check_cancels_the_native_launch(monkeypatch):
    controller, ui, permission, jobs, callbacks = setup_controller(monkeypatch)
    permission.open_permission_page.side_effect = lambda cancelled: None if cancelled() else pytest.fail('not cancelled')
    controller.share_host_location()
    controller.hide()
    jobs.pop()()
    assert not callbacks
    controller.show()
    assert not ui.set_host_location_state.call_args.args[0].busy
