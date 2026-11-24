# SPDX-License-Identifier: MIT
"""Touch-friendly cached calendar agenda."""

import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from controllers.calendar.calendar_agenda import CalendarAgendaController
from ui.theme import ThemeBundle


class CalendarScreen(tk.Frame):
    """Load agenda data off the Tk thread and render on the Tk thread."""

    def __init__(self, parent, *, controller: CalendarAgendaController, theme: ThemeBundle, zone):
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._controller = controller
        self._zone = zone
        self._day = datetime.now(zone).date()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._future = None
        self._poll = None
        self._requested = None
        bar = tk.Frame(self, bg=ui.background)
        bar.pack(fill=tk.X)
        for title, delta in (("Previous", -7), ("Today", 0), ("Next", 7)):
            tk.Button(
                bar,
                text=title,
                command=lambda value=delta: self._move(value),
                bg=ui.surface,
                fg=ui.text,
                font=("Sans", 12),
                pady=6,
            ).pack(side=tk.LEFT, padx=4, pady=4)
        self._status = tk.Label(bar, bg=ui.background, fg=ui.text, font=("Sans", 11))
        self._status.pack(side=tk.RIGHT, padx=6)
        self._body = tk.Text(
            self,
            bg=ui.background,
            fg=ui.text,
            font=("Sans", 12),
            wrap=tk.WORD,
            relief=tk.FLAT,
            highlightthickness=0,
            padx=12,
            pady=8,
        )
        self._body.pack(fill=tk.BOTH, expand=True)
        self._body.tag_configure("day", foreground=ui.accent_primary, font=("Sans", 13, "bold"))
        self._body.tag_configure("location", foreground=ui.text_muted)
        self._body.configure(state=tk.DISABLED)
        self._body.bind("<ButtonPress-1>", self._drag_start)
        self._body.bind("<B1-Motion>", self._drag_move)
        self.bind("<Destroy>", self._close, add="+")
        self._refresh()

    def _drag_start(self, event):
        self._body.scan_mark(event.x, event.y)
        return "break"

    def _drag_move(self, event):
        self._body.scan_dragto(event.x, event.y, gain=1)
        return "break"

    def _move(self, delta):
        self._day = (
            self._day + timedelta(days=delta) if delta else datetime.now(self._zone).date()
        )
        self._refresh()

    def _refresh(self):
        self._status.configure(text=self._day.strftime("%b %d, %Y"))
        if self._future is None:
            self._requested = self._day
            self._future = self._executor.submit(self._controller.load, self._day)
            self._poll = self.after(50, self._collect)

    def _collect(self):
        self._poll = None
        if not self._future.done():
            self._poll = self.after(50, self._collect)
            return
        future, self._future = self._future, None
        if self._requested != self._day:
            self._refresh()
            return
        self._body.configure(state=tk.NORMAL)
        self._body.delete("1.0", tk.END)
        try:
            groups = future.result()
            if not groups:
                self._body.insert(tk.END, "No cached appointments in this period.")
            for group in groups:
                self._body.insert(tk.END, group.day.strftime("%A, %B %d") + "\n", "day")
                for event in group.events:
                    start = event.starts_at.astimezone(self._zone)
                    when = "All day" if event.all_day else start.strftime("%I:%M %p")
                    if not event.all_day and start.date() < group.day:
                        when = "Continues"
                    self._body.insert(tk.END, f"  {when}    {event.title or 'Untitled'}\n")
                    if event.location:
                        self._body.insert(tk.END, f"      {event.location}\n", "location")
                self._body.insert(tk.END, "\n")
        except Exception:
            self._body.insert(tk.END, "Calendar cache unavailable.")
        finally:
            self._body.configure(state=tk.DISABLED)

    def _close(self, event):
        if event.widget is self:
            if self._poll is not None:
                self.after_cancel(self._poll)
            self._executor.shutdown(wait=False, cancel_futures=True)
