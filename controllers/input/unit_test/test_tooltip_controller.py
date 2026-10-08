# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tooltip contract lifecycle tests with deliberately delivered stale timers."""

from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from controllers.input.tooltip_controller import TooltipController
from ui.tooltip_if import TooltipState, TooltipUiIf


def _session():
    view = Mock(spec=TooltipUiIf)
    dispatcher = Mock()
    dispatcher.schedule_ui_callback.side_effect = lambda _delay, callback: callback
    return TooltipController(view, dispatcher), view, dispatcher


def test_delayed_show_and_replacement_reject_obsolete_completion():
    controller, view, dispatcher = _session()
    controller.request_show("Zoom in")
    dispatcher.schedule_ui_callback.assert_called_once()
    assert dispatcher.schedule_ui_callback.call_args.args[0] == 500
    first = dispatcher.schedule_ui_callback.call_args.args[1]
    assert view.set_tooltip_state.call_args.args[0] == TooltipState()
    controller.request_show("Zoom out")
    latest = dispatcher.schedule_ui_callback.call_args.args[1]
    dispatcher.cancel_ui_callback.assert_called_once_with(first)
    view.reset_mock()
    first()
    view.set_tooltip_state.assert_not_called()
    latest()
    view.set_tooltip_state.assert_called_once_with(TooltipState("Zoom out", True))


@pytest.mark.parametrize("action", ["request_hide", "close"])
def test_dismissal_invalidates_timers_even_if_cancellation_loses_a_race(action):
    controller, view, dispatcher = _session()
    controller.request_show("Follow vehicle")
    late = dispatcher.schedule_ui_callback.call_args.args[1]
    getattr(controller, action)()
    view.reset_mock()
    late()
    view.set_tooltip_state.assert_not_called()
    if action == "close":
        controller.close()
        controller.request_show("Recenter")
        controller.request_hide()
        view.set_tooltip_state.assert_not_called()


def test_visible_tip_hides_and_blank_descriptions_do_not_schedule():
    controller, view, dispatcher = _session()
    controller.request_show("North up")
    dispatcher.schedule_ui_callback.call_args.args[1]()
    controller.request_hide()
    assert view.set_tooltip_state.call_args.args[0] == TooltipState()
    dispatcher.reset_mock()
    controller.request_show(" ")
    dispatcher.schedule_ui_callback.assert_not_called()


def test_tooltip_contracts_reject_unrelated_views_and_state_is_immutable():
    with pytest.raises(TypeError, match="TooltipUiIf"):
        TooltipController(object(), Mock())
    with pytest.raises(ValueError, match="nonnegative"):
        TooltipController(Mock(spec=TooltipUiIf), Mock(), delay_ms=-1)
    with pytest.raises(FrozenInstanceError):
        TooltipState().visible = True
