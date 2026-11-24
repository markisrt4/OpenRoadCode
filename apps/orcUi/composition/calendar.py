# SPDX-License-Identifier: MIT
"""Compose the dashboard calendar and own its visible panel lifecycle."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apps.orcUi.theme_runtime import theme_bundle
from controllers.calendar.cached_calendar_provider import CachedCalendarProvider
from controllers.calendar.calendar_agenda import CalendarAgendaController
from controllers.calendar.calendar_event_cache import CalendarEventCache
from frontends.tk.calendar.calendar_screen import CalendarScreen
from frontends.tk.tk_screen import TkScreen
from ui.screen_ui_if import ScreenId


class DashboardCalendarScreen(TkScreen):
    """Create the calendar only while its dashboard destination is active."""

    def __init__(self, app):
        super().__init__(ScreenId("calendar"))
        self._app = app
        self._panel = None

    def show(self):
        self.hide()
        self._app.activate_screen(self)
        self._app.clear_screen_content()
        self._app.set_screen_title("CALENDAR")
        cache_path = Path.home() / ".local/share/openroadcode/calendar/events.sqlite3"
        selection = Path.home() / ".config/openroadcode/calendar-selection.json"
        try:
            zone = ZoneInfo("America/Detroit")
        except ZoneInfoNotFoundError:
            zone = datetime.now().astimezone().tzinfo
        provider = CachedCalendarProvider(
            "caldav", CalendarEventCache(cache_path), selection_file=selection
        )
        self._panel = CalendarScreen(
            self._app.screen_parent,
            controller=CalendarAgendaController(provider, zone),
            theme=theme_bundle(self._app.theme_mode),
            zone=zone,
            selection_file=selection,
            catalog_file=cache_path.with_suffix(".catalog.json"),
        )
        self._panel.pack(fill="both", expand=True)

    def hide(self):
        panel, self._panel = self._panel, None
        if panel is not None and panel.winfo_exists():
            panel.destroy()

    def set_theme_mode(self, mode):
        del mode
        if self._panel is not None:
            self.show()


def configure_calendar(app):
    screen = DashboardCalendarScreen(app)
    app.register_screen("CALENDAR", screen, before="MEDIA")
    return screen
