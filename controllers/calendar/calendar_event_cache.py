# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""SQLite-backed snapshots of normalized calendar events.

Snapshots are scoped to a queried time window. Failed calendar syncs never
replace a previously successful snapshot.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .calendar_models import CalendarEvent


class CalendarEventCache:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS calendar_snapshots (
                    account_id TEXT NOT NULL,
                    calendar_id TEXT NOT NULL,
                    window_start TEXT NOT NULL,
                    window_end TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    recurrence_id TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    ends_at TEXT NOT NULL,
                    all_day INTEGER NOT NULL,
                    location TEXT,
                    PRIMARY KEY (
                        account_id, calendar_id, window_start, window_end,
                        event_id, recurrence_id
                    )
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS calendar_snapshot_windows (
                    account_id TEXT NOT NULL,
                    calendar_id TEXT NOT NULL,
                    window_start TEXT NOT NULL,
                    window_end TEXT NOT NULL,
                    PRIMARY KEY (account_id, calendar_id, window_start, window_end)
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    @staticmethod
    def _window(start: datetime, end: datetime) -> tuple[str, str]:
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("Expected timezone-aware, increasing time range")
        return start.isoformat(), end.isoformat()

    def replace_calendar_window(
        self,
        account_id: str,
        calendar_id: str,
        start: datetime,
        end: datetime,
        events: list[CalendarEvent],
    ) -> None:
        """Atomically replace one successful calendar/window, including empty ones."""
        window_start, window_end = self._window(start, end)
        if not account_id or not calendar_id:
            raise ValueError("Account and calendar IDs are required")
        if any(
            event.account_id != account_id or event.calendar_id != calendar_id
            for event in events
        ):
            raise ValueError("Events must belong to the selected calendar")
        with self._connect() as connection:
            key = (account_id, calendar_id, window_start, window_end)
            connection.execute(
                """DELETE FROM calendar_snapshots WHERE account_id = ?
                   AND calendar_id = ? AND window_start = ? AND window_end = ?""",
                key,
            )
            connection.executemany(
                """INSERT INTO calendar_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        *key, event.event_id, event.recurrence_id or "",
                        event.title, event.starts_at.isoformat(),
                        event.ends_at.isoformat(), int(event.all_day), event.location,
                    )
                    for event in events
                ],
            )
            connection.execute(
                """INSERT OR IGNORE INTO calendar_snapshot_windows VALUES (?, ?, ?, ?)""",
                key,
            )

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """Read events from saved windows, deduplicating overlapping snapshots."""
        self._window(start, end)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT account_id, calendar_id, event_id, recurrence_id, title,
                          starts_at, ends_at, all_day, location
                   FROM calendar_snapshots"""
            ).fetchall()
        events: dict[tuple[str, str, str, str], CalendarEvent] = {}
        for row in rows:
            account_id, calendar_id, event_id, recurrence_id, title, begins, ends, all_day, location = row
            event = CalendarEvent(
                account_id=account_id,
                calendar_id=calendar_id,
                event_id=event_id,
                recurrence_id=recurrence_id or None,
                title=title,
                starts_at=datetime.fromisoformat(begins),
                ends_at=datetime.fromisoformat(ends),
                all_day=bool(all_day),
                location=location,
            )
            if event.starts_at < end and event.ends_at > start:
                events[(account_id, calendar_id, event_id, recurrence_id)] = event
        return sorted(
            events.values(),
            key=lambda event: (event.starts_at, event.ends_at, event.account_id,
                               event.calendar_id, event.event_id),
        )
