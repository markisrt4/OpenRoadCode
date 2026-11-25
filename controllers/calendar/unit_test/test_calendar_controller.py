# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Calendar controller contract tests using two independent providers."""

import unittest
from datetime import datetime, timedelta, timezone

from controllers.calendar import (
    CalendarCapabilities,
    CalendarController,
    CalendarEvent,
    CalendarProviderIf,
)

UTC = timezone.utc
START = datetime(2026, 11, 23, tzinfo=UTC)


class FakeProvider(CalendarProviderIf):
    def __init__(self, events: list[CalendarEvent], readable: bool = True) -> None:
        self.events = events
        self.readable = readable

    @property
    def capabilities(self) -> CalendarCapabilities:
        return CalendarCapabilities(can_read=self.readable)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return list(self.events)


def event(account: str, name: str, offset: int, duration: int = 60) -> CalendarEvent:
    return CalendarEvent(
        account_id=account,
        calendar_id="primary",
        event_id=name,
        title=name,
        starts_at=START + timedelta(minutes=offset),
        ends_at=START + timedelta(minutes=offset + duration),
    )


class CalendarControllerTests(unittest.TestCase):
    def test_combines_two_providers_in_chronological_order(self) -> None:
        controller = CalendarController(
            {
                "proton": FakeProvider([event("proton", "Later", 120)]),
                "google": FakeProvider([event("google", "Earlier", 30)]),
            }
        )
        result = controller.list_events(START, START + timedelta(days=1))
        self.assertEqual([item.title for item in result], ["Earlier", "Later"])

    def test_includes_overlapping_events_but_not_boundary_touching(self) -> None:
        controller = CalendarController(
            {
                "local": FakeProvider(
                    [
                        event("local", "Overlaps", -30),
                        event("local", "Ends at start", -60),
                        event("local", "Starts at end", 60),
                    ]
                )
            }
        )
        result = controller.list_events(START, START + timedelta(minutes=60))
        self.assertEqual([item.title for item in result], ["Overlaps"])

    def test_unreadable_provider_is_skipped(self) -> None:
        controller = CalendarController(
            {"local": FakeProvider([event("local", "Hidden", 0)], False)}
        )
        self.assertEqual(controller.list_events(START, START + timedelta(days=1)), [])

    def test_rejects_mismatched_account(self) -> None:
        controller = CalendarController({"google": FakeProvider([event("proton", "Wrong", 0)])})
        with self.assertRaises(ValueError):
            controller.list_events(START, START + timedelta(days=1))

    def test_requires_aware_query_range(self) -> None:
        controller = CalendarController({})
        with self.assertRaises(ValueError):
            controller.list_events(START.replace(tzinfo=None), START + timedelta(days=1))

    def test_rejects_invalid_event_range(self) -> None:
        with self.assertRaises(ValueError):
            event("local", "Invalid", 10, duration=0)


if __name__ == "__main__":
    unittest.main()
