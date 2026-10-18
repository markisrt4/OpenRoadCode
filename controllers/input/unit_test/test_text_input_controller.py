# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Text sessions keep field ownership, focus and keyboard cleanup explicit."""
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, call

import pytest

from controllers.input.text_input_controller import TextInputController


def make_controller():
    keyboard = Mock(available=True)
    return TextInputController(keyboard), keyboard


def test_begin_show_hide_and_submit_preserve_the_active_target():
    controller, keyboard = make_controller()
    events = Mock()
    events.attach_mock(keyboard, 'keyboard')
    target = events.target
    view = Mock()
    controller.set_ui(view)
    session = controller.request_begin(target)
    assert session is not None
    controller.request_show_keyboard(session)
    assert events.mock_calls == [call.target.focus(), call.keyboard.show(), call.target.focus()]
    assert controller.state.keyboard_requested
    controller.request_hide_keyboard(session)
    assert controller.state.session_id == session
    assert not controller.state.keyboard_requested
    controller.request_submit(session)
    target.submit.assert_called_once()
    target.cancel.assert_not_called()
    assert controller.state.session_id is None
    assert view.set_text_input_state.call_args.args[0] == controller.state
    with pytest.raises(FrozenInstanceError):
        controller.state.error = 'mutated'


def test_rebinding_does_not_submit_cancel_or_accept_old_requests():
    controller, keyboard = make_controller()
    first, second = Mock(), Mock()
    old = controller.request_begin(first)
    controller.request_show_keyboard(old)
    new = controller.request_begin(second)
    assert new != old
    keyboard.hide.assert_called_once()
    first.submit.assert_not_called()
    first.cancel.assert_not_called()
    keyboard.reset_mock()
    for method in (controller.request_show_keyboard, controller.request_hide_keyboard,
                   controller.request_submit, controller.request_cancel):
        method(old)
    assert keyboard.mock_calls == []
    second.submit.assert_not_called()
    second.cancel.assert_not_called()
    assert controller.state.session_id == new


def test_unavailable_keyboard_still_allows_physical_keyboard_and_submit():
    controller, keyboard = make_controller()
    keyboard.available = False
    target = Mock()
    session = controller.request_begin(target)
    controller.request_show_keyboard(session)
    keyboard.show.assert_not_called()
    assert not controller.state.keyboard_available
    assert controller.state.error
    controller.request_submit(session)
    target.submit.assert_called_once()


def test_show_focus_failure_hides_the_keyboard_and_can_retry():
    controller, keyboard = make_controller()
    target = Mock()
    session = controller.request_begin(target)
    target.focus.side_effect = RuntimeError('gone')
    controller.request_show_keyboard(session)
    keyboard.hide.assert_called_once()
    assert not controller.state.keyboard_requested
    assert controller.state.error
    target.focus.side_effect = None
    controller.request_show_keyboard(session)
    assert controller.state.keyboard_requested
    assert controller.state.error is None


def test_replacement_hide_failure_preserves_previous_session():
    controller, keyboard = make_controller()
    old = controller.request_begin(Mock())
    controller.request_show_keyboard(old)
    keyboard.hide.side_effect = RuntimeError('busy')
    replacement = Mock()
    assert controller.request_begin(replacement) is None
    replacement.focus.assert_not_called()
    assert controller.state.session_id == old
    assert controller.state.keyboard_requested


@pytest.mark.parametrize('action', ['request_submit', 'request_cancel'])
def test_completion_callback_can_open_another_field_without_old_cleanup(action):
    controller, keyboard = make_controller()
    target, replacement = Mock(), Mock()
    old = controller.request_begin(target)
    def replace_target():
        session = controller.request_begin(replacement)
        controller.request_show_keyboard(session)
    getattr(target, 'submit' if action == 'request_submit' else 'cancel').side_effect = replace_target
    getattr(controller, action)(old)
    assert controller.state.session_id != old
    assert controller.state.keyboard_requested
    keyboard.hide.assert_not_called()


@pytest.mark.parametrize('action', ['request_submit', 'request_cancel'])
def test_failed_completion_keeps_session_for_retry(action):
    controller, keyboard = make_controller()
    target = Mock()
    getattr(target, 'submit' if action == 'request_submit' else 'cancel').side_effect = RuntimeError('failed')
    session = controller.request_begin(target)
    getattr(controller, action)(session)
    assert controller.state.session_id == session
    assert controller.state.error
    keyboard.hide.assert_not_called()


def test_cancel_releases_session_without_submitting():
    controller, keyboard = make_controller()
    target = Mock()
    session = controller.request_begin(target)
    controller.request_show_keyboard(session)
    controller.request_cancel(session)
    target.cancel.assert_called_once()
    target.submit.assert_not_called()
    keyboard.hide.assert_called_once()
    assert controller.state.session_id is None
    assert not controller.state.keyboard_requested


def test_begin_focus_failure_retires_old_token():
    controller, keyboard = make_controller()
    old = controller.request_begin(Mock())
    bad = Mock()
    bad.focus.side_effect = RuntimeError('widget destroyed')
    assert controller.request_begin(bad) is None
    controller.request_submit(old)
    assert controller.state.session_id is None
    assert controller.state.error


@pytest.mark.parametrize('failure', [False, True])
def test_close_releases_resources_once_without_calling_destroyed_fields(failure):
    controller, keyboard = make_controller()
    target, view = Mock(), Mock()
    controller.set_ui(view)
    session = controller.request_begin(target)
    controller.request_show_keyboard(session)
    if failure:
        keyboard.close.side_effect = RuntimeError('failed')
        with pytest.raises(RuntimeError, match='failed'):
            controller.close()
    else:
        controller.close()
    view.reset_mock()
    controller.close()
    for method in (controller.request_show_keyboard, controller.request_hide_keyboard,
                   controller.request_submit, controller.request_cancel):
        method(session)
    assert controller.request_begin(Mock()) is None
    keyboard.close.assert_called_once()
    assert controller.state.closed
    target.submit.assert_not_called()
    target.cancel.assert_not_called()
    view.set_text_input_state.assert_not_called()


def test_focus_rebinding_during_show_releases_old_keyboard_without_overwriting_new_state():
    controller, keyboard = make_controller()
    first, second = Mock(), Mock()
    old = controller.request_begin(first)
    first.focus.side_effect = lambda: controller.request_begin(second)
    controller.request_show_keyboard(old)
    keyboard.hide.assert_called_once()
    assert controller.state.session_id != old
    assert not controller.state.keyboard_requested
    controller.request_cancel(old)
    second.cancel.assert_not_called()


def test_failed_hide_after_submit_does_not_allow_duplicate_submit():
    controller, keyboard = make_controller()
    target = Mock()
    session = controller.request_begin(target)
    controller.request_show_keyboard(session)
    keyboard.hide.side_effect = RuntimeError('busy')
    controller.request_submit(session)
    controller.request_submit(session)
    target.submit.assert_called_once()
    assert controller.state.session_id is None
    assert controller.state.keyboard_requested
    assert controller.state.error
    keyboard.hide.side_effect = None
    replacement = controller.request_begin(Mock())
    assert replacement is not None
    assert not controller.state.keyboard_requested
