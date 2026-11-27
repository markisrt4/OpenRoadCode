# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Exercise calendar aggregation without network or hardware dependencies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from controllers.calendar import (
    CalendarCapabilities,
    CalendarController,
    CalendarEvent,
    CalendarProviderIf,
)


class ExampleProvider(CalendarProviderIf):
    def __init__(self, account_id: str, title: str, start: datetime) -> None:
        self.account_id = account_id
        self.title = title
        self.start = start

    @property
    def capabilities(self) -> CalendarCapabilities:
        return CalendarCapabilities()

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return [
            CalendarEvent(
                account_id=self.account_id,
                calendar_id="primary",
                event_id="demo",
                title=self.title,
                starts_at=self.start,
                ends_at=self.start + timedelta(hours=1),
            )
        ]


def main() -> None:
    start = datetime(2026, 11, 23, tzinfo=timezone.utc)
    controller = CalendarController(
        {
            "proton": ExampleProvider("proton", "Proton example", start + timedelta(hours=9)),
            "google": ExampleProvider("google", "Google example", start + timedelta(hours=10)),
        }
    )
    for item in controller.list_events(start, start + timedelta(days=1)):
        print(f"{item.starts_at.isoformat()} [{item.account_id}] {item.title}")


if __name__ == "__main__":
    main()
