# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Switchable secondary context rail for the ORC cockpit home screen."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta, timezone
from collections.abc import Callable
from dataclasses import dataclass

from .context_offroad_panel import ContextOffroadPanel
from .context_vehicle_panel import ContextVehiclePanel
from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from apps.orcUi.trip_presenter import TripPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive import FuelLevelGauge
from frontends.tk.automotive.vehicle_gauge_widgets import LinearGauge, RoundGauge
from ui.theme import ThemeBundle, ThemeMode
from .shell_metrics import CONTEXT_RAIL_WIDTH, FONT_BODY, FONT_CONTROL, FONT_SMALL
from ui.ui_widget import UiWidget


@dataclass(frozen=True)
class ContextPage:
    name: str
    accent: str
    builder: Callable[[tk.Frame], None]


class ContextRail(tk.Frame, UiWidget, ContextVehiclePanel):
    """Compact, user-switchable secondary information panel."""

    WIDTH = CONTEXT_RAIL_WIDTH

    def __init__(
        self,
        parent: tk.Misc,
        on_expand: Callable[[str], None] | None = None,
        *,
        theme: ThemeBundle | None = None,
    ) -> None:
        self._theme = theme or packaged_theme_bundle(ThemeMode.DARK)
        ui = self._theme.ui
        super().__init__(
            parent,
            bg=ui.surface,
            width=self.WIDTH,
            highlightthickness=1,
            highlightcolor=ui.border,
            highlightbackground=ui.border,
        )
        self.pack_propagate(False)
        self._on_expand = on_expand
        self._vehicle_state = VehiclePresentationState()
        self._trip_state = TripPresentationState()
        self._position_state = PositionPresentationState()
        self._attitude_state = AttitudePresentationState()
        self._vehicle_gauges: dict[str, RoundGauge | LinearGauge | FuelLevelGauge] = {}
        self._trip_value_labels: dict[str, tk.Label] = {}
        self._gear_value_label: tk.Label | None = None
        self._offroad_panel: ContextOffroadPanel | None = None
        self._calendar_factory: Callable[[tk.Misc], tk.Widget] | None = None
        self._calendar_timer = None
        self._personal_tab = None
        self.bind("<Destroy>", self._stop_calendar_poll, add="+")
        self._group = "AUTOMOTIVE"
        self._group_pages = {"AUTOMOTIVE": 0, "PERSONAL": 0}
        self._page_index = 0
        self._swipe_start: tuple[int, int] | None = None
        self._title: tk.Label
        self._body: tk.Frame
        self._rebuild()

    @property
    def selected_page(self) -> str:
        return self._pages()[self._page_index].name

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply a CSS-derived theme while preserving page and telemetry state."""
        self._theme = theme
        self.configure(
            bg=theme.ui.surface, highlightcolor=theme.ui.border, highlightbackground=theme.ui.border
        )
        self._rebuild()

    def update_vehicle_state(self, state: VehiclePresentationState) -> None:
        self._vehicle_state = state
        if self.selected_page == "VEHICLE":
            self._paint_vehicle_values()
        elif self._offroad_panel is not None:
            self._offroad_panel.update_vehicle(state)

    def update_trip_state(self, state: TripPresentationState) -> None:
        self._trip_state = state
        if self.selected_page == "TRIP":
            self._paint_trip_values()

    def update_position_state(self, state: PositionPresentationState) -> None:
        self._position_state = state
        if self._offroad_panel is not None:
            self._offroad_panel.update_position(state)

    def update_attitude_state(self, state: AttitudePresentationState) -> None:
        self._attitude_state = state
        if self._offroad_panel is not None:
            self._offroad_panel.update_attitude(state)

    def _pages(self) -> tuple[ContextPage, ...]:
        ui = self._theme.ui
        pages = (
            ContextPage("VEHICLE", ui.accent_success, self._build_vehicle),
            ContextPage("TRIP", ui.accent_primary, self._build_trip),
            ContextPage("OFF-ROAD", ui.accent_warning, self._build_offroad),
        )
        if self._group == "PERSONAL" and self._calendar_factory is not None:
            return (ContextPage("CALENDAR", ui.accent_primary, self._build_calendar),)
        return pages

    def selection(self) -> tuple[str, dict[str, int]]:
        pages = dict(self._group_pages)
        pages[self._group] = self._page_index
        return self._group, pages

    def restore_selection(self, selection: tuple[str, dict[str, int]]) -> None:
        group, pages = selection
        self._group_pages = dict(pages)
        self._group = group if self._calendar_factory is not None else "AUTOMOTIVE"
        self._page_index = self._group_pages[self._group] % len(self._pages())
        self._rebuild()

    def set_calendar_factory(self, factory: Callable[[tk.Misc], tk.Widget]) -> None:
        self._calendar_factory = factory
        self._rebuild()
        if self._calendar_timer is None:
            self._poll_calendar()

    def _poll_calendar(self) -> None:
        self._calendar_timer = None
        monitor = getattr(self._calendar_factory, "monitor", None)
        if monitor is None:
            return
        monitor.poll()
        upcoming = False
        if monitor.snapshot is not None and not monitor.failed:
            events, health = monitor.snapshot.events, monitor.snapshot.health
            if not health.stale and health.last_data_refresh_age_seconds is not None:
                now = datetime.now(timezone.utc)
                upcoming = any(
                    timedelta(0) <= event.starts_at - now <= timedelta(hours=1) for event in events
                )
        if self._personal_tab is not None:
            self._personal_tab.configure(text="PERSONAL •" if upcoming else "PERSONAL")
        self._calendar_timer = self.after(500, self._poll_calendar)

    def _stop_calendar_poll(self, event: tk.Event) -> None:
        if event.widget is self and self._calendar_timer is not None:
            self.after_cancel(self._calendar_timer)
            self._calendar_timer = None

    def _select_group(self, group: str) -> None:
        if group == self._group:
            return
        self._group_pages[self._group] = self._page_index
        self._group = group
        self._page_index = self._group_pages[group]
        self._rebuild()

    def _build_calendar(self, parent: tk.Frame) -> None:
        if self._calendar_factory is not None:
            self._calendar_factory(parent).pack(fill=tk.BOTH, expand=True)

    def _rebuild(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._vehicle_gauges.clear()
        self._trip_value_labels.clear()
        self._gear_value_label = None
        self._offroad_panel = None
        self._build_header()
        self._body = tk.Frame(self, bg=self._theme.ui.surface)
        self._body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 10))
        self._show_page()

    def _build_header(self) -> None:
        ui = self._theme.ui
        if self._calendar_factory is not None:
            tabs = tk.Frame(self, bg=ui.surface)
            tabs.pack(fill=tk.X, padx=8, pady=(4, 0))
            for group in ("AUTOMOTIVE", "PERSONAL"):
                button = tk.Button(
                    tabs,
                    text=group,
                    command=lambda value=group: self._select_group(value),
                    bg=ui.control_active if group == self._group else ui.control_background,
                    fg=ui.control_text,
                    relief=tk.FLAT,
                    bd=0,
                    highlightthickness=0,
                    font=("Sans", FONT_SMALL, "bold"),
                )
                button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
                if group == "PERSONAL":
                    self._personal_tab = button
        header = tk.Frame(self, bg=ui.surface)
        header.pack(fill=tk.X, padx=8, pady=(7, 3))
        header.grid_columnconfigure(1, weight=1)
        self._title = tk.Label(
            header, text="", bg=ui.surface, font=("Sans", FONT_CONTROL + 1, "bold")
        )
        if len(self._pages()) > 1:
            self._nav_button(header, "‹", self._previous_page).grid(row=0, column=0, sticky="w")
        self._title.grid(row=0, column=1)
        controls = tk.Frame(header, bg=ui.surface)
        controls.grid(row=0, column=2, sticky="e")
        if self._on_expand is not None:
            tk.Button(
                controls,
                text="↗",
                command=self._expand_page,
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                width=3,
                font=("Sans", 15, "bold"),
                cursor="hand2",
            ).pack(side=tk.LEFT)
        if len(self._pages()) > 1:
            self._nav_button(controls, "›", self._next_page).pack(side=tk.LEFT)

    def _nav_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        width: int = 3,
        font_size: int = 16,
    ) -> tk.Button:
        ui = self._theme.ui
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            width=width,
            font=("Sans", font_size, "bold"),
            cursor="hand2",
        )

    def _expand_page(self) -> None:
        if self._on_expand is not None:
            self._on_expand(self.selected_page)

    def _previous_page(self) -> None:
        self._page_index = (self._page_index - 1) % len(self._pages())
        self._show_page()

    def _next_page(self) -> None:
        self._page_index = (self._page_index + 1) % len(self._pages())
        self._show_page()

    def _show_page(self) -> None:
        ui = self._theme.ui
        for child in self._body.winfo_children():
            child.destroy()
        self._vehicle_gauges.clear()
        self._trip_value_labels.clear()
        self._gear_value_label = None
        self._offroad_panel = None
        pages = self._pages()
        page = pages[self._page_index]
        self._title.configure(text=page.name, fg=page.accent, bg=ui.surface)
        page.builder(self._body)
        self._swipe_start = None
        for child in self._body.winfo_children():
            self._bind_swipe(child)
        if len(pages) == 1:
            return
        dots = tk.Frame(self._body, bg=ui.surface)
        dots.pack(side=tk.BOTTOM, pady=(4, 0))
        for index in range(len(pages)):
            tk.Label(
                dots,
                text="●" if index == self._page_index else "·",
                fg=page.accent if index == self._page_index else ui.text_muted,
                bg=ui.surface,
                font=("Sans", FONT_SMALL),
            ).pack(side=tk.LEFT, padx=2)

    def _bind_swipe(self, widget: tk.Misc) -> None:
        if isinstance(widget, tk.Button):
            return
        widget.bind("<ButtonPress-1>", self._begin_swipe, add="+")
        widget.bind("<ButtonRelease-1>", self._end_swipe, add="+")
        for child in widget.winfo_children():
            self._bind_swipe(child)

    def _begin_swipe(self, event: tk.Event) -> None:
        self._swipe_start = (event.x_root, event.y_root)

    def _end_swipe(self, event: tk.Event) -> None:
        start, self._swipe_start = self._swipe_start, None
        if start is None or len(self._pages()) < 2:
            return
        dx = event.x_root - start[0]
        dy = event.y_root - start[1]
        if abs(dx) >= 50 and abs(dx) > 2 * abs(dy):
            if dx < 0:
                self._next_page()
            else:
                self._previous_page()

    def _build_trip(self, parent: tk.Frame) -> None:
        self._metric_table(
            parent,
            (
                ("distance", "Distance", "mi"),
                ("elapsed", "Elapsed", ""),
                ("average", "Avg speed", "MPH"),
                ("moving", "Moving", ""),
                ("fuel_used", "Fuel used", "gal"),
                ("economy", "Economy", "MPG"),
            ),
            self._trip_value_labels,
        )
        self._paint_trip_values()

    def _paint_trip_values(self) -> None:
        if not self._trip_value_labels:
            return
        state = self._trip_state
        values = {
            "distance": f"{state.distance_miles:.1f}",
            "elapsed": self._format_duration(state.elapsed_s),
            "average": "--"
            if state.average_speed_mph is None
            else f"{state.average_speed_mph:.1f}",
            "moving": self._format_duration(state.moving_s),
            "fuel_used": "--"
            if state.fuel_used_gallons is None
            else f"{state.fuel_used_gallons:.2f}",
            "economy": "--" if state.economy_mpg is None else f"{state.economy_mpg:.1f}",
        }
        for key, text in values.items():
            label = self._trip_value_labels.get(key)
            if label is not None:
                label.configure(text=text)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, round(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}"

    def _build_offroad(self, parent: tk.Frame) -> None:
        self._offroad_panel = ContextOffroadPanel(
            parent,
            theme=self._theme,
            vehicle=self._vehicle_state,
            position=self._position_state,
            attitude=self._attitude_state,
        )

    def _metric_table(
        self,
        parent: tk.Frame,
        metrics: tuple[tuple[str, str, str], ...],
        value_labels: dict[str, tk.Label] | None = None,
    ) -> None:
        ui = self._theme.ui
        grid = tk.Frame(parent, bg=ui.surface)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.grid_columnconfigure(0, weight=2)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_columnconfigure(2, weight=1)
        for row, (key, label, unit) in enumerate(metrics):
            tk.Label(
                grid,
                text=label,
                fg=ui.text_muted,
                bg=ui.surface,
                font=("Sans", FONT_SMALL),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(2, 4), pady=3)
            value = tk.Label(
                grid,
                text="--",
                fg=ui.text,
                bg=ui.surface,
                font=("Sans", FONT_BODY + 2, "bold"),
                anchor="e",
            )
            value.grid(row=row, column=1, sticky="e", padx=4, pady=3)
            if value_labels is not None:
                value_labels[key] = value
            tk.Label(
                grid,
                text=unit,
                fg=ui.text_muted,
                bg=ui.surface,
                font=("Sans", FONT_SMALL),
                anchor="w",
            ).grid(row=row, column=2, sticky="w", padx=(0, 2), pady=3)
