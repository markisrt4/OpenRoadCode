# SPDX-License-Identifier: MIT
"""Compose the dashboard calendar and own its visible panel lifecycle."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apps.orcUi.theme_runtime import theme_bundle
from controllers.calendar.appointment_monitor import AppointmentMonitor
from controllers.calendar.cached_calendar_provider import CachedCalendarProvider
from controllers.calendar.calendar_agenda import CalendarAgendaController
from controllers.calendar.calendar_presentation import (
    CalendarAgendaPresentation,
    CalendarSelectionPresentation,
    calendar_health_view,
)
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.upcoming_appointments import upcoming_appointments
from controllers.system.calendar_health_sampler import sample_calendar_health
from frontends.tk.calendar.calendar_screen import CalendarScreen
from frontends.tk.calendar.upcoming_panel import UpcomingPanel
from frontends.tk.calendar.dashboard_screen import DashboardCalendarScreen


def configure_calendar(app):
    def create_panel(parent):
        cache_path = Path.home() / ".local/share/openroadcode/calendar/events.sqlite3"
        selection = Path.home() / ".config/openroadcode/calendar-selection.json"
        try:
            zone = ZoneInfo("America/Detroit")
        except ZoneInfoNotFoundError:
            zone = datetime.now().astimezone().tzinfo
        provider = CachedCalendarProvider(
            "caldav", CalendarEventCache(cache_path), selection_file=selection
        )
        return CalendarScreen(
            parent,
            agenda=CalendarAgendaPresentation(
                CalendarAgendaController(provider, zone), calendar_health_view
            ),
            theme=theme_bundle(app.theme_mode),
            zone=zone,
            selection=CalendarSelectionPresentation(
                selection, cache_path.with_suffix(".catalog.json")
            ),
        )

    screen = DashboardCalendarScreen(app, create_panel)
    app.register_screen("CALENDAR", screen, before="MEDIA")
    return screen


class HomeCalendarFactory:
    def __init__(self, app):
        self._app = app
        try:
            self._zone = ZoneInfo("America/Detroit")
        except ZoneInfoNotFoundError:
            self._zone = datetime.now().astimezone().tzinfo
        zone = self._zone

        def load():
            cache = CalendarEventCache(
                Path.home() / ".local/share/openroadcode/calendar/events.sqlite3"
            )
            provider = CachedCalendarProvider(
                "caldav",
                cache,
                selection_file=Path.home() / ".config/openroadcode/calendar-selection.json",
            )
            events = upcoming_appointments(
                CalendarAgendaController(provider, zone), datetime.now(zone), limit=1
            )
            return events, sample_calendar_health()

        self.monitor = AppointmentMonitor(load)

    def __call__(self, parent):
        return UpcomingPanel(
            parent,
            theme=theme_bundle(self._app.theme_mode),
            monitor=self.monitor,
            zone=self._zone,
        )


def create_home_calendar_factory(app):
    return HomeCalendarFactory(app)
