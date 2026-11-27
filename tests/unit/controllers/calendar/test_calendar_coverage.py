# SPDX-License-Identifier: MIT
"""Verify empty snapshots and incomplete offline coverage."""

from datetime import date, datetime, timedelta, timezone

from controllers.calendar.calendar_coverage import covered_calendar_days
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.calendar_selection import (
    save_calendar_catalog,
    save_disabled_calendar_ids,
)


def test_coverage_requires_every_enabled_calendar(tmp_path):
    cache = CalendarEventCache(tmp_path / "events.sqlite3")
    selection = tmp_path / "selection.json"
    catalog = tmp_path / "catalog.json"
    start = datetime(2026, 11, 25, tzinfo=timezone.utc)
    end = start + timedelta(days=2)
    save_calendar_catalog(catalog, {"a": "Personal", "b": "Work"})

    def coverage():
        return covered_calendar_days(
            cache, "account", selection, catalog, timezone.utc, start.date(), 3
        )

    assert coverage() == frozenset()
    cache.replace_calendar_window("account", "a", start, end, [])
    assert coverage() == frozenset()
    cache.replace_calendar_window("account", "b", start, end, [])
    expected = frozenset({date(2026, 11, 25), date(2026, 11, 26)})
    assert coverage() == expected
    cache.replace_calendar_window("account", "b", start, start + timedelta(days=1), [])
    assert coverage() == frozenset({start.date()})
    save_disabled_calendar_ids(selection, {"b"})
    assert coverage() == expected
