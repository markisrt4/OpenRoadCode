# SPDX-License-Identifier: MIT
"""Compact upcoming appointments presentation for a mounted context page."""

import tkinter as tk
from concurrent.futures import Future
from threading import Thread


def _read(future, load):
    if not future.set_running_or_notify_cancel():
        return
    try:
        future.set_result(load())
    except Exception as error:
        future.set_exception(error)


class UpcomingPanel(tk.Frame):
    def __init__(self, parent, *, theme, load, zone):
        super().__init__(parent, bg=theme.ui.surface)
        self._ui = theme.ui
        self._load = load
        self._zone = zone
        self._future = None
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
        self._future = Future()
        Thread(
            target=_read,
            args=(self._future, self._load),
            daemon=True,
            name="upcoming-calendar-read",
        ).start()
        self._timer = self.after(50, self._collect)

    def _collect(self):
        self._timer = None
        if self._closed:
            return
        if not self._future.done():
            self._timer = self.after(50, self._collect)
            return
        for child in self.winfo_children():
            child.destroy()
        try:
            events, health = self._future.result()
        except Exception:
            self._label("Calendar cache unavailable", self._ui.accent_warning)
        else:
            if health.get("status") == "unavailable" or health.get(
                "last_data_refresh_age_seconds"
            ) is None:
                self._label("Calendar freshness unknown", self._ui.accent_warning)
            elif health.get("stale"):
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
        self._future = None
        self._timer = self.after(30000, self._refresh)

    def _close(self, event):
        if event.widget is not self or self._closed:
            return
        self._closed = True
        if self._timer is not None:
            self.after_cancel(self._timer)
            self._timer = None
        if self._future is not None:
            self._future.cancel()
            self._future = None
