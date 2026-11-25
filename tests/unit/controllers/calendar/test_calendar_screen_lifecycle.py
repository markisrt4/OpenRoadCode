# SPDX-License-Identifier: MIT
"""Headless regression coverage for calendar presentation lifecycle."""

from concurrent.futures import Future
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from frontends.tk.calendar.calendar_screen import CalendarScreen
from controllers.calendar.calendar_presentation import CalendarAgendaPresentation, read_agenda
from ui.calendar.calendar_models import AgendaSnapshot, CalendarHealthView


def test_worker_returns_agenda_without_tk():
    future = Future()
    controller = Mock()
    controller.load.return_value = ()
    day = date(2026, 11, 24)
    read_agenda(future, controller, day, 7, CalendarHealthView)
    assert future.result() == AgendaSnapshot((), CalendarHealthView())
    controller.load.assert_called_once_with(day, 7)


def test_cancelled_worker_does_not_read_cache():
    future = Future()
    future.cancel()
    controller = Mock()
    read_agenda(future, controller, date(2026, 11, 24), 7, CalendarHealthView)
    controller.load.assert_not_called()


def test_periodic_refresh_reschedules_until_closed():
    screen = Mock()
    screen._closed = False
    CalendarScreen._periodic_refresh(screen)
    screen._refresh.assert_called_once_with()
    screen.after.assert_called_once_with(30000, screen._periodic_refresh)
    screen._closed = True
    CalendarScreen._periodic_refresh(screen)
    assert screen._refresh_timer is None
    assert screen.after.call_count == 1


def test_stale_generation_is_discarded_and_reloaded():
    agenda = CalendarAgendaPresentation(Mock(), CalendarHealthView)
    with patch("controllers.calendar.calendar_presentation.Thread") as thread:
        agenda.request(date(2026, 11, 23), 7)
        agenda.request(date(2026, 11, 30), 7)
        assert thread.call_count == 1
        agenda._future.set_result(AgendaSnapshot((), CalendarHealthView()))
        assert agenda.poll() is None
        assert thread.call_count == 2
        assert thread.call_args.kwargs["args"][2] == date(2026, 11, 30)
        latest = AgendaSnapshot((), CalendarHealthView(status="ok"))
        agenda._future.set_result(latest)
        assert agenda.poll() == latest


def test_current_generation_renders_without_resetting_scroll():
    screen = Mock()
    screen._closed = False
    screen._day = date(2026, 11, 23)
    screen._month = False
    health = CalendarHealthView(status="ok")
    screen._agenda.poll.return_value = AgendaSnapshot((), health)
    CalendarScreen._collect(screen)
    assert screen._groups == ()
    screen._update_footer.assert_called_once_with(health)
    screen._render.assert_called_once_with(preserve_scroll=True)


def test_destroy_cancels_timers_and_pending_read_once():
    screen = Mock()
    screen._closed = False
    screen._refresh_timer = "refresh"
    screen._poll = "poll"
    CalendarScreen._close(screen, SimpleNamespace(widget=object()))
    assert not screen._closed
    CalendarScreen._close(screen, SimpleNamespace(widget=screen))
    CalendarScreen._close(screen, SimpleNamespace(widget=screen))
    assert screen._closed
    assert screen._poll is None
    assert screen._refresh_timer is None
    screen._agenda.close.assert_called_once_with()
    assert [call.args for call in screen.after_cancel.call_args_list] == [
        ("refresh",),
        ("poll",),
    ]
