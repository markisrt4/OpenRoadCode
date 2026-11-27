# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""CalDAV provider isolation and normalization tests."""

import unittest
from datetime import datetime, timedelta, timezone

from controllers.calendar.caldav_adapter import (
    CalDavCalendar,
    CalDavEventResource,
    CalDavTimeoutError,
)
from controllers.calendar.caldav_provider import CalDavCalendarProvider

START = datetime(2026, 11, 23, tzinfo=timezone.utc)
EVENT = (
    "BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:abc\n"
    "DTSTART:20261123T140000Z\nDTEND:20261123T150000Z\n"
    "SUMMARY:Meeting\nEND:VEVENT\nEND:VCALENDAR"
)
RECURRING = (
    "BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:weekly\n"
    "DTSTART:20261123T140000Z\nDTEND:20261123T150000Z\n"
    "RRULE:FREQ=WEEKLY\nEND:VEVENT\nEND:VCALENDAR"
)


class FakeAdapter:
    def discover_calendars(self):
        return [
            CalDavCalendar("http://localhost/one/", "One"),
            CalDavCalendar("http://localhost/two/", "Two"),
        ]

    def query_event_resources(self, calendar, start, end):
        if calendar.display_name == "Two":
            raise CalDavTimeoutError("Timed out")
        return [
            CalDavEventResource("http://localhost/one/a.ics", None, EVENT),
            CalDavEventResource("http://localhost/one/b.ics", None, RECURRING),
        ]


class CalDavProviderTests(unittest.TestCase):
    def test_recurring_and_standalone_results_survive_timeout(self):
        provider = CalDavCalendarProvider("proton", FakeAdapter())
        events = provider.list_events(START, START + timedelta(days=1))
        self.assertEqual([event.title for event in events], ["Meeting", ""])
        self.assertEqual(events[1].recurrence_id, "2026-11-23T14:00:00+00:00")
        self.assertEqual(len(provider.last_sync_status), 2)
        self.assertTrue(provider.last_sync_status[0].ok)
        self.assertEqual(provider.last_sync_status[0].skipped_resources, 0)
        self.assertFalse(provider.last_sync_status[1].ok)
        self.assertEqual(provider.last_sync_status[1].error, "CalDavTimeoutError")

    def test_invalid_window_is_rejected(self):
        provider = CalDavCalendarProvider("proton", FakeAdapter())
        with self.assertRaises(ValueError):
            provider.list_events(START, START)


if __name__ == "__main__":
    unittest.main()
