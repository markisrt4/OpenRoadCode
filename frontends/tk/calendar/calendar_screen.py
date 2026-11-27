# SPDX-License-Identifier: MIT
"""Touch-friendly cached calendar agenda."""

import calendar
import hashlib
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timedelta

from ui import UiWidget
from ui.calendar.calendar_models import CalendarHealthView
from ui.calendar.calendar_presentation_if import CalendarAgendaIf, CalendarSelectionIf
from ui.theme import ThemeBundle


def _calendar_color(account_id: str, calendar_id: str) -> str:
    """Stable presentation color independent of event order."""
    palette = ("#4285d4", "#a56bd8", "#249b83", "#c47c32", "#d45d83", "#708ac4")
    digest = hashlib.sha256(f"{account_id}:{calendar_id}".encode()).digest()
    return palette[int.from_bytes(digest[:4], "big") % len(palette)]


class CalendarScreen(tk.Frame, UiWidget):
    """Load agenda data off the Tk thread and render on the Tk thread."""

    def __init__(
        self,
        parent,
        *,
        agenda: CalendarAgendaIf,
        theme: ThemeBundle,
        zone,
        selection: CalendarSelectionIf | None = None,
        arrival_buffer: Callable[[], int] | None = None,
        save_arrival_buffer: Callable[[int], None] | None = None,
    ):
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._ui = ui
        self._month = False
        self._groups = ()
        self._agenda = agenda
        self._zone = zone
        self._selection = selection
        self._arrival_buffer = arrival_buffer
        self._save_arrival_buffer = save_arrival_buffer
        self._day = datetime.now(zone).date()
        self._selected = self._day
        self._day -= timedelta(days=self._day.weekday())
        self._closed = False
        self._poll = None
        self._refresh_timer = None
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
        if selection is not None or arrival_buffer is not None:
            tk.Button(
                bar,
                text="⚙",
                command=self._settings,
                bg=ui.surface,
                fg=ui.text,
                relief=tk.FLAT,
                font=("Sans", 15),
            ).pack(side=tk.LEFT, padx=4)
        self._status = tk.Label(bar, bg=ui.background, fg=ui.text, font=("Sans", 11))
        self._status.pack(side=tk.RIGHT, padx=6)
        self._content = tk.Frame(self, bg=ui.background)
        self._content.pack(fill=tk.BOTH, expand=True, padx=8)
        self._week = tk.Frame(self._content, bg=ui.background)
        self._body = tk.Canvas(self._content, bg=ui.background, highlightthickness=0)
        self._layout()

        self._body.bind("<Configure>", lambda event: self._render_agenda(preserve_scroll=True))
        self._body.bind("<ButtonPress-1>", self._drag_start)
        self._body.bind("<B1-Motion>", self._drag_move)
        self._body.bind(
            "<MouseWheel>",
            lambda event: self._body.yview_scroll(-1 if event.delta > 0 else 1, "units"),
        )
        self._body.bind("<Button-4>", lambda event: self._body.yview_scroll(-1, "units"))
        self._body.bind("<Button-5>", lambda event: self._body.yview_scroll(1, "units"))
        self._covered_days = None
        self._message = "Loading appointments..."
        self._footer = tk.Label(
            self, text="Local calendar agenda", bg=ui.background, fg=ui.text_muted
        )
        self._footer.pack(anchor="w", padx=12, pady=4)
        self.bind("<Destroy>", self._close, add="+")
        self._refresh()
        self._render()
        self._refresh_timer = self.after(30000, self._periodic_refresh)

    def _periodic_refresh(self):
        self._refresh_timer = None
        if self._closed:
            return
        self._refresh()
        self._refresh_timer = self.after(30000, self._periodic_refresh)

    def _settings(self):
        from tkinter import messagebox

        try:
            catalog = self._selection.list_calendars() if self._selection is not None else ()
        except (OSError, ValueError) as error:
            messagebox.showerror("Calendar settings", str(error), parent=self)
            return
        ui = self._ui
        dialog = tk.Toplevel(self, bg=ui.background)
        dialog.title("Calendar settings")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        buffer = tk.IntVar(dialog, value=self._arrival_buffer() if self._arrival_buffer else 10)
        if self._save_arrival_buffer is not None:
            row = tk.Frame(dialog, bg=ui.background)
            row.pack(fill=tk.X, padx=12, pady=8)
            tk.Label(row, text="Arrive early (minutes)", bg=ui.background, fg=ui.text).pack()
            controls = tk.Frame(row, bg=ui.background)
            controls.pack()
            for label, delta in (("−", -5), ("+", 5)):
                tk.Button(
                    controls,
                    text=label,
                    width=4,
                    pady=8,
                    bg=ui.surface,
                    fg=ui.text,
                    command=lambda step=delta: buffer.set(max(0, min(120, buffer.get() + step))),
                ).pack(side=tk.LEFT if delta < 0 else tk.RIGHT, padx=8)
            tk.Label(
                controls, textvariable=buffer, bg=ui.background, fg=ui.text, font=("Sans", 16)
            ).pack(side=tk.LEFT)
        if not catalog:
            tk.Label(
                dialog, text="Waiting for calendar discovery.", bg=ui.background, fg=ui.text_muted
            ).pack(padx=12, pady=6)
        variables = {}
        for item in sorted(catalog, key=lambda item: item.name.casefold()):
            calendar_id, name = item.calendar_id, item.name
            variable = tk.BooleanVar(dialog, value=item.enabled)
            variables[calendar_id] = variable
            row = tk.Frame(dialog, bg=ui.background)
            row.pack(fill=tk.X, padx=12, pady=3)
            tk.Frame(row, bg=_calendar_color("caldav", calendar_id), width=5).pack(
                side=tk.LEFT, fill=tk.Y
            )
            tk.Checkbutton(
                row,
                text=name or "Unnamed calendar",
                variable=variable,
                bg=ui.background,
                fg=ui.text,
                selectcolor=ui.surface,
                activebackground=ui.background,
                activeforeground=ui.text,
                font=("Sans", 13),
            ).pack(side=tk.LEFT, padx=8)

        def apply():
            updated = {key: value.get() for key, value in variables.items()}
            try:
                if self._selection is not None and updated:
                    self._selection.apply_selection(updated)
                if self._save_arrival_buffer is not None:
                    self._save_arrival_buffer(buffer.get())
            except OSError as error:
                messagebox.showerror("Calendar settings", str(error), parent=dialog)
                return
            dialog.destroy()
            self._reload()

        tk.Button(dialog, text="Apply", command=apply, bg=ui.surface, fg=ui.text, pady=8).pack(
            pady=10
        )
        tk.Button(dialog, text="Cancel", command=dialog.destroy, bg=ui.surface, fg=ui.text).pack(
            pady=(0, 8)
        )

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
        self._covered_days = None
        self._groups = ()
        self._message = "Loading appointments..."
        self._refresh()
        self._render()

    def _select(self, day):
        self._selected = day
        self._render()

    def _render(self, *, preserve_scroll=False):
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
        self._render_agenda(preserve_scroll=preserve_scroll)

    def _render_agenda(self, *, preserve_scroll=False):
        ui = self._ui
        canvas = self._body
        scroll = canvas.yview()[0] if preserve_scroll else 0
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
            message = self._message
            covered = getattr(self, "_covered_days", None)
            if (
                covered is not None
                and self._selected not in covered
                and message == "No cached appointments."
            ):
                message = "Calendar data incomplete or unavailable for this date."
            canvas.create_text(margin, y, anchor="nw", text=message, fill=ui.text_muted)
        for event in events:
            start = event.starts_at.astimezone(self._zone)
            end = event.ends_at.astimezone(self._zone)
            when = "All day" if event.all_day else f"{start:%I:%M %p} – {end:%I:%M %p}"
            ongoing = not event.all_day and start <= datetime.now(self._zone) < end
            color = _calendar_color(event.account_id, event.calendar_id)
            text_width = max(1, width - 2 * margin - 32)
            background = canvas.create_rectangle(
                margin, y, width - margin, y + 1, fill=ui.surface, outline=""
            )
            cursor = y + 10
            for label, foreground, font in (
                (when + ("  • Now" if ongoing else ""), ui.text_muted, ("Sans", 11)),
                (event.title or "Untitled", ui.text, ("Sans", 13 if compact else 16, "bold")),
                (event.location, ui.text_muted, ("Sans", 10)),
            ):
                if not label:
                    continue
                item = canvas.create_text(
                    margin + 16,
                    cursor,
                    anchor="nw",
                    text=label,
                    fill=foreground,
                    font=font,
                    width=text_width,
                )
                cursor = canvas.bbox(item)[3] + 5
            bottom = max(cursor + 5, y + 64)
            canvas.coords(background, margin, y, width - margin, bottom)
            canvas.create_rectangle(margin, y, margin + 5, bottom, fill=color, outline="")
            y = bottom + 8
        canvas.configure(scrollregion=(0, 0, width, max(y + 12, canvas.winfo_height())))
        canvas.yview_moveto(scroll)

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
        events_by_day = {group.day: group.events for group in self._groups}
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
                indicator = tk.Frame(cell, bg=background)
                indicator.pack(anchor="center")
                colors = list(
                    dict.fromkeys(
                        _calendar_color(event.account_id, event.calendar_id)
                        for event in events_by_day.get(day, ())
                    )
                )
                for color in colors[:3]:
                    tk.Label(indicator, text="●", bg=background, fg=color, font=("Sans", 10)).pack(
                        side=tk.LEFT
                    )
                tk.Label(
                    indicator,
                    text=str(count) if count else " ",
                    bg=background,
                    fg=ui.text_muted,
                    font=("Sans", 9),
                ).pack(side=tk.LEFT)
                if in_month:
                    for widget in (cell, number, indicator, *indicator.winfo_children()):
                        widget.bind("<Button-1>", lambda event, value=day: self._select(value))

    def _refresh(self):
        if self._closed:
            return
        days = calendar.monthrange(self._day.year, self._day.month)[1] if self._month else 7
        end = self._day + timedelta(days=days - 1)
        self._status.configure(
            text=self._day.strftime("%B %Y")
            if self._month
            else f"{self._day:%b %d} – {end:%b %d, %Y}"
        )
        self._agenda.request(self._day, days)
        if self._poll is None:
            self._poll = self.after(50, self._collect)

    def _collect(self):
        self._poll = None
        if self._closed:
            return
        try:
            snapshot = self._agenda.poll()
            if snapshot is None:
                self._poll = self.after(50, self._collect)
                return
            self._groups = snapshot.groups
            self._covered_days = snapshot.covered_days
            self._update_footer(snapshot.health)
            self._message = snapshot.health.empty_message
        except Exception:
            self._covered_days = None
            self._message = "Calendar cache unavailable."
            self._footer.configure(text=self._message, fg=self._ui.accent_warning)
        self._render(preserve_scroll=True)

    def _update_footer(self, health: CalendarHealthView):
        status = health.status
        age = health.last_data_refresh_age_seconds
        freshness = "not yet refreshed" if age is None else f"refreshed {age / 60:.0f} min ago"
        stale = health.stale
        if health.syncing and not health.offline:
            status = "syncing"
        self._footer.configure(
            text=(
                f"Calendar sync: {'OFFLINE' if health.offline else status.upper()} · {freshness}"
                + (" · Stale" if stale else "")
            ),
            fg=self._ui.accent_warning if stale or status != "ok" else self._ui.text_muted,
        )

    def _close(self, event):
        if event.widget is self and not self._closed:
            self._closed = True
            if self._refresh_timer is not None:
                self.after_cancel(self._refresh_timer)
                self._refresh_timer = None
            if self._poll is not None:
                self.after_cancel(self._poll)
                self._poll = None
            self._agenda.close()
