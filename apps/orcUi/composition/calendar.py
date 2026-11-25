# SPDX-License-Identifier: MIT
"""Compose the dashboard calendar and own its visible panel lifecycle."""

from dataclasses import dataclass, field
from datetime import date, datetime, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apps.orcUi.composition.appointment_navigation import create_appointment_estimate_cache
from apps.orcUi.theme_runtime import theme_bundle
from common.app_settings import AppSettingsStore
from controllers.calendar.appointment_monitor import AppointmentMonitor
from controllers.calendar.cached_calendar_provider import CachedCalendarProvider
from controllers.calendar.calendar_agenda import CalendarAgendaController
from controllers.calendar.calendar_coverage import covered_calendar_days
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.calendar_presentation import (
    CalendarAgendaPresentation,
    CalendarSelectionPresentation,
    calendar_health_view,
    event_view,
)
from controllers.calendar.calendar_query_if import CalendarQueryIf
from controllers.calendar.upcoming_appointments import upcoming_appointments
from controllers.connectivity.online_mode import saved_online_mode
from frontends.tk.calendar.calendar_screen import CalendarScreen
from frontends.tk.calendar.dashboard_screen import DashboardCalendarScreen
from frontends.tk.calendar.upcoming_panel import UpcomingPanel
from ui.calendar.calendar_models import AppointmentSnapshot
from ui.calendar.calendar_presentation_if import AppointmentMonitorIf
from ui.navigation.route_request_handler_if import RouteRequestHandlerIf


def _local_zone() -> tzinfo:
    try:
        return ZoneInfo("America/Detroit")
    except ZoneInfoNotFoundError:
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

    def coverage(self, day: date, days: int) -> frozenset[date]:
        """Read cached coverage for the configured account and timezone."""
        return covered_calendar_days(
            CalendarEventCache(self.cache_path),
            self.account_id,
            self.selection_path,
            self.cache_path.with_suffix(".catalog.json"),
            self.zone,
            day,
            days,
        )

    def query(self) -> CalendarQueryIf:
        provider = CachedCalendarProvider(
            self.account_id,
            CalendarEventCache(self.cache_path),
            selection_file=self.selection_path,
        )
        return CalendarAgendaController(provider, self.zone)


def configure_calendar(app, config: CalendarConfiguration | None = None):
    config = config or CalendarConfiguration()

    settings = AppSettingsStore()

    def save_buffer(minutes: int) -> None:
        settings.update(appointment_arrival_minutes=minutes)

    def create_panel(parent):
        return CalendarScreen(
            parent,
            agenda=CalendarAgendaPresentation(
                config.query(),
                lambda: calendar_health_view(
                    config.cache_path.with_suffix(".health.json"), offline=not saved_online_mode()
                ),
                config.coverage,
            ),
            theme=theme_bundle(app.theme_mode),
            zone=config.zone,
            arrival_buffer=lambda: settings.load().appointment_arrival_minutes,
            save_arrival_buffer=save_buffer,
            selection=CalendarSelectionPresentation(
                config.selection_path, config.cache_path.with_suffix(".catalog.json")
            ),
        )

    screen = DashboardCalendarScreen(app, create_panel)
    app.register_screen("CALENDAR", screen, before="MEDIA")
    return screen


class HomeCalendarFactory:
    def __init__(
        self,
        app,
        config: CalendarConfiguration | None = None,
        route_handler: RouteRequestHandlerIf | None = None,
    ):
        self._route_handler = route_handler
        self._app = app
        config = config or CalendarConfiguration()
        self._zone = config.zone
        estimates = create_appointment_estimate_cache()

        def load():
            now = datetime.now(config.zone)
            query = config.query()
            events = upcoming_appointments(query, now, limit=1)
            return AppointmentSnapshot(
                tuple(event_view(event) for event in events),
                calendar_health_view(
                    config.cache_path.with_suffix(".health.json"), offline=not saved_online_mode()
                ),
                len(config.coverage(now.date(), 7)) == 7,
                estimates.estimate(query, events[0]) if events else None,
            )

        self.monitor: AppointmentMonitorIf = AppointmentMonitor(load)

    def __call__(self, parent):
        return UpcomingPanel(
            parent,
            theme=theme_bundle(self._app.theme_mode),
            monitor=self.monitor,
            zone=self._zone,
            route_handler=self._route_handler,
        )


def create_home_calendar_factory(
    app,
    config: CalendarConfiguration | None = None,
    route_handler: RouteRequestHandlerIf | None = None,
):
    return HomeCalendarFactory(app, config, route_handler)
