# SPDX-License-Identifier: MIT
"""Agenda grouping regression tests."""

from datetime import date, datetime, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from controllers.calendar.calendar_agenda import CalendarAgendaController
from controllers.calendar.calendar_models import CalendarEvent
from controllers.calendar.calendar_provider_if import CalendarProviderIf


def test_agenda_groups_all_day_and_overnight_events():
    provider = Mock(spec=CalendarProviderIf)
    all_day = CalendarEvent(
        "account",
        "calendar",
        "holiday",
        "Holiday",
        datetime(2026, 11, 24, tzinfo=timezone.utc),
        datetime(2026, 11, 25, tzinfo=timezone.utc),
        all_day=True,
    )
    overnight = CalendarEvent(
        "account",
        "calendar",
        "overnight",
        "Overnight",
        datetime(2026, 11, 25, 4, tzinfo=timezone.utc),
        datetime(2026, 11, 25, 7, tzinfo=timezone.utc),
    )
    provider.list_events.return_value = [overnight, all_day]
    controller = CalendarAgendaController(provider, ZoneInfo("America/Detroit"))
    groups = controller.load(date(2026, 11, 24), 2)
    assert groups[0].events == (all_day, overnight)
    assert groups[1].events == (overnight,)


@pytest.mark.parametrize("days", [0, 32])
def test_invalid_window(days):
    provider = Mock(spec=CalendarProviderIf)
    controller = CalendarAgendaController(provider, timezone.utc)
    with pytest.raises(ValueError):
        controller.load(date(2026, 11, 24), days)
    provider.list_events.assert_not_called()
