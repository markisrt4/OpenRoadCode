# SPDX-License-Identifier: MIT
"""Touch-friendly cached calendar agenda."""

import calendar
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
        self._ui = ui
        self._month = False
        self._groups = ()
        self._controller = controller
        self._zone = zone
        self._day = datetime.now(zone).date()
        self._selected = self._day
        self._day -= timedelta(days=self._day.weekday())
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._future = None
        self._poll = None
        self._requested = None
        bar = tk.Frame(self, bg=ui.background)
        bar.pack(fill=tk.X, padx=8, pady=(8, 18))
        tk.Label(
            bar, text="CALENDAR", bg=ui.background, fg=ui.text, font=("Sans", 15, "bold")
        ).pack(side=tk.LEFT, padx=12)
        for title, delta in (("Previous", -7), ("Today", 0), ("Next", 7)):
            tk.Button(
                bar,
                text=title,
                command=lambda value=delta: self._move(value),
                bg=ui.surface,
                fg=ui.text,
                font=("Sans", 12),
                pady=6,
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0,
                activebackground=ui.surface,
                activeforeground=ui.accent_primary,
            ).pack(side=tk.LEFT, padx=4, pady=4)
        self._toggle = tk.Button(
            bar,
            text="Month",
            command=self._toggle_view,
            bg=ui.surface,
            fg=ui.text,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=("Sans", 12),
            pady=6,
        )
        self._toggle.pack(side=tk.LEFT, padx=4)
        self._status = tk.Label(bar, bg=ui.background, fg=ui.text, font=("Sans", 11))
        self._status.pack(side=tk.RIGHT, padx=6)
        self._content = tk.Frame(self, bg=ui.background)
        self._content.pack(fill=tk.BOTH, expand=True, padx=8)
        self._week = tk.Frame(self._content, bg=ui.background)
        self._body = tk.Canvas(self._content, bg=ui.background, highlightthickness=0)
        self._layout()

        self._body.bind("<Configure>", lambda event: self._render())
        self._body.bind("<ButtonPress-1>", self._drag_start)
        self._body.bind("<B1-Motion>", self._drag_move)
        self._body.bind(
            "<MouseWheel>",
            lambda event: self._body.yview_scroll(-1 if event.delta > 0 else 1, "units"),
        )
        self._body.bind("<Button-4>", lambda event: self._body.yview_scroll(-1, "units"))
        self._body.bind("<Button-5>", lambda event: self._body.yview_scroll(1, "units"))
        self._message = "Loading appointments..."
        tk.Label(self, text="Local calendar agenda", bg=ui.background, fg=ui.text_muted).pack(
            anchor="w", padx=12, pady=4
        )
        self.bind("<Destroy>", self._close, add="+")
        self._refresh()
        self._render()

    def _layout(self):
        self._week.grid_forget()
        self._body.grid_forget()
        self._content.columnconfigure(0, weight=1)
        self._content.columnconfigure(1, weight=0)
        self._content.rowconfigure(0, weight=0)
        self._content.rowconfigure(1, weight=1)
        if self._month:
            self._content.columnconfigure(0, weight=5, uniform="pane")
            self._content.columnconfigure(1, weight=4, uniform="pane")
            self._content.rowconfigure(0, weight=1)
            self._content.rowconfigure(1, weight=0)
            self._week.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
            self._body.grid(row=0, column=1, sticky="nsew")
        else:
            self._content.columnconfigure(0, weight=1, uniform="")
            self._content.columnconfigure(1, weight=0, uniform="")
            self._week.grid(row=0, column=0, sticky="ew")
            self._body.grid(row=1, column=0, sticky="nsew")

    def _drag_start(self, event):
        self._body.scan_mark(event.x, event.y)
        return "break"

    def _drag_move(self, event):
        self._body.scan_dragto(event.x, event.y, gain=1)
        return "break"

    def _toggle_view(self):
        self._month = not self._month
        self._toggle.configure(text="Week" if self._month else "Month")
        self._day = (
            self._selected.replace(day=1)
            if self._month
            else self._selected - timedelta(days=self._selected.weekday())
        )
        self._layout()
        self._reload()

    def _move(self, delta):
        today = datetime.now(self._zone).date()
        if not delta:
            self._selected = today
            self._day = (
                today.replace(day=1) if self._month else today - timedelta(days=today.weekday())
            )
        elif self._month:
            index = self._day.year * 12 + self._day.month - 1 + (1 if delta > 0 else -1)
            year, month = divmod(index, 12)
            self._day = self._day.replace(year=year, month=month + 1, day=1)
            self._selected = self._day
        else:
            self._day += timedelta(days=delta)
            self._selected = self._day
        self._reload()

    def _reload(self):
        self._groups = ()
        self._message = "Loading appointments..."
        self._refresh()
        self._render()

    def _select(self, day):
        self._selected = day
        self._render()

    def _render(self):
        ui = self._ui
        today = datetime.now(self._zone).date()
        counts = {group.day: len(group.events) for group in self._groups}
        for child in self._week.winfo_children():
            child.destroy()
        for row in range(7):
            self._week.rowconfigure(row, weight=0, uniform="")
        if self._month:
            self._render_month(counts, today)
        else:
            for index in range(7):
                day = self._day + timedelta(days=index)
                selected = day == self._selected
                count = counts.get(day, 0)
                background = ui.surface if selected else ui.background
                foreground = ui.accent_primary if selected or day == today else ui.text
                cell = tk.Frame(self._week, bg=background)
                cell.grid(row=0, column=index, sticky="nsew", padx=2)
                self._week.columnconfigure(index, weight=1, uniform="day")
                for label, size, color in (
                    (day.strftime("%a").upper(), 10, foreground),
                    (str(day.day), 19, foreground),
                    (f"• {count}" if count else " ", 10, ui.accent_primary),
                ):
                    widget = tk.Label(
                        cell, text=label, font=("Sans", size), bg=background, fg=color
                    )
                    widget.pack(fill=tk.X)
                    widget.bind("<Button-1>", lambda event, value=day: self._select(value))
                cell.bind("<Button-1>", lambda event, value=day: self._select(value))
        canvas = self._body
        canvas.delete("all")
        width = max(canvas.winfo_width(), 240)
        compact = width < 850
        margin = 10 if compact else 20
        y = 12
        canvas.create_text(
            margin,
            y,
            anchor="nw",
            text=self._selected.strftime("%A, %B %d"),
            fill=ui.accent_primary,
            font=("Sans", 15, "bold"),
        )
        y += 34
        events = next((group.events for group in self._groups if group.day == self._selected), ())
        if not events:
            canvas.create_text(margin, y, anchor="nw", text=self._message, fill=ui.text_muted)
        for event in events:
            start = event.starts_at.astimezone(self._zone)
            end = event.ends_at.astimezone(self._zone)
            when = "All day" if event.all_day else f"{start:%I:%M %p} – {end:%I:%M %p}"
            ongoing = not event.all_day and start <= datetime.now(self._zone) < end
            color = ui.accent_success if ongoing else ui.accent_primary
            height = 78 if compact else 96
            canvas.create_rectangle(
                margin, y, width - margin, y + height, fill=ui.surface, outline=""
            )
            canvas.create_rectangle(margin, y, margin + 5, y + height, fill=color, outline="")
            canvas.create_text(
                margin + 16,
                y + 9,
                anchor="nw",
                text=when + ("  • Now" if ongoing else ""),
                fill=color,
                font=("Sans", 11),
            )
            canvas.create_text(
                margin + 16,
                y + 29,
                anchor="nw",
                text=event.title or "Untitled",
                fill=ui.text,
                font=("Sans", 13 if compact else 16, "bold"),
                width=width - 2 * margin - 32,
            )
            if event.location:
                canvas.create_text(
                    margin + 16,
                    y + 54,
                    anchor="nw",
                    text=event.location,
                    fill=ui.text_muted,
                    font=("Sans", 10),
                    width=width - 2 * margin - 32,
                )
            y += height + 8
        canvas.configure(scrollregion=(0, 0, width, max(y + 12, canvas.winfo_height())))
        canvas.yview_moveto(0)

    def _render_month(self, counts, today):
        ui = self._ui
        for column, name in enumerate(calendar.day_abbr):
            self._week.columnconfigure(column, weight=1, uniform="day")
            tk.Label(
                self._week,
                text=name.upper(),
                bg=ui.background,
                fg=ui.text_muted,
                font=("Sans", 10),
            ).grid(row=0, column=column, sticky="ew")
        weeks = calendar.Calendar().monthdatescalendar(self._day.year, self._day.month)
        for row, week in enumerate(weeks, 1):
            self._week.rowconfigure(row, weight=1, uniform="week")
            for column, day in enumerate(week):
                selected = day == self._selected
                in_month = day.month == self._day.month
                count = counts.get(day, 0)
                background = ui.surface if in_month else ui.background
                foreground = ui.accent_primary if day == today else ui.text
                cell = tk.Frame(
                    self._week,
                    bg=background,
                    highlightthickness=2,
                    highlightbackground=ui.accent_primary if selected else ui.background,
                )
                cell.grid(row=row, column=column, sticky="nsew", padx=2, pady=2)
                number = tk.Label(
                    cell,
                    text=str(day.day),
                    bg=background,
                    fg=foreground if in_month else ui.text_muted,
                    font=("Sans", 13, "bold" if selected or day == today else "normal"),
                )
                number.pack(anchor="center", expand=True)
                indicator = tk.Label(
                    cell,
                    text=f"• {count}" if count else " ",
                    bg=background,
                    fg=ui.accent_primary,
                    font=("Sans", 9),
                )
                indicator.pack(anchor="center")
                if in_month:
                    for widget in (cell, number, indicator):
                        widget.bind("<Button-1>", lambda event, value=day: self._select(value))

    def _refresh(self):
        days = calendar.monthrange(self._day.year, self._day.month)[1] if self._month else 7
        end = self._day + timedelta(days=days - 1)
        self._status.configure(
            text=self._day.strftime("%B %Y")
            if self._month
            else f"{self._day:%b %d} – {end:%b %d, %Y}"
        )
        if self._future is None:
            self._requested = (self._day, self._month)
            self._future = self._executor.submit(self._controller.load, self._day, days)
            self._poll = self.after(50, self._collect)

    def _collect(self):
        self._poll = None
        if not self._future.done():
            self._poll = self.after(50, self._collect)
            return
        future, self._future = self._future, None
        if self._requested != (self._day, self._month):
            self._refresh()
            return
        try:
            self._groups = future.result()
            self._message = "No cached appointments on this day."
        except Exception:
            self._groups = ()
            self._message = "Calendar cache unavailable."
        self._render()

    def _close(self, event):
        if event.widget is self:
            if self._poll is not None:
                self.after_cancel(self._poll)
            self._executor.shutdown(wait=False, cancel_futures=True)
