# SPDX-License-Identifier: MIT
"""Compose the dashboard calendar and own its visible panel lifecycle."""

from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo

from apps.orcUi.theme_runtime import theme_bundle
from controllers.calendar.appointment_monitor import AppointmentMonitor
from controllers.calendar.cached_calendar_provider import CachedCalendarProvider
from controllers.calendar.calendar_agenda import CalendarAgendaController
from controllers.calendar.calendar_presentation import (
    CalendarAgendaPresentation,
    CalendarSelectionPresentation,
    calendar_health_view,
    event_view,
)
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.calendar_query_if import CalendarQueryIf
from controllers.calendar.upcoming_appointments import upcoming_appointments
from ui.calendar.calendar_models import AppointmentSnapshot
from ui.calendar.calendar_presentation_if import AppointmentMonitorIf
from frontends.tk.calendar.calendar_screen import CalendarScreen
from frontends.tk.calendar.upcoming_panel import UpcomingPanel
from frontends.tk.calendar.dashboard_screen import DashboardCalendarScreen


def _local_zone() -> tzinfo:
    return datetime.now().astimezone().tzinfo or ZoneInfo("UTC")


@dataclass(frozen=True)
class CalendarConfiguration:
    """Shared configuration for all calendar consumers."""

    cache_path: Path = field(
        default_factory=lambda: Path.home() / ".local/share/openroadcode/calendar/events.sqlite3"
    )
    selection_path: Path = field(
        default_factory=lambda: Path.home() / ".config/openroadcode/calendar-selection.json"
    )
    account_id: str = "caldav"
    zone: tzinfo = field(default_factory=_local_zone)

    def query(self) -> CalendarQueryIf:
        provider = CachedCalendarProvider(
            self.account_id,
            CalendarEventCache(self.cache_path),
            selection_file=self.selection_path,
        )
        return CalendarAgendaController(provider, self.zone)


def configure_calendar(app, config: CalendarConfiguration | None = None):
    config = config or CalendarConfiguration()

    def create_panel(parent):
        return CalendarScreen(
            parent,
            agenda=CalendarAgendaPresentation(config.query(), calendar_health_view),
            theme=theme_bundle(app.theme_mode),
            zone=config.zone,
            selection=CalendarSelectionPresentation(
                config.selection_path, config.cache_path.with_suffix(".catalog.json")
            ),
        )

    screen = DashboardCalendarScreen(app, create_panel)
    app.register_screen("CALENDAR", screen, before="MEDIA")
    return screen


class HomeCalendarFactory:
    def __init__(self, app, config: CalendarConfiguration | None = None):
        self._app = app
        config = config or CalendarConfiguration()
        self._zone = config.zone

        def load():
            events = upcoming_appointments(config.query(), datetime.now(config.zone), limit=1)
            return AppointmentSnapshot(
                tuple(event_view(event) for event in events), calendar_health_view()
            )

        self.monitor: AppointmentMonitorIf = AppointmentMonitor(load)

    def __call__(self, parent):
        return UpcomingPanel(
            parent,
            theme=theme_bundle(self._app.theme_mode),
            monitor=self.monitor,
            zone=self._zone,
        )


def create_home_calendar_factory(app, config: CalendarConfiguration | None = None):
    return HomeCalendarFactory(app, config)
