# SPDX-License-Identifier: MIT
"""Compact upcoming appointments presentation for a mounted context page."""

import tkinter as tk
from ui.calendar.calendar_presentation_if import AppointmentMonitorIf


class UpcomingPanel(tk.Frame):
    def __init__(self, parent, *, theme, monitor: AppointmentMonitorIf, zone):
        super().__init__(parent, bg=theme.ui.surface)
        self._ui = theme.ui
        self._monitor = monitor
        self._zone = zone
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
            if (
                health.status == "unavailable"
                or health.last_data_refresh_age_seconds is None
            ):
                self._label("Calendar freshness unknown", self._ui.accent_warning)
            elif health.stale:
                self._label("Calendar data stale", self._ui.accent_warning)
            elif health.get("status") != "ok":
                self._label("Calendar sync incomplete", self._ui.accent_warning)
            if not events:
                self._label("No upcoming timed appointments in cache", self._ui.text_muted)
            for event in events:
                start = event.starts_at.astimezone(self._zone)
                self._label(start.strftime("%a %b %d · %I:%M %p"), self._ui.accent_primary)
                self._label(event.title or "Untitled", self._ui.text, 12)
                if event.location:
                    self._label(event.location, self._ui.text_muted)

    def _close(self, event):
        if event.widget is not self or self._closed:
            return
        self._closed = True
        if self._timer is not None:
            self.after_cancel(self._timer)
            self._timer = None
