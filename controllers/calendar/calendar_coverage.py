# SPDX-License-Identifier: MIT
"""Determine which local dates have complete selected-calendar coverage."""

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path

from .calendar_event_cache import CalendarEventCache
from .calendar_selection import load_calendar_catalog, load_disabled_calendar_ids


def covered_calendar_days(
    cache: CalendarEventCache,
    account_id: str,
    selection: Path,
    catalog: Path,
    zone: tzinfo,
    first_day: date,
    days: int,
) -> frozenset[date]:
    """Return dates fully covered by every known enabled calendar.

    @param cache Local event cache.
    @param account_id Selected account.
    @param selection Calendar selection file.
    @param catalog Discovered calendar catalog.
    @param zone Display timezone.
    @param first_day First requested local date.
    @param days Number of requested dates.
    @return Fully covered dates, conservatively empty for unknown catalogs.
    """
    enabled = set(load_calendar_catalog(catalog)) - load_disabled_calendar_ids(selection)
    windows = cache.snapshot_windows(account_id)
    if not enabled or not enabled.issubset(windows):
        return frozenset()
    covered = set()
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        following = day + timedelta(days=1)
        start = min(
            datetime.combine(day, time.min, zone),
            datetime.combine(day, time.min, timezone.utc),
        )
        end = max(
            datetime.combine(following, time.min, zone),
            datetime.combine(following, time.min, timezone.utc),
        )
        if all(windows[key][0] <= start and windows[key][1] >= end for key in enabled):
            covered.add(day)
    return frozenset(covered)
