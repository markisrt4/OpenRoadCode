# SPDX-License-Identifier: MIT
"""Compact upcoming appointments presentation for a mounted context page."""

import tkinter as tk
from tkinter import messagebox

from ui.navigation.route_request_handler_if import RouteRequestHandlerIf
from ui.navigation.route_types import TravelMode

from ui import UiWidget
from ui.calendar.calendar_presentation_if import AppointmentMonitorIf


class UpcomingPanel(tk.Frame, UiWidget):
    def __init__(
        self, parent, *, theme, monitor: AppointmentMonitorIf, zone,
        route_handler: RouteRequestHandlerIf | None = None,
    ):
        super().__init__(parent, bg=theme.ui.surface)
        self._ui = theme.ui
        self._monitor = monitor
        self._zone = zone
        self._route_handler = route_handler
        self._last_state = None
        self._timer = None
        self._closed = False
        self.bind("<Destroy>", self._close, add="+")
        self._label("Loading appointments…", self._ui.text_muted)
        self._refresh()

    def _label(self, text, color, size=10):
        tk.Label(
            self,
            text=text,
            fg=color,
            bg=self._ui.surface,
            font=("Sans", size),
            wraplength=180,
            justify=tk.LEFT,
            anchor="w",
        ).pack(fill=tk.X, pady=3)

    def _refresh(self):
        self._timer = None
        if self._closed:
            return
        state = (self._monitor.snapshot, self._monitor.failed)
        if state != self._last_state:
            self._last_state = state
            self._render(*state)
        self._timer = self.after(500, self._refresh)

    def _render(self, snapshot, failed):
        for child in self.winfo_children():
            child.destroy()
        if failed:
            self._label("Calendar cache unavailable", self._ui.accent_warning)
        if snapshot is None:
            if not failed:
                self._label("Loading appointments…", self._ui.text_muted)
        else:
            events, health = snapshot.events, snapshot.health
            if health.offline:
                self._label("Offline · Saved calendar data", self._ui.text_muted)
            if health.status == "unavailable" or health.last_data_refresh_age_seconds is None:
                self._label("Calendar freshness unknown", self._ui.accent_warning)
            elif health.stale:
                self._label("Calendar data stale", self._ui.accent_warning)
            elif health.status != "ok":
                self._label("Calendar sync incomplete", self._ui.accent_warning)
            if snapshot.complete_coverage is False:
                self._label("Upcoming calendar coverage incomplete", self._ui.accent_warning)
            if not events:
                message = health.empty_message
                if (
                    snapshot.complete_coverage is False
                    and health.last_data_refresh_age_seconds is not None
                ):
                    message = "Upcoming appointments unknown"
                self._label(message, self._ui.text_muted)
            for event in events:
                start = event.starts_at.astimezone(self._zone)
                self._label(start.strftime("%a %b %d · %I:%M %p"), self._ui.accent_primary)
                self._label(event.title or "Untitled", self._ui.text, 12)
                if event.location:
                    self._label(event.location, self._ui.text_muted)
            if snapshot.journey is not None and snapshot.journey.event in events:
                departure = snapshot.journey.leave_by.astimezone(self._zone)
                minutes = int((snapshot.journey.travel_seconds + 59) // 60)
                self._label(f"Travel: {minutes} min", self._ui.text_muted)
                self._label(
                    departure.strftime("Leave by %a %I:%M %p"), self._ui.accent_primary
                )
                if (
                    not failed
                    and self._route_handler is not None
                    and snapshot.journey.destination is not None
                    and TravelMode.AUTO in self._route_handler.supported_travel_modes
                ):
                    tk.Button(
                        self,
                        text="Navigate to appointment",
                        command=lambda: self._navigate(snapshot),
                    ).pack(fill=tk.X, pady=3)

    def _navigate(self, snapshot):
        journey = snapshot.journey
        handler = self._route_handler
        if journey is None or journey.destination is None or handler is None:
            return
        if journey.event is None or journey.event not in snapshot.events:
            return
        if not messagebox.askyesno(
            "Navigate to appointment",
            f"Start driving guidance to {journey.event.location}? "
            "This may replace active guidance.",
            parent=self,
        ):
            return
        if self._monitor.snapshot != snapshot or self._monitor.failed:
            return
        try:
            handler.request_start_route(journey.destination, TravelMode.AUTO)
        except Exception:
            messagebox.showerror("Navigation", "Unable to start guidance.", parent=self)

    def _close(self, event):
        if event.widget is not self or self._closed:
            return
        self._closed = True
        if self._timer is not None:
            self.after_cancel(self._timer)
            self._timer = None
