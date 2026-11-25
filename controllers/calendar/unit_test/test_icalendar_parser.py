# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Test normalization of standalone CalDAV iCalendar events."""

import unittest
from datetime import datetime, timezone

from controllers.calendar.icalendar_parser import (
    UnsupportedCalendarEventError,
    parse_icalendar_events,
)


class ICalendarParserTests(unittest.TestCase):
    def test_utc_event_and_escaped_summary(self) -> None:
        raw = (
            "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:abc\r\n"
            "DTSTART:20261123T140000Z\r\nDTEND:20261123T150000Z\r\n"
            "SUMMARY:Lunch\\, team\r\nLOCATION:Office\r\nEND:VEVENT\r\nEND:VCALENDAR"
        )
        events = parse_icalendar_events(raw, "proton", "personal")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Lunch, team")
        self.assertEqual(events[0].location, "Office")
        self.assertEqual(events[0].starts_at, datetime(2026, 11, 23, 14, tzinfo=timezone.utc))

    def test_all_day_exclusive_end(self) -> None:
        raw = (
            "BEGIN:VEVENT\nUID:day\nDTSTART;VALUE=DATE:20261123\n"
            "DTEND;VALUE=DATE:20261125\nSUMMARY:Trip\nEND:VEVENT"
        )
        event = parse_icalendar_events(raw, "proton", "personal")[0]
        self.assertTrue(event.all_day)
        self.assertEqual(event.ends_at.day, 25)

    def test_timezone_aware_event(self) -> None:
        raw = (
            "BEGIN:VEVENT\nUID:local\n"
            "DTSTART;TZID=America/Detroit:20261123T090000\n"
            "DTEND;TZID=America/Detroit:20261123T100000\nEND:VEVENT"
        )
        event = parse_icalendar_events(raw, "proton", "personal")[0]
        self.assertEqual(event.starts_at.utcoffset().total_seconds(), -18000)

    def test_recurrence_master_rejected_not_silently_misrepresented(self) -> None:
        raw = (
            "BEGIN:VEVENT\nUID:weekly\nDTSTART:20261123T140000Z\n"
            "DTEND:20261123T150000Z\nRRULE:FREQ=WEEKLY\nEND:VEVENT"
        )
        with self.assertRaises(UnsupportedCalendarEventError):
            parse_icalendar_events(raw, "proton", "personal")

    def test_cancelled_event_skipped(self) -> None:
        raw = (
            "BEGIN:VEVENT\nUID:gone\nSTATUS:CANCELLED\n"
            "DTSTART:20261123T140000Z\nDTEND:20261123T150000Z\nEND:VEVENT"
        )
        self.assertEqual(parse_icalendar_events(raw, "proton", "personal"), [])


if __name__ == "__main__":
    unittest.main()
