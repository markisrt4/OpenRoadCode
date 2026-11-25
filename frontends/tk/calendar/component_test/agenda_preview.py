# SPDX-License-Identifier: MIT
"""Preview the calendar agenda independently of the dashboard."""

import argparse
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apps.orcUi.theme_runtime import theme_bundle
from controllers.calendar.cached_calendar_provider import CachedCalendarProvider
from controllers.calendar.calendar_agenda import CalendarAgendaController
from controllers.calendar.calendar_presentation import (
    CalendarAgendaPresentation,
    CalendarSelectionPresentation,
    calendar_health_view,
)
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.calendar_models import CalendarCapabilities, CalendarEvent
from controllers.calendar.calendar_provider_if import CalendarProviderIf
from frontends.tk.calendar.calendar_screen import CalendarScreen
from ui.theme import ThemeMode


class DemoProvider(CalendarProviderIf):
    @property
    def capabilities(self):
        return CalendarCapabilities()

    def list_events(self, start, end):
        return [
            CalendarEvent(
                "demo",
                "demo",
                str(index),
                title,
                start + timedelta(days=index, hours=14),
                start + timedelta(days=index, hours=15),
                location=location,
            )
            for index, (title, location) in enumerate(
                [
                    ("Team meeting", "Conference room"),
                    ("Dinner", "Downtown"),
                    ("Family activity", "Community center"),
                ]
            )
            if start + timedelta(days=index, hours=14) < end
        ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("--size", choices=("1280x720", "800x480"), default="1280x720")
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--light", action="store_true")
    args = parser.parse_args()
    zone = ZoneInfo(args.timezone)
    selection = Path.home() / ".config/openroadcode/calendar-selection.json"
    cache_path = Path.home() / ".local/share/openroadcode/calendar/events.sqlite3"
    provider = (
        CachedCalendarProvider(
            "caldav",
            CalendarEventCache(cache_path),
            selection_file=selection,
        )
        if args.cached
        else DemoProvider()
    )
    root = tk.Tk()
    root.title("OpenRoadCode Calendar")
    root.geometry(args.size)
    screen = CalendarScreen(
        root,
        agenda=CalendarAgendaPresentation(
            CalendarAgendaController(provider, zone), calendar_health_view
        ),
        theme=theme_bundle(ThemeMode.LIGHT if args.light else ThemeMode.DARK),
        zone=zone,
        selection=CalendarSelectionPresentation(selection, cache_path.with_suffix(".catalog.json"))
        if args.cached
        else None,
    )
    screen.pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
